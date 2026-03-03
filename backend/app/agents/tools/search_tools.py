"""LangChain tool wrapper for Google Custom Search API."""

from typing import Any, Optional

import httpx
import structlog
from langchain_core.tools import tool

from app.config import get_settings

logger = structlog.get_logger()

GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"


@tool
async def google_search(
    query: str,
    num_results: int = 10,
    date_restrict: Optional[str] = None,
    site_search: Optional[str] = None,
) -> dict[str, Any]:
    """Search the web using Google Custom Search API.

    Performs a Google web search and returns structured results including
    titles, snippets, URLs, and metadata.

    Args:
        query: The search query string.
        num_results: Number of results to return (1-10 per page).
        date_restrict: Optional recency filter, e.g. "d7" (past 7 days),
                       "m1" (past month), "y1" (past year).
        site_search: Optional domain to restrict search to (e.g.
                     "youtube.com").

    Returns:
        Dict with search metadata and a list of result items, each
        containing title, link, snippet, and display link.
    """
    settings = get_settings()

    if not settings.google_search_api_key or not settings.google_search_cx:
        logger.warning("tool.google_search.missing_credentials")
        return {
            "query": query,
            "total_results": 0,
            "items": [],
            "error": "Google Search API key or CX not configured",
        }

    logger.info(
        "tool.google_search",
        query=query,
        num_results=num_results,
        date_restrict=date_restrict,
    )

    params: dict[str, Any] = {
        "key": settings.google_search_api_key,
        "cx": settings.google_search_cx,
        "q": query,
        "num": min(num_results, 10),
    }

    if date_restrict:
        params["dateRestrict"] = date_restrict
    if site_search:
        params["siteSearch"] = site_search

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                GOOGLE_CSE_URL,
                params=params,
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "tool.google_search.api_error",
            status=exc.response.status_code,
            detail=exc.response.text[:200],
        )
        return {
            "query": query,
            "total_results": 0,
            "items": [],
            "error": f"Google API returned {exc.response.status_code}",
        }
    except httpx.RequestError as exc:
        logger.error("tool.google_search.request_error", error=str(exc))
        return {
            "query": query,
            "total_results": 0,
            "items": [],
            "error": str(exc),
        }

    search_info = data.get("searchInformation", {})
    raw_items = data.get("items", [])

    items = []
    for item in raw_items:
        items.append({
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "snippet": item.get("snippet", ""),
            "display_link": item.get("displayLink", ""),
            "formatted_url": item.get("formattedUrl", ""),
            "page_map": _extract_pagemap(item.get("pagemap", {})),
        })

    result = {
        "query": query,
        "total_results": int(search_info.get("totalResults", 0)),
        "search_time": float(search_info.get("searchTime", 0)),
        "items": items,
    }

    logger.info(
        "tool.google_search.complete",
        query=query,
        results=len(items),
    )
    return result


def _extract_pagemap(pagemap: dict[str, Any]) -> dict[str, Any]:
    """Extract useful metadata from the Google CSE pagemap object."""
    extracted: dict[str, Any] = {}

    # Open Graph / metatags
    metatags = pagemap.get("metatags", [])
    if metatags:
        meta = metatags[0]
        extracted["og_title"] = meta.get("og:title", "")
        extracted["og_description"] = meta.get("og:description", "")
        extracted["og_image"] = meta.get("og:image", "")
        extracted["og_type"] = meta.get("og:type", "")

    # Thumbnail image
    cse_images = pagemap.get("cse_image", [])
    if cse_images:
        extracted["thumbnail"] = cse_images[0].get("src", "")

    return extracted
