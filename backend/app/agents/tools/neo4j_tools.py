"""LangChain tool wrappers for Neo4j knowledge-graph queries.

Provides agents with the ability to query content gaps, topic authority,
related content, and perform free-text knowledge graph searches.  All
queries run against the Creator OS Neo4j instance configured in settings.
"""

from typing import Any, Optional

import structlog
from langchain_core.tools import tool
from neo4j import AsyncGraphDatabase

from app.config import get_settings

logger = structlog.get_logger()


async def _get_driver() -> AsyncGraphDatabase.driver:
    """Create an async Neo4j driver from application settings."""
    settings = get_settings()
    return AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


async def _run_query(
    query: str,
    params: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Execute a Cypher query and return results as a list of dicts."""
    driver = await _get_driver()
    try:
        async with driver.session() as session:
            result = await session.run(query, parameters=params or {})
            records = [record.data() async for record in result]
            return records
    finally:
        await driver.close()


# ------------------------------------------------------------------
# Content Gaps
# ------------------------------------------------------------------

@tool
async def query_content_gaps(
    niche: str,
    existing_topics: list[str],
    limit: int = 10,
) -> dict[str, Any]:
    """Find content gaps by comparing niche topics against existing content.

    Queries the knowledge graph for topics that are trending or in-demand
    within a niche but have NOT been covered by the creator yet.

    Args:
        niche: The creator's niche (e.g. "machine learning", "cooking").
        existing_topics: Topics the creator has already covered.
        limit: Maximum number of gap topics to return.

    Returns:
        Dict with gap_topics list and niche context.
    """
    logger.info(
        "tool.query_content_gaps",
        niche=niche,
        existing_count=len(existing_topics),
    )

    cypher = """
    MATCH (t:Topic)-[:BELONGS_TO]->(n:Niche {name: $niche})
    WHERE NOT t.name IN $existing_topics
    OPTIONAL MATCH (t)<-[:COVERS]-(c:Content)
    WITH t, count(c) AS coverage
    OPTIONAL MATCH (t)<-[:RELATES_TO]-(tr:Trend)
    WITH t, coverage, count(tr) AS trend_count
    RETURN t.name AS topic,
           t.description AS description,
           coverage,
           trend_count,
           t.demand_score AS demand_score
    ORDER BY trend_count DESC, t.demand_score DESC
    LIMIT $limit
    """

    try:
        records = await _run_query(cypher, {
            "niche": niche,
            "existing_topics": existing_topics,
            "limit": limit,
        })
    except Exception as exc:
        logger.error("tool.query_content_gaps.error", error=str(exc))
        return {
            "niche": niche,
            "gap_topics": [],
            "error": str(exc),
        }

    gap_topics = [
        {
            "topic": r.get("topic", ""),
            "description": r.get("description", ""),
            "competitor_coverage": r.get("coverage", 0),
            "trend_signals": r.get("trend_count", 0),
            "demand_score": r.get("demand_score", 0.0),
        }
        for r in records
    ]

    return {
        "niche": niche,
        "gap_topics": gap_topics,
        "total_gaps": len(gap_topics),
    }


# ------------------------------------------------------------------
# Topic Authority
# ------------------------------------------------------------------

@tool
async def query_topic_authority(
    channel_id: str,
    topic: str,
) -> dict[str, Any]:
    """Assess a creator's authority on a specific topic.

    Looks at the knowledge graph for content nodes linked to the topic
    that belong to the given channel, calculating coverage depth and
    audience engagement signals.

    Args:
        channel_id: YouTube channel ID.
        topic: Topic name to check authority for.

    Returns:
        Dict with authority_score, content_count, and related metrics.
    """
    logger.info(
        "tool.query_topic_authority",
        channel_id=channel_id,
        topic=topic,
    )

    cypher = """
    MATCH (ch:Channel {channel_id: $channel_id})-[:PUBLISHED]->(c:Content)-[:COVERS]->(t:Topic {name: $topic})
    WITH ch, t, collect(c) AS content_list
    UNWIND content_list AS c
    RETURN t.name AS topic,
           count(c) AS content_count,
           avg(c.engagement_rate) AS avg_engagement,
           avg(c.view_count) AS avg_views,
           max(c.published_at) AS last_published,
           sum(c.view_count) AS total_views
    """

    try:
        records = await _run_query(cypher, {
            "channel_id": channel_id,
            "topic": topic,
        })
    except Exception as exc:
        logger.error("tool.query_topic_authority.error", error=str(exc))
        return {
            "channel_id": channel_id,
            "topic": topic,
            "authority_score": 0.0,
            "error": str(exc),
        }

    if not records:
        return {
            "channel_id": channel_id,
            "topic": topic,
            "authority_score": 0.0,
            "content_count": 0,
            "message": "No content found for this topic",
        }

    r = records[0]
    content_count = r.get("content_count", 0)
    avg_engagement = r.get("avg_engagement") or 0.0

    # Heuristic authority score
    authority_score = min(
        round(
            (min(content_count, 20) / 20) * 0.5
            + min(avg_engagement / 0.1, 1.0) * 0.5,
            4,
        ),
        1.0,
    )

    return {
        "channel_id": channel_id,
        "topic": topic,
        "authority_score": authority_score,
        "content_count": content_count,
        "avg_engagement": round(avg_engagement, 6),
        "avg_views": r.get("avg_views", 0),
        "total_views": r.get("total_views", 0),
        "last_published": str(r.get("last_published", "")),
    }


# ------------------------------------------------------------------
# Related Content
# ------------------------------------------------------------------

@tool
async def query_related_content(
    content_id: str,
    limit: int = 10,
) -> dict[str, Any]:
    """Find content pieces related to a given piece via the knowledge graph.

    Traverses topic and tag relationships to find thematically related
    content from the same or other creators.

    Args:
        content_id: UUID of the content piece to find relations for.
        limit: Maximum number of related items.

    Returns:
        Dict with a list of related content items and relationship types.
    """
    logger.info("tool.query_related_content", content_id=content_id, limit=limit)

    cypher = """
    MATCH (source:Content {content_id: $content_id})-[:COVERS]->(t:Topic)<-[:COVERS]-(related:Content)
    WHERE related.content_id <> $content_id
    WITH related, collect(DISTINCT t.name) AS shared_topics, count(t) AS topic_overlap
    RETURN related.content_id AS content_id,
           related.title AS title,
           related.content_type AS content_type,
           related.view_count AS view_count,
           shared_topics,
           topic_overlap
    ORDER BY topic_overlap DESC
    LIMIT $limit
    """

    try:
        records = await _run_query(cypher, {
            "content_id": content_id,
            "limit": limit,
        })
    except Exception as exc:
        logger.error("tool.query_related_content.error", error=str(exc))
        return {
            "source_content_id": content_id,
            "related": [],
            "error": str(exc),
        }

    related = [
        {
            "content_id": r.get("content_id", ""),
            "title": r.get("title", ""),
            "content_type": r.get("content_type", ""),
            "view_count": r.get("view_count", 0),
            "shared_topics": r.get("shared_topics", []),
            "topic_overlap": r.get("topic_overlap", 0),
        }
        for r in records
    ]

    return {
        "source_content_id": content_id,
        "related": related,
        "total": len(related),
    }


# ------------------------------------------------------------------
# Free-text Knowledge Graph Search
# ------------------------------------------------------------------

@tool
async def search_knowledge_graph(
    query: str,
    node_types: Optional[list[str]] = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Search the knowledge graph using a free-text query.

    Performs a full-text search across Topic, Content, Trend, and Channel
    nodes to surface relevant entities.

    Args:
        query: Free-text search string.
        node_types: Optional list of node labels to restrict search
                    (e.g. ["Topic", "Trend"]).
        limit: Maximum results to return.

    Returns:
        Dict with matching nodes grouped by type.
    """
    logger.info(
        "tool.search_knowledge_graph",
        query=query,
        node_types=node_types,
    )

    # Build a UNION query across desired node types
    target_types = node_types or ["Topic", "Content", "Trend", "Channel"]
    union_parts: list[str] = []

    for label in target_types:
        part = f"""
        MATCH (n:{label})
        WHERE toLower(n.name) CONTAINS toLower($query)
           OR toLower(n.title) CONTAINS toLower($query)
           OR toLower(n.description) CONTAINS toLower($query)
        RETURN labels(n)[0] AS node_type,
               n.name AS name,
               n.title AS title,
               n.description AS description,
               properties(n) AS props
        LIMIT $limit
        """
        union_parts.append(part.strip())

    cypher = "\nUNION ALL\n".join(union_parts)

    try:
        records = await _run_query(cypher, {
            "query": query,
            "limit": limit,
        })
    except Exception as exc:
        logger.error("tool.search_knowledge_graph.error", error=str(exc))
        return {"query": query, "results": [], "error": str(exc)}

    # Group by node type
    grouped: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        node_type = r.get("node_type", "Unknown")
        entry = {
            "name": r.get("name") or r.get("title", ""),
            "description": (r.get("description") or "")[:300],
            "properties": {
                k: v
                for k, v in (r.get("props") or {}).items()
                if k not in ("name", "title", "description")
            },
        }
        grouped.setdefault(node_type, []).append(entry)

    return {
        "query": query,
        "results": grouped,
        "total": sum(len(v) for v in grouped.values()),
    }
