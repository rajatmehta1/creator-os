"""Knowledge Graph API endpoints."""

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import DbSession

router = APIRouter()


@router.get("/topics")
async def get_topic_map(db: DbSession) -> dict:
    """Get the creator's topic map from knowledge graph."""
    # TODO: Query Neo4j for creator's topic relationships
    return {"topics": [], "relationships": []}


@router.get("/content-map")
async def get_content_map(db: DbSession) -> dict:
    """Get content relationship visualization data."""
    return {"nodes": [], "edges": []}


@router.get("/gaps")
async def get_content_gaps(db: DbSession) -> list[dict]:
    """Get content gap analysis from knowledge graph."""
    return []


@router.post("/search")
async def semantic_search(
    query: str,
    db: DbSession,
    top_k: int = Query(default=10, le=50),
) -> list[dict]:
    """Semantic search across all content using hybrid search."""
    from app.knowledge_graph.search import hybrid_search

    try:
        results = await hybrid_search(query=query, creator_id="", top_k=top_k)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )
