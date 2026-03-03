"""Knowledge graph module -- Neo4j-backed content intelligence layer.

Provides topic mapping, content gap analysis, compounding opportunity
detection, and hybrid search (vector + graph) for Creator OS.
"""

from app.knowledge_graph.client import Neo4jClient, get_neo4j_client
from app.knowledge_graph.ingestion import ingest_content
from app.knowledge_graph.schemas import (
    AudienceSegmentNode,
    ContentNode,
    CreatorNode,
    IdeaNode,
    KeywordNode,
    TopicNode,
    TrendNode,
)
from app.knowledge_graph.search import hybrid_search

__all__ = [
    # Client
    "Neo4jClient",
    "get_neo4j_client",
    # Node schemas
    "CreatorNode",
    "ContentNode",
    "TopicNode",
    "KeywordNode",
    "TrendNode",
    "AudienceSegmentNode",
    "IdeaNode",
    # Pipeline
    "ingest_content",
    # Search
    "hybrid_search",
]
