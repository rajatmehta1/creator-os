"""Content-to-graph ingestion pipeline.

Extracts topics, keywords, and audience segments from content text using
an LLM, then creates / updates the corresponding nodes and relationships
in the Neo4j knowledge graph.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import get_settings
from app.knowledge_graph.client import Neo4jClient, get_neo4j_client
from app.knowledge_graph.queries import (
    CREATE_CONTENT,
    CREATE_KEYWORD,
    CREATE_TOPIC,
    LINK_CONTENT_TO_CREATOR,
    LINK_CONTENT_TO_KEYWORD,
    LINK_CONTENT_TO_TOPIC,
    LINK_CREATOR_TO_TOPIC,
    LINK_KEYWORD_TO_TOPIC,
)
from app.knowledge_graph.schemas import ContentNode, KeywordNode, TopicNode

logger = structlog.get_logger()

# ------------------------------------------------------------------
# LLM extraction
# ------------------------------------------------------------------

_EXTRACTION_SYSTEM_PROMPT: str = """\
You are a knowledge-graph extraction engine for a YouTube creator platform.
Given the title, content type, and body text of a piece of content, extract
structured metadata that will be stored as nodes and edges in a Neo4j graph.

Return ONLY a valid JSON object with exactly these keys:
{
  "topics": [
    {
      "name": "<lower-cased canonical topic name>",
      "display_name": "<human-friendly name>",
      "category": "<broad category or null>",
      "relevance": <float 0-1>,
      "is_primary": <bool>
    }
  ],
  "keywords": [
    {
      "name": "<lower-cased keyword phrase>",
      "intent": "<informational|navigational|transactional|commercial>"
    }
  ],
  "parent_topics": [
    {
      "child": "<topic name from topics list>",
      "parent": "<broader parent topic name>"
    }
  ],
  "keyword_topic_links": [
    {
      "keyword": "<keyword name>",
      "topic": "<topic name>"
    }
  ],
  "audience_segments": [
    "<segment name>"
  ]
}

Rules:
- Extract 3-8 topics, ordered by relevance.
- Mark exactly ONE topic as is_primary: true.
- Extract 5-15 keywords relevant for SEO.
- Parent topics should link narrow topics to broader ones.
- Audience segments describe who this content is for (1-3 segments).
- All names must be lower-cased and trimmed.
- Do NOT wrap the JSON in markdown code fences.
"""


async def _extract_graph_metadata(
    title: str,
    body: str,
    content_type: str,
) -> dict[str, Any]:
    """Call the LLM to extract topics, keywords, and relationships.

    Returns the parsed JSON dict.  On failure, returns a minimal fallback
    so ingestion can still proceed (with the title as the sole topic).
    """
    settings = get_settings()
    llm = ChatAnthropic(
        model=settings.default_llm,
        anthropic_api_key=settings.anthropic_api_key,
        temperature=0.0,
        max_tokens=2048,
    )

    # Truncate body to avoid blowing context limits.
    truncated_body = body[:12_000] if body else ""

    user_prompt = (
        f"Title: {title}\n"
        f"Content type: {content_type}\n\n"
        f"Body:\n{truncated_body}"
    )

    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=_EXTRACTION_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]
        )
        raw_text = response.content
        if isinstance(raw_text, list):
            # Some LangChain versions return a list of content blocks.
            raw_text = "".join(
                block if isinstance(block, str) else block.get("text", "")
                for block in raw_text
            )
        data: dict[str, Any] = json.loads(raw_text)
        logger.info(
            "kg.extraction_complete",
            topics=len(data.get("topics", [])),
            keywords=len(data.get("keywords", [])),
        )
        return data
    except Exception as exc:
        logger.error("kg.extraction_failed", error=str(exc), title=title)
        # Graceful fallback: use the title itself as a single topic.
        fallback_name = title.lower().strip()
        return {
            "topics": [
                {
                    "name": fallback_name,
                    "display_name": title,
                    "category": None,
                    "relevance": 1.0,
                    "is_primary": True,
                }
            ],
            "keywords": [],
            "parent_topics": [],
            "keyword_topic_links": [],
            "audience_segments": [],
        }


# ------------------------------------------------------------------
# Node / edge writers
# ------------------------------------------------------------------


async def _upsert_content_node(
    client: Neo4jClient,
    content_id: str,
    title: str,
    content_type: str,
    word_count: int,
) -> None:
    """Create or update the Content node."""
    await client.execute_write(
        CREATE_CONTENT,
        {
            "content_id": content_id,
            "title": title,
            "content_type": content_type,
            "status": "draft",
            "word_count": word_count,
            "vector_id": None,
            "url": None,
            "published_at": None,
            "performance_score": None,
        },
    )


async def _upsert_topic_nodes(
    client: Neo4jClient,
    topics: list[dict[str, Any]],
) -> None:
    """Create or update Topic nodes for every extracted topic."""
    for topic in topics:
        await client.execute_write(
            CREATE_TOPIC,
            {
                "name": topic["name"],
                "display_name": topic.get("display_name", topic["name"]),
                "category": topic.get("category"),
                "depth": 0,
            },
        )


async def _upsert_keyword_nodes(
    client: Neo4jClient,
    keywords: list[dict[str, Any]],
) -> None:
    """Create or update Keyword nodes."""
    for kw in keywords:
        await client.execute_write(
            CREATE_KEYWORD,
            {
                "name": kw["name"],
                "search_volume": None,
                "competition": None,
                "cpc": None,
                "intent": kw.get("intent"),
            },
        )


async def _link_content_to_topics(
    client: Neo4jClient,
    content_id: str,
    topics: list[dict[str, Any]],
) -> None:
    """Create COVERS edges between the content node and its topics."""
    for topic in topics:
        await client.execute_write(
            LINK_CONTENT_TO_TOPIC,
            {
                "content_id": content_id,
                "topic_name": topic["name"],
                "relevance": topic.get("relevance", 1.0),
                "is_primary": topic.get("is_primary", False),
                "mentioned_count": 1,
            },
        )


async def _link_content_to_keywords(
    client: Neo4jClient,
    content_id: str,
    keywords: list[dict[str, Any]],
) -> None:
    """Create TARGETS edges between the content node and its keywords."""
    for kw in keywords:
        await client.execute_write(
            LINK_CONTENT_TO_KEYWORD,
            {
                "content_id": content_id,
                "keyword_name": kw["name"],
            },
        )


async def _link_keywords_to_topics(
    client: Neo4jClient,
    keyword_topic_links: list[dict[str, str]],
) -> None:
    """Create KEYWORD_OF edges from keywords to topics."""
    for link in keyword_topic_links:
        await client.execute_write(
            LINK_KEYWORD_TO_TOPIC,
            {
                "keyword_name": link["keyword"],
                "topic_name": link["topic"],
            },
        )


async def _link_topic_hierarchy(
    client: Neo4jClient,
    parent_topics: list[dict[str, str]],
) -> None:
    """Create SUBTOPIC_OF edges and ensure parent topic nodes exist."""
    from app.knowledge_graph.queries import LINK_TOPIC_PARENT

    for relation in parent_topics:
        # Ensure the parent node exists before linking.
        await client.execute_write(
            CREATE_TOPIC,
            {
                "name": relation["parent"].lower().strip(),
                "display_name": relation["parent"],
                "category": None,
                "depth": 0,
            },
        )
        await client.execute_write(
            LINK_TOPIC_PARENT,
            {
                "child_name": relation["child"],
                "parent_name": relation["parent"],
            },
        )


async def _link_content_to_creator(
    client: Neo4jClient,
    content_id: str,
    creator_id: str,
) -> None:
    """Create the CREATED_BY edge from content to creator."""
    await client.execute_write(
        LINK_CONTENT_TO_CREATOR,
        {
            "content_id": content_id,
            "creator_id": creator_id,
        },
    )


async def _update_creator_authority(
    client: Neo4jClient,
    creator_id: str,
    topics: list[dict[str, Any]],
) -> None:
    """Update HAS_AUTHORITY edges between the creator and each topic.

    Authority score is proportional to the topic's relevance in the
    newly ingested content.  The actual accumulated score is maintained
    by the MERGE/ON MATCH clause in the Cypher query.
    """
    for topic in topics:
        authority_delta = topic.get("relevance", 1.0) * 10.0
        await client.execute_write(
            LINK_CREATOR_TO_TOPIC,
            {
                "creator_id": creator_id,
                "topic_name": topic["name"],
                "authority_score": authority_delta,
            },
        )


# ------------------------------------------------------------------
# Public entry point
# ------------------------------------------------------------------


async def ingest_content(
    content_id: str,
    title: str,
    body: str,
    content_type: str,
    creator_id: str,
    *,
    client: Neo4jClient | None = None,
) -> dict[str, Any]:
    """Full content-to-graph ingestion pipeline.

    1. Calls the LLM to extract topics, keywords, and relationships.
    2. Creates / updates all nodes (Content, Topic, Keyword).
    3. Creates all relationship edges (COVERS, TARGETS, CREATED_BY,
       HAS_AUTHORITY, SUBTOPIC_OF, KEYWORD_OF).

    Parameters
    ----------
    content_id : str
        UUID (as string) of the content row in PostgreSQL.
    title : str
        Content title.
    body : str
        Full text body of the content.
    content_type : str
        E.g. ``"youtube_video"``, ``"blog_post"``.
    creator_id : str
        UUID (as string) of the creator / user.
    client : Neo4jClient | None
        Optional pre-initialised client (useful in tests).

    Returns
    -------
    dict
        Summary of what was created, including extracted topics and
        keyword counts.
    """
    log = logger.bind(content_id=content_id, creator_id=creator_id)
    log.info("kg.ingestion_start", title=title, content_type=content_type)

    if client is None:
        client = await get_neo4j_client()

    # Step 1 -- LLM extraction
    metadata = await _extract_graph_metadata(title, body, content_type)
    topics: list[dict[str, Any]] = metadata.get("topics", [])
    keywords: list[dict[str, Any]] = metadata.get("keywords", [])
    parent_topics: list[dict[str, str]] = metadata.get("parent_topics", [])
    keyword_topic_links: list[dict[str, str]] = metadata.get("keyword_topic_links", [])

    word_count = len(body.split()) if body else 0

    # Step 2 -- Upsert nodes
    await _upsert_content_node(client, content_id, title, content_type, word_count)
    await _upsert_topic_nodes(client, topics)
    await _upsert_keyword_nodes(client, keywords)

    # Step 3 -- Create edges
    await _link_content_to_creator(client, content_id, creator_id)
    await _link_content_to_topics(client, content_id, topics)
    await _link_content_to_keywords(client, content_id, keywords)
    await _link_keywords_to_topics(client, keyword_topic_links)
    await _link_topic_hierarchy(client, parent_topics)
    await _update_creator_authority(client, creator_id, topics)

    summary = {
        "content_id": content_id,
        "topics_extracted": len(topics),
        "keywords_extracted": len(keywords),
        "parent_links": len(parent_topics),
        "keyword_topic_links": len(keyword_topic_links),
        "word_count": word_count,
        "topic_names": [t["name"] for t in topics],
    }
    log.info("kg.ingestion_complete", **summary)
    return summary
