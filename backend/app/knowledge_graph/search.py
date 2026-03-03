"""Hybrid search combining ChromaDB vector similarity and Neo4j graph proximity.

Scoring formula:
    final_score = (VECTOR_WEIGHT * vector_score) + (GRAPH_WEIGHT * graph_score)

Default weights: vector 0.6, graph 0.4.
"""

from __future__ import annotations

import asyncio
from typing import Any

import chromadb
import structlog
from langchain_openai import OpenAIEmbeddings

from app.config import Settings, get_settings
from app.knowledge_graph.client import Neo4jClient, get_neo4j_client
from app.knowledge_graph.queries import GRAPH_PROXIMITY_SEARCH

logger = structlog.get_logger()

# ------------------------------------------------------------------
# Weights
# ------------------------------------------------------------------

VECTOR_WEIGHT: float = 0.6
GRAPH_WEIGHT: float = 0.4

# ChromaDB collection name shared with the rest of Creator OS.
_CONTENT_COLLECTION: str = "content_embeddings"


# ------------------------------------------------------------------
# Embedding helper
# ------------------------------------------------------------------


async def _embed_query(query: str, settings: Settings) -> list[float]:
    """Embed the search query using the configured OpenAI embedding model.

    Returns a list of floats representing the query vector.
    """
    embeddings = OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key,
    )
    vector: list[float] = await embeddings.aembed_query(query)
    return vector


# ------------------------------------------------------------------
# ChromaDB vector search
# ------------------------------------------------------------------


def _get_chroma_client(settings: Settings) -> chromadb.HttpClient:
    """Return a ChromaDB HTTP client configured from settings."""
    return chromadb.HttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port,
    )


async def _vector_search(
    query: str,
    creator_id: str,
    top_k: int,
    settings: Settings,
) -> list[dict[str, Any]]:
    """Perform a vector similarity search in ChromaDB.

    Returns a list of dicts with ``content_id``, ``title``, ``vector_score``,
    and ``distance``.
    """
    query_vector = await _embed_query(query, settings)

    # ChromaDB's Python client is synchronous; run in the default executor
    # to avoid blocking the event loop.
    loop = asyncio.get_running_loop()

    def _query() -> dict[str, Any]:
        client = _get_chroma_client(settings)
        collection = client.get_or_create_collection(name=_CONTENT_COLLECTION)
        return collection.query(
            query_embeddings=[query_vector],
            n_results=top_k * 2,  # over-fetch to allow re-ranking
            where={"creator_id": creator_id},
            include=["metadatas", "distances"],
        )

    try:
        results = await loop.run_in_executor(None, _query)
    except Exception as exc:
        logger.error("hybrid_search.vector_failed", error=str(exc))
        return []

    # Unpack ChromaDB response (lists are wrapped in an outer list).
    ids: list[str] = results.get("ids", [[]])[0]
    metadatas: list[dict[str, Any]] = results.get("metadatas", [[]])[0]
    distances: list[float] = results.get("distances", [[]])[0]

    scored: list[dict[str, Any]] = []
    for content_id, meta, distance in zip(ids, metadatas, distances):
        # ChromaDB returns L2 distance by default.  Convert to a 0-1
        # similarity score: sim = 1 / (1 + distance).
        similarity = 1.0 / (1.0 + distance)
        scored.append(
            {
                "content_id": content_id,
                "title": meta.get("title", ""),
                "content_type": meta.get("content_type", ""),
                "vector_score": similarity,
                "distance": distance,
            }
        )

    logger.info("hybrid_search.vector_done", hits=len(scored))
    return scored


# ------------------------------------------------------------------
# Neo4j graph proximity search
# ------------------------------------------------------------------


async def _extract_query_topics(query: str, settings: Settings) -> list[str]:
    """Use the LLM to extract topic names from a free-text search query.

    Returns a list of lower-cased topic strings suitable for matching
    against ``Topic.name`` in Neo4j.
    """
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = ChatAnthropic(
        model=settings.default_llm,
        anthropic_api_key=settings.anthropic_api_key,
        temperature=0.0,
        max_tokens=512,
    )

    system = (
        "You extract topic names from a search query. "
        "Return ONLY a JSON array of lower-cased topic strings. "
        'Example: ["machine learning", "python", "neural networks"]. '
        "Do NOT wrap in markdown code fences."
    )

    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=system),
                HumanMessage(content=query),
            ]
        )
        import json

        raw = response.content
        if isinstance(raw, list):
            raw = "".join(
                block if isinstance(block, str) else block.get("text", "")
                for block in raw
            )
        topics: list[str] = json.loads(raw)
        return [t.lower().strip() for t in topics if isinstance(t, str)]
    except Exception as exc:
        logger.warning("hybrid_search.topic_extraction_failed", error=str(exc))
        # Naive fallback: split on spaces and return meaningful chunks.
        return [query.lower().strip()]


async def _graph_search(
    query: str,
    creator_id: str,
    top_k: int,
    settings: Settings,
    client: Neo4jClient,
) -> list[dict[str, Any]]:
    """Search the Neo4j graph for content related to the query topics.

    Uses graph proximity (shared topics, subtopic relationships) to score
    content.  Returns a list of dicts with ``content_id``, ``title``,
    ``graph_score``, etc.
    """
    topic_names = await _extract_query_topics(query, settings)

    if not topic_names:
        return []

    try:
        records = await client.execute_query(
            GRAPH_PROXIMITY_SEARCH,
            {
                "creator_id": creator_id,
                "topic_names": topic_names,
                "limit": top_k * 2,
            },
        )
    except Exception as exc:
        logger.error("hybrid_search.graph_failed", error=str(exc))
        return []

    results: list[dict[str, Any]] = []
    for record in records:
        results.append(
            {
                "content_id": record["content_id"],
                "title": record.get("title", ""),
                "content_type": record.get("content_type", ""),
                "vector_id": record.get("vector_id"),
                "matched_topics": record.get("matched_topics", []),
                "graph_score": float(record.get("graph_score", 0.0)),
            }
        )

    logger.info("hybrid_search.graph_done", hits=len(results), topics=topic_names)
    return results


# ------------------------------------------------------------------
# Score normalisation
# ------------------------------------------------------------------


def _normalise_scores(
    items: list[dict[str, Any]],
    score_key: str,
) -> list[dict[str, Any]]:
    """Min-max normalise ``score_key`` to [0, 1] in place."""
    if not items:
        return items

    scores = [item[score_key] for item in items]
    min_s = min(scores)
    max_s = max(scores)
    span = max_s - min_s if max_s != min_s else 1.0

    for item in items:
        item[score_key] = (item[score_key] - min_s) / span

    return items


# ------------------------------------------------------------------
# Fusion & ranking
# ------------------------------------------------------------------


def _fuse_results(
    vector_results: list[dict[str, Any]],
    graph_results: list[dict[str, Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    """Merge vector and graph results into a single ranked list.

    For content that appears in both result sets the scores are combined
    using the configured weights.  Content appearing in only one set
    receives a zero for the missing component.
    """
    # Normalise each source independently.
    vector_results = _normalise_scores(vector_results, "vector_score")
    graph_results = _normalise_scores(graph_results, "graph_score")

    # Build lookup dicts keyed on content_id.
    merged: dict[str, dict[str, Any]] = {}

    for item in vector_results:
        cid = item["content_id"]
        merged[cid] = {
            "content_id": cid,
            "title": item.get("title", ""),
            "content_type": item.get("content_type", ""),
            "vector_score": item["vector_score"],
            "graph_score": 0.0,
            "matched_topics": [],
        }

    for item in graph_results:
        cid = item["content_id"]
        if cid in merged:
            merged[cid]["graph_score"] = item["graph_score"]
            merged[cid]["matched_topics"] = item.get("matched_topics", [])
        else:
            merged[cid] = {
                "content_id": cid,
                "title": item.get("title", ""),
                "content_type": item.get("content_type", ""),
                "vector_score": 0.0,
                "graph_score": item["graph_score"],
                "matched_topics": item.get("matched_topics", []),
            }

    # Compute final hybrid score.
    for entry in merged.values():
        entry["hybrid_score"] = (
            VECTOR_WEIGHT * entry["vector_score"]
            + GRAPH_WEIGHT * entry["graph_score"]
        )

    ranked = sorted(merged.values(), key=lambda x: x["hybrid_score"], reverse=True)
    return ranked[:top_k]


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


async def hybrid_search(
    query: str,
    creator_id: str,
    top_k: int = 10,
    *,
    vector_weight: float = VECTOR_WEIGHT,
    graph_weight: float = GRAPH_WEIGHT,
    settings: Settings | None = None,
    neo4j_client: Neo4jClient | None = None,
) -> list[dict[str, Any]]:
    """Execute a hybrid search combining ChromaDB vectors and Neo4j graph proximity.

    Parameters
    ----------
    query : str
        Free-text search query.
    creator_id : str
        UUID (as string) of the creator whose content should be searched.
    top_k : int
        Maximum number of results to return (default 10).
    vector_weight : float
        Weight for the vector similarity component (default 0.6).
    graph_weight : float
        Weight for the graph proximity component (default 0.4).
    settings : Settings | None
        Optional pre-loaded settings (falls back to ``get_settings()``).
    neo4j_client : Neo4jClient | None
        Optional pre-initialised Neo4j client (useful in tests).

    Returns
    -------
    list[dict[str, Any]]
        Ranked list of results, each containing:
        - ``content_id``
        - ``title``
        - ``content_type``
        - ``hybrid_score`` (0-1)
        - ``vector_score`` (0-1)
        - ``graph_score`` (0-1)
        - ``matched_topics``
    """
    log = logger.bind(query=query, creator_id=creator_id, top_k=top_k)
    log.info("hybrid_search.start")

    if settings is None:
        settings = get_settings()
    if neo4j_client is None:
        neo4j_client = await get_neo4j_client(settings)

    # Override module-level weights if the caller supplied custom ones.
    global VECTOR_WEIGHT, GRAPH_WEIGHT  # noqa: PLW0603
    original_vw, original_gw = VECTOR_WEIGHT, GRAPH_WEIGHT
    VECTOR_WEIGHT, GRAPH_WEIGHT = vector_weight, graph_weight

    try:
        # Run both searches concurrently.
        vector_task = _vector_search(query, creator_id, top_k, settings)
        graph_task = _graph_search(query, creator_id, top_k, settings, neo4j_client)
        vector_results, graph_results = await asyncio.gather(
            vector_task, graph_task, return_exceptions=False
        )

        ranked = _fuse_results(vector_results, graph_results, top_k)
        log.info("hybrid_search.complete", result_count=len(ranked))
        return ranked
    except Exception as exc:
        log.error("hybrid_search.failed", error=str(exc))
        raise
    finally:
        # Restore original weights.
        VECTOR_WEIGHT, GRAPH_WEIGHT = original_vw, original_gw
