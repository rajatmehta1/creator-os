"""Google Trends integration using pytrends, with Redis caching."""

import asyncio
from typing import Any, Optional

from pytrends.request import TrendReq
import structlog

from app.utils.cache import cached

logger = structlog.get_logger()


def _build_pytrends(
    hl: str = "en-US",
    tz: int = 360,
    timeout: tuple[int, int] = (10, 30),
) -> TrendReq:
    """Create a configured pytrends request object.

    pytrends is synchronous; all public functions wrap calls in
    ``asyncio.to_thread`` so the event loop is never blocked.
    """
    return TrendReq(hl=hl, tz=tz, timeout=timeout)


# ------------------------------------------------------------------
# Rising queries
# ------------------------------------------------------------------

@cached("trends:google")
async def get_rising_queries(
    keywords: list[str],
    timeframe: str = "today 3-m",
) -> dict[str, Any]:
    """Return rising search queries for the given keywords.

    Args:
        keywords: Up to 5 search terms to compare.
        timeframe: pytrends timeframe string (e.g. ``"today 3-m"``,
                   ``"today 12-m"``).

    Returns:
        Dict mapping each keyword to its list of rising queries with
        their ``value`` (growth %) and ``query`` text.
    """
    logger.info("google_trends.rising_queries", keywords=keywords, timeframe=timeframe)

    def _fetch() -> dict[str, Any]:
        pt = _build_pytrends()
        pt.build_payload(keywords[:5], timeframe=timeframe)
        related = pt.related_queries()

        result: dict[str, Any] = {}
        for kw, frames in related.items():
            rising_df = frames.get("rising")
            if rising_df is not None and not rising_df.empty:
                result[kw] = rising_df.to_dict(orient="records")
            else:
                result[kw] = []
        return result

    return await asyncio.to_thread(_fetch)


# ------------------------------------------------------------------
# Trending searches (daily)
# ------------------------------------------------------------------

@cached("trends:google")
async def get_trending_searches(
    country: str = "united_states",
) -> list[str]:
    """Return today's trending searches for a country.

    Args:
        country: Country name in pytrends format (e.g. ``"united_states"``).

    Returns:
        List of trending search term strings.
    """
    logger.info("google_trends.trending_searches", country=country)

    def _fetch() -> list[str]:
        pt = _build_pytrends()
        df = pt.trending_searches(pn=country)
        return df[0].tolist() if not df.empty else []

    return await asyncio.to_thread(_fetch)


# ------------------------------------------------------------------
# Interest over time
# ------------------------------------------------------------------

@cached("trends:google")
async def get_interest_over_time(
    keywords: list[str],
    timeframe: str = "today 3-m",
    geo: str = "",
) -> dict[str, Any]:
    """Return search-interest time-series for each keyword.

    Args:
        keywords: Up to 5 search terms.
        timeframe: pytrends timeframe string.
        geo: Two-letter country code or empty for worldwide.

    Returns:
        Dict with ``dates`` (list of ISO date strings) and a nested dict
        per keyword containing its interest values.
    """
    logger.info(
        "google_trends.interest_over_time",
        keywords=keywords,
        timeframe=timeframe,
        geo=geo,
    )

    def _fetch() -> dict[str, Any]:
        pt = _build_pytrends()
        pt.build_payload(keywords[:5], timeframe=timeframe, geo=geo)
        df = pt.interest_over_time()

        if df.empty:
            return {"dates": [], "series": {}}

        # Drop the ``isPartial`` column added by pytrends
        if "isPartial" in df.columns:
            df = df.drop(columns=["isPartial"])

        dates = [d.isoformat() for d in df.index]
        series = {col: df[col].tolist() for col in df.columns}
        return {"dates": dates, "series": series}

    return await asyncio.to_thread(_fetch)


# ------------------------------------------------------------------
# Related topics
# ------------------------------------------------------------------

@cached("trends:google")
async def get_related_topics(
    keyword: str,
    timeframe: str = "today 3-m",
) -> dict[str, Any]:
    """Return related topics (top & rising) for a single keyword.

    Args:
        keyword: A single search term.
        timeframe: pytrends timeframe string.

    Returns:
        Dict with ``top`` and ``rising`` keys, each containing a list of
        topic dicts with ``title``, ``type``, and ``value``.
    """
    logger.info("google_trends.related_topics", keyword=keyword, timeframe=timeframe)

    def _fetch() -> dict[str, Any]:
        pt = _build_pytrends()
        pt.build_payload([keyword], timeframe=timeframe)
        related = pt.related_topics()

        kw_data = related.get(keyword, {})
        result: dict[str, Any] = {"top": [], "rising": []}

        for category in ("top", "rising"):
            df = kw_data.get(category)
            if df is not None and not df.empty:
                records = df.to_dict(orient="records")
                result[category] = [
                    {
                        "title": r.get("topic_title", ""),
                        "type": r.get("topic_type", ""),
                        "value": r.get("value", 0),
                    }
                    for r in records
                ]
        return result

    return await asyncio.to_thread(_fetch)
