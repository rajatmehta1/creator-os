"""News and RSS feed aggregator integration."""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
import structlog
from xml.etree import ElementTree

from app.config import get_settings
from app.utils.cache import cached

logger = structlog.get_logger()

NEWSAPI_BASE = "https://newsapi.org/v2"


# ------------------------------------------------------------------
# NewsAPI search
# ------------------------------------------------------------------

@cached("trends:google", ttl=3600)
async def search_news(
    query: str,
    days: int = 7,
    language: str = "en",
    sort_by: str = "relevancy",
    page_size: int = 20,
) -> dict[str, Any]:
    """Search recent news articles using the NewsAPI ``/everything`` endpoint.

    Args:
        query: Search query string.
        days: Number of days to look back.
        language: Two-letter language code.
        sort_by: One of ``"relevancy"``, ``"popularity"``, ``"publishedAt"``.
        page_size: Number of articles to return (max 100).

    Returns:
        Dict with ``total_results``, ``articles`` list, and ``query`` echo.
    """
    settings = get_settings()
    if not settings.news_api_key:
        logger.warning("news.missing_api_key")
        return {"total_results": 0, "articles": [], "query": query, "error": "NEWS_API_KEY not configured"}

    from_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    logger.info("news.search", query=query, days=days, from_date=from_date)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{NEWSAPI_BASE}/everything",
            params={
                "q": query,
                "from": from_date,
                "language": language,
                "sortBy": sort_by,
                "pageSize": min(page_size, 100),
                "apiKey": settings.news_api_key,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

    articles = []
    for article in data.get("articles", []):
        articles.append({
            "title": article.get("title", ""),
            "description": article.get("description", ""),
            "url": article.get("url", ""),
            "source": article.get("source", {}).get("name", ""),
            "author": article.get("author"),
            "published_at": article.get("publishedAt", ""),
            "image_url": article.get("urlToImage"),
        })

    logger.info("news.search_complete", query=query, result_count=len(articles))
    return {
        "total_results": data.get("totalResults", 0),
        "articles": articles,
        "query": query,
    }


# ------------------------------------------------------------------
# RSS feed fetcher
# ------------------------------------------------------------------

@cached("trends:google", ttl=3600)
async def fetch_rss_feeds(
    urls: list[str],
    max_items_per_feed: int = 20,
) -> list[dict[str, Any]]:
    """Fetch and parse multiple RSS/Atom feeds concurrently.

    Args:
        urls: List of RSS/Atom feed URLs to fetch.
        max_items_per_feed: Maximum number of items to extract per feed.

    Returns:
        Flat list of feed-item dicts containing title, link, summary,
        published date, and source URL.
    """
    logger.info("news.fetch_rss", feed_count=len(urls))

    all_items: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for url in urls:
            try:
                response = await client.get(url)
                response.raise_for_status()
                items = _parse_feed_xml(response.text, url, max_items_per_feed)
                all_items.extend(items)
                logger.debug("news.rss_feed_parsed", url=url, item_count=len(items))
            except httpx.HTTPError as exc:
                logger.warning("news.rss_feed_error", url=url, error=str(exc))
            except ElementTree.ParseError as exc:
                logger.warning("news.rss_parse_error", url=url, error=str(exc))

    # Sort by published date descending (newest first)
    all_items.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    logger.info("news.rss_complete", total_items=len(all_items))
    return all_items


def _parse_feed_xml(
    xml_text: str,
    source_url: str,
    max_items: int,
) -> list[dict[str, Any]]:
    """Parse RSS 2.0 or Atom feed XML into a list of item dicts."""
    root = ElementTree.fromstring(xml_text)
    items: list[dict[str, Any]] = []

    # RSS 2.0 format
    for item_el in root.iter("item"):
        if len(items) >= max_items:
            break
        items.append({
            "title": _get_text(item_el, "title"),
            "link": _get_text(item_el, "link"),
            "summary": _get_text(item_el, "description")[:500],
            "published_at": _get_text(item_el, "pubDate"),
            "source_url": source_url,
            "format": "rss",
        })

    if items:
        return items

    # Atom format
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry_el in root.findall("atom:entry", ns):
        if len(items) >= max_items:
            break
        link_el = entry_el.find("atom:link", ns)
        link_href = link_el.get("href", "") if link_el is not None else ""
        items.append({
            "title": _get_text_ns(entry_el, "atom:title", ns),
            "link": link_href,
            "summary": _get_text_ns(entry_el, "atom:summary", ns)[:500],
            "published_at": _get_text_ns(entry_el, "atom:published", ns)
            or _get_text_ns(entry_el, "atom:updated", ns),
            "source_url": source_url,
            "format": "atom",
        })

    return items


def _get_text(element: ElementTree.Element, tag: str) -> str:
    """Safely extract text from a child element."""
    child = element.find(tag)
    return (child.text or "").strip() if child is not None else ""


def _get_text_ns(
    element: ElementTree.Element,
    tag: str,
    ns: dict[str, str],
) -> str:
    """Safely extract text from a namespaced child element."""
    child = element.find(tag, ns)
    return (child.text or "").strip() if child is not None else ""
