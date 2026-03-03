"""LangChain tool wrappers for trend data sources.

Provides agents with access to Google Trends, Reddit hot posts, and
NewsAPI article search.  Each tool is async and delegates to the
corresponding integration module.
"""

from typing import Any

import structlog
from langchain_core.tools import tool

from app.integrations import google_trends, reddit, news

logger = structlog.get_logger()


@tool
async def get_google_trends(
    keywords: list[str],
    timeframe: str = "today 3-m",
) -> dict[str, Any]:
    """Get Google Trends data for one or more keywords.

    Returns trending searches, rising queries, and interest-over-time
    data from Google Trends.

    Args:
        keywords: List of search terms to analyse (up to 5).
        timeframe: Time window - "today 3-m", "today 12-m", "now 7-d", etc.

    Returns:
        Dict with three sections:
        - trending_searches: today's trending queries
        - rising_queries: breakout queries per keyword
        - interest_over_time: time series of search interest
    """
    logger.info("tool.get_google_trends", keywords=keywords, timeframe=timeframe)

    trending_searches = await google_trends.get_trending_searches()
    rising_queries = await google_trends.get_rising_queries(
        keywords, timeframe=timeframe
    )
    interest = await google_trends.get_interest_over_time(
        keywords, timeframe=timeframe
    )

    return {
        "keywords": keywords,
        "timeframe": timeframe,
        "trending_searches": trending_searches[:30],
        "rising_queries": rising_queries,
        "interest_over_time": interest,
    }


@tool
async def get_reddit_hot(
    subreddit: str,
    limit: int = 25,
) -> dict[str, Any]:
    """Get hot and rising posts from a Reddit subreddit.

    Args:
        subreddit: Subreddit name without "r/" prefix (e.g. "technology").
        limit: Number of posts to fetch per category (max 100).

    Returns:
        Dict with hot_posts and rising_posts lists containing titles,
        scores, comment counts, and URLs.
    """
    logger.info("tool.get_reddit_hot", subreddit=subreddit, limit=limit)

    hot_posts = await reddit.get_hot_posts(subreddit, limit=limit)
    rising_posts = await reddit.get_rising_posts(subreddit, limit=limit)

    return {
        "subreddit": subreddit,
        "hot_posts": hot_posts,
        "rising_posts": rising_posts,
        "total": len(hot_posts) + len(rising_posts),
    }


@tool
async def search_news_articles(
    query: str,
    days: int = 7,
) -> dict[str, Any]:
    """Search for recent news articles on a topic.

    Uses the NewsAPI to find relevant articles from thousands of sources.

    Args:
        query: Search query string.
        days: How many days back to search (default 7).

    Returns:
        Dict with total_results count and articles list containing
        title, description, source, URL, and published date.
    """
    logger.info("tool.search_news_articles", query=query, days=days)

    result = await news.search_news(query, days=days)

    return {
        "query": query,
        "days": days,
        "total_results": result.get("total_results", 0),
        "articles": result.get("articles", []),
    }
