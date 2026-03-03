"""LangChain tool wrappers for the YouTube Data API v3.

These tools provide agents with the ability to search YouTube, retrieve
trending videos, fetch video details, and pull channel statistics.  All
functions are async and delegate to the existing ``YouTubeClient``.
"""

from typing import Any, Optional

import structlog
from langchain_core.tools import tool

from app.integrations.youtube.client import YouTubeClient

logger = structlog.get_logger()


@tool
async def search_youtube(
    query: str,
    max_results: int = 10,
    order: str = "relevance",
) -> dict[str, Any]:
    """Search YouTube for videos matching a query.

    Args:
        query: Search terms (e.g. "python tutorial beginners").
        max_results: Number of results to return (1-50).
        order: Sort order - "relevance", "date", "viewCount", "rating".

    Returns:
        Dict containing a list of video snippets with video IDs, titles,
        descriptions, channel info, and publish dates.
    """
    logger.info("tool.search_youtube", query=query, max_results=max_results)
    client = YouTubeClient()
    raw = await client.search_videos(query, max_results=max_results, order=order)

    items = raw.get("items", [])
    results = []
    for item in items:
        snippet = item.get("snippet", {})
        results.append({
            "video_id": item.get("id", {}).get("videoId", ""),
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "channel_id": snippet.get("channelId", ""),
            "published_at": snippet.get("publishedAt", ""),
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
        })

    return {
        "query": query,
        "total_results": raw.get("pageInfo", {}).get("totalResults", 0),
        "results": results,
    }


@tool
async def get_trending_videos(
    region_code: str = "US",
    category_id: Optional[str] = None,
    max_results: int = 25,
) -> dict[str, Any]:
    """Get currently trending videos on YouTube.

    Args:
        region_code: ISO 3166-1 alpha-2 country code (default "US").
        category_id: Optional YouTube category ID to filter by.
        max_results: Number of trending videos (1-50).

    Returns:
        Dict containing trending video snippets with stats.
    """
    logger.info(
        "tool.get_trending_videos",
        region=region_code,
        category=category_id,
    )
    client = YouTubeClient()
    raw = await client.get_trending_videos(
        region_code=region_code,
        category_id=category_id,
        max_results=max_results,
    )

    items = raw.get("items", [])
    results = []
    for item in items:
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        results.append({
            "video_id": item.get("id", ""),
            "title": snippet.get("title", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "category_id": snippet.get("categoryId", ""),
            "published_at": snippet.get("publishedAt", ""),
            "tags": snippet.get("tags", []),
            "view_count": int(stats.get("viewCount", 0)),
            "like_count": int(stats.get("likeCount", 0)),
            "comment_count": int(stats.get("commentCount", 0)),
        })

    return {"region": region_code, "trending": results}


@tool
async def get_video_details(video_id: str) -> dict[str, Any]:
    """Get detailed information about a specific YouTube video.

    Args:
        video_id: The YouTube video ID (e.g. "dQw4w9WgXcQ").

    Returns:
        Dict with full video metadata including snippet, statistics,
        content details, and topic information.
    """
    logger.info("tool.get_video_details", video_id=video_id)
    client = YouTubeClient()
    raw = await client.get_video_details(video_id)

    items = raw.get("items", [])
    if not items:
        return {"video_id": video_id, "found": False}

    item = items[0]
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    content = item.get("contentDetails", {})
    topics = item.get("topicDetails", {})

    return {
        "video_id": video_id,
        "found": True,
        "title": snippet.get("title", ""),
        "description": snippet.get("description", ""),
        "channel_id": snippet.get("channelId", ""),
        "channel_title": snippet.get("channelTitle", ""),
        "published_at": snippet.get("publishedAt", ""),
        "tags": snippet.get("tags", []),
        "category_id": snippet.get("categoryId", ""),
        "duration": content.get("duration", ""),
        "definition": content.get("definition", ""),
        "view_count": int(stats.get("viewCount", 0)),
        "like_count": int(stats.get("likeCount", 0)),
        "comment_count": int(stats.get("commentCount", 0)),
        "favorite_count": int(stats.get("favoriteCount", 0)),
        "topic_categories": topics.get("topicCategories", []),
    }


@tool
async def get_channel_stats(channel_id: str) -> dict[str, Any]:
    """Get statistics and metadata for a YouTube channel.

    Args:
        channel_id: The YouTube channel ID (e.g. "UCxxxxxx").

    Returns:
        Dict with channel snippet, subscriber count, video count,
        total views, and branding settings.
    """
    logger.info("tool.get_channel_stats", channel_id=channel_id)
    client = YouTubeClient()
    raw = await client.get_channel_info(channel_id)

    items = raw.get("items", [])
    if not items:
        return {"channel_id": channel_id, "found": False}

    item = items[0]
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    branding = item.get("brandingSettings", {}).get("channel", {})

    return {
        "channel_id": channel_id,
        "found": True,
        "title": snippet.get("title", ""),
        "description": snippet.get("description", ""),
        "custom_url": snippet.get("customUrl", ""),
        "country": snippet.get("country", ""),
        "published_at": snippet.get("publishedAt", ""),
        "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
        "subscriber_count": int(stats.get("subscriberCount", 0)),
        "video_count": int(stats.get("videoCount", 0)),
        "view_count": int(stats.get("viewCount", 0)),
        "keywords": branding.get("keywords", ""),
    }
