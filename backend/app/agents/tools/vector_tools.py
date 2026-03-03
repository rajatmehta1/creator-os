"""ChromaDB vector store client wrapper for Creator OS.

Provides async utilities for initialising collections, upserting
embeddings, querying for similar items, and deleting entries.  Three
persistent collections are managed:

- **creator_dna**: Stores creator DNA profile embeddings for style matching.
- **content_embeddings**: Stores content script / outline embeddings for
  duplicate / similarity detection.
- **trend_embeddings**: Stores trend description embeddings for clustering
  and de-duplication.
"""

from typing import Any, Optional

import chromadb
import structlog

from app.config import get_settings

logger = structlog.get_logger()

# Collection names managed by Creator OS
COLLECTION_NAMES: list[str] = [
    "creator_dna",
    "content_embeddings",
    "trend_embeddings",
]

_chroma_client: Optional[chromadb.HttpClient] = None


def _get_chroma_client() -> chromadb.HttpClient:
    """Get or create the ChromaDB HTTP client singleton."""
    global _chroma_client
    if _chroma_client is None:
        settings = get_settings()
        _chroma_client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
        logger.info(
            "vector.client_created",
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
    return _chroma_client


def _get_collection(name: str) -> chromadb.Collection:
    """Retrieve a ChromaDB collection by name, creating it if absent."""
    client = _get_chroma_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


# ------------------------------------------------------------------
# Initialise collections
# ------------------------------------------------------------------

async def init_collections() -> dict[str, Any]:
    """Ensure all required ChromaDB collections exist.

    Creates any missing collections with cosine distance metric.
    Safe to call multiple times (idempotent).

    Returns:
        Dict mapping collection name to its current document count.
    """
    logger.info("vector.init_collections")
    import asyncio

    def _init() -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name in COLLECTION_NAMES:
            col = _get_collection(name)
            result[name] = col.count()
            logger.debug("vector.collection_ready", name=name, count=result[name])
        return result

    return await asyncio.to_thread(_init)


# ------------------------------------------------------------------
# Upsert
# ------------------------------------------------------------------

async def upsert_embedding(
    collection_name: str,
    doc_id: str,
    embedding: list[float],
    document: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Insert or update an embedding in a ChromaDB collection.

    Args:
        collection_name: Target collection (must be one of the managed names).
        doc_id: Unique document identifier.
        embedding: The embedding vector (list of floats).
        document: Optional raw text associated with the embedding.
        metadata: Optional metadata dict stored alongside the vector.

    Returns:
        Dict confirming the upsert with the doc_id and collection.
    """
    if collection_name not in COLLECTION_NAMES:
        raise ValueError(
            f"Unknown collection '{collection_name}'. "
            f"Valid: {COLLECTION_NAMES}"
        )

    logger.debug(
        "vector.upsert",
        collection=collection_name,
        doc_id=doc_id,
        dim=len(embedding),
    )
    import asyncio

    def _upsert() -> None:
        col = _get_collection(collection_name)
        upsert_kwargs: dict[str, Any] = {
            "ids": [doc_id],
            "embeddings": [embedding],
        }
        if document is not None:
            upsert_kwargs["documents"] = [document]
        if metadata is not None:
            # ChromaDB metadata values must be str, int, float, or bool
            clean_meta = {
                k: v
                for k, v in metadata.items()
                if isinstance(v, (str, int, float, bool))
            }
            upsert_kwargs["metadatas"] = [clean_meta]
        col.upsert(**upsert_kwargs)

    await asyncio.to_thread(_upsert)

    return {
        "status": "upserted",
        "collection": collection_name,
        "doc_id": doc_id,
    }


# ------------------------------------------------------------------
# Query similar
# ------------------------------------------------------------------

async def query_similar(
    collection_name: str,
    query_embedding: list[float],
    n_results: int = 5,
    where: Optional[dict[str, Any]] = None,
    include: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Find the most similar embeddings in a collection.

    Args:
        collection_name: Collection to search.
        query_embedding: The query vector.
        n_results: Number of nearest neighbours to return.
        where: Optional ChromaDB metadata filter dict.
        include: Fields to include in results (default:
                 ``["documents", "metadatas", "distances"]``).

    Returns:
        Dict with ids, documents, metadatas, and distances for each match.
    """
    if collection_name not in COLLECTION_NAMES:
        raise ValueError(
            f"Unknown collection '{collection_name}'. "
            f"Valid: {COLLECTION_NAMES}"
        )

    logger.debug(
        "vector.query",
        collection=collection_name,
        n_results=n_results,
    )
    import asyncio

    default_include = include or ["documents", "metadatas", "distances"]

    def _query() -> dict[str, Any]:
        col = _get_collection(collection_name)
        query_kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": default_include,
        }
        if where:
            query_kwargs["where"] = where

        results = col.query(**query_kwargs)

        # Flatten the nested lists (ChromaDB returns list-of-lists)
        return {
            "ids": results.get("ids", [[]])[0],
            "documents": results.get("documents", [[]])[0],
            "metadatas": results.get("metadatas", [[]])[0],
            "distances": results.get("distances", [[]])[0],
        }

    raw = await asyncio.to_thread(_query)

    matches: list[dict[str, Any]] = []
    for i in range(len(raw["ids"])):
        matches.append({
            "id": raw["ids"][i],
            "document": raw["documents"][i] if raw["documents"] else None,
            "metadata": raw["metadatas"][i] if raw["metadatas"] else None,
            "distance": raw["distances"][i] if raw["distances"] else None,
        })

    return {
        "collection": collection_name,
        "query_results": n_results,
        "matches": matches,
    }


# ------------------------------------------------------------------
# Delete
# ------------------------------------------------------------------

async def delete_embedding(
    collection_name: str,
    doc_id: str,
) -> dict[str, Any]:
    """Delete an embedding from a ChromaDB collection.

    Args:
        collection_name: Collection containing the document.
        doc_id: Document ID to remove.

    Returns:
        Dict confirming the deletion.
    """
    if collection_name not in COLLECTION_NAMES:
        raise ValueError(
            f"Unknown collection '{collection_name}'. "
            f"Valid: {COLLECTION_NAMES}"
        )

    logger.debug("vector.delete", collection=collection_name, doc_id=doc_id)
    import asyncio

    def _delete() -> None:
        col = _get_collection(collection_name)
        col.delete(ids=[doc_id])

    await asyncio.to_thread(_delete)

    return {
        "status": "deleted",
        "collection": collection_name,
        "doc_id": doc_id,
    }
