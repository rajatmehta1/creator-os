"""LangChain tool wrappers for Creator OS agents.

Each sub-module exposes ``@tool``-decorated async functions that agents
can call during graph execution.  The tools are thin wrappers around
the project's integration clients, services, and external APIs.

Modules:
    youtube_tools  - YouTube Data API search and stats
    trend_tools    - Google Trends, Reddit, and NewsAPI
    search_tools   - Google Custom Search
    neo4j_tools    - Knowledge-graph queries (Neo4j)
    vector_tools   - ChromaDB vector store operations
"""

from app.agents.tools.youtube_tools import (
    get_channel_stats,
    get_trending_videos,
    get_video_details,
    search_youtube,
)
from app.agents.tools.trend_tools import (
    get_google_trends,
    get_reddit_hot,
    search_news_articles,
)
from app.agents.tools.search_tools import google_search
from app.agents.tools.neo4j_tools import (
    query_content_gaps,
    query_related_content,
    query_topic_authority,
    search_knowledge_graph,
)
from app.agents.tools.vector_tools import (
    delete_embedding,
    init_collections,
    query_similar,
    upsert_embedding,
)

__all__ = [
    # YouTube
    "search_youtube",
    "get_trending_videos",
    "get_video_details",
    "get_channel_stats",
    # Trends
    "get_google_trends",
    "get_reddit_hot",
    "search_news_articles",
    # Search
    "google_search",
    # Neo4j
    "query_content_gaps",
    "query_topic_authority",
    "query_related_content",
    "search_knowledge_graph",
    # Vector
    "init_collections",
    "upsert_embedding",
    "query_similar",
    "delete_embedding",
]
