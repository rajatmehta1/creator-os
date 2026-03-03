"""YouTube Analytics API client for channel and video performance data."""

from datetime import date, datetime
from typing import Any, Optional

import httpx
import structlog

from app.config import get_settings
from app.utils.cache import cached

logger = structlog.get_logger()

YOUTUBE_ANALYTICS_API_BASE = "https://youtubeanalytics.googleapis.com/v2/reports"
YOUTUBE_DATA_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeAnalyticsClient:
    """Async client for the YouTube Analytics API.

    Uses OAuth2 bearer tokens for authenticated access to channel analytics,
    video performance data, demographics, traffic sources, and retention curves.
    """

    def __init__(self, access_token: str) -> None:
        self._access_token = access_token
        self._settings = get_settings()

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
        }

    async def _analytics_request(
        self,
        params: dict[str, Any],
        *,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Execute a request against the YouTube Analytics API."""
        async with httpx.AsyncClient() as client:
            logger.debug(
                "youtube_analytics.request",
                metrics=params.get("metrics"),
                dimensions=params.get("dimensions"),
            )
            response = await client.get(
                YOUTUBE_ANALYTICS_API_BASE,
                params=params,
                headers=self._auth_headers(),
                timeout=timeout,
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            logger.debug(
                "youtube_analytics.response",
                row_count=len(data.get("rows", [])),
            )
            return data

    async def _data_request(
        self,
        endpoint: str,
        params: dict[str, Any],
        *,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Execute a request against the YouTube Data API v3."""
        url = f"{YOUTUBE_DATA_API_BASE}/{endpoint}"
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                params=params,
                headers=self._auth_headers(),
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()

    # ------------------------------------------------------------------
    # Channel-level analytics
    # ------------------------------------------------------------------

    @cached("youtube:analytics")
    async def get_channel_analytics(
        self,
        channel_id: str,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Retrieve aggregate channel analytics for a date range.

        Returns views, watch time, subscribers gained/lost, estimated revenue,
        impressions, CTR, and average view duration aggregated over the range.
        """
        logger.info(
            "youtube_analytics.channel",
            channel_id=channel_id,
            start=str(start_date),
            end=str(end_date),
        )
        params: dict[str, Any] = {
            "ids": f"channel=={channel_id}",
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "metrics": ",".join([
                "views",
                "estimatedMinutesWatched",
                "averageViewDuration",
                "subscribersGained",
                "subscribersLost",
                "likes",
                "dislikes",
                "comments",
                "shares",
                "impressions",
                "impressionClickThroughRate",
                "estimatedRevenue",
            ]),
            "dimensions": "day",
            "sort": "day",
        }
        raw = await self._analytics_request(params)
        return self._format_channel_analytics(raw, channel_id, start_date, end_date)

    # ------------------------------------------------------------------
    # Video-level analytics
    # ------------------------------------------------------------------

    @cached("youtube:analytics")
    async def get_video_analytics(self, video_id: str) -> dict[str, Any]:
        """Retrieve lifetime analytics for a specific video.

        Returns core metrics (views, watch time, engagement) as well as
        traffic sources and audience retention data.
        """
        logger.info("youtube_analytics.video", video_id=video_id)

        # Fetch lifetime stats via Data API for the basics
        data_response = await self._data_request("videos", {
            "part": "statistics,contentDetails,snippet",
            "id": video_id,
        })

        items = data_response.get("items", [])
        if not items:
            logger.warning("youtube_analytics.video_not_found", video_id=video_id)
            return {"video_id": video_id, "found": False}

        item = items[0]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        content_details = item.get("contentDetails", {})

        # Fetch analytics metrics via Analytics API
        publish_date_str = snippet.get("publishedAt", "")
        try:
            publish_date = datetime.fromisoformat(
                publish_date_str.replace("Z", "+00:00")
            ).date()
        except (ValueError, AttributeError):
            publish_date = date(2020, 1, 1)

        analytics_params: dict[str, Any] = {
            "ids": f"channel=={snippet.get('channelId', '')}",
            "startDate": publish_date.isoformat(),
            "endDate": date.today().isoformat(),
            "metrics": ",".join([
                "views",
                "estimatedMinutesWatched",
                "averageViewDuration",
                "averageViewPercentage",
                "likes",
                "comments",
                "shares",
                "subscribersGained",
                "subscribersLost",
                "impressions",
                "impressionClickThroughRate",
                "estimatedRevenue",
            ]),
            "filters": f"video=={video_id}",
        }

        try:
            analytics_raw = await self._analytics_request(analytics_params)
        except httpx.HTTPStatusError:
            logger.warning("youtube_analytics.analytics_api_error", video_id=video_id)
            analytics_raw = {"rows": []}

        return self._format_video_analytics(
            video_id, snippet, stats, content_details, analytics_raw
        )

    # ------------------------------------------------------------------
    # Demographics
    # ------------------------------------------------------------------

    @cached("youtube:analytics")
    async def get_demographics(self, channel_id: str) -> dict[str, Any]:
        """Retrieve audience demographics (age group and gender) for a channel."""
        logger.info("youtube_analytics.demographics", channel_id=channel_id)

        params: dict[str, Any] = {
            "ids": f"channel=={channel_id}",
            "startDate": "2020-01-01",
            "endDate": date.today().isoformat(),
            "metrics": "viewerPercentage",
            "dimensions": "ageGroup,gender",
            "sort": "gender,ageGroup",
        }

        raw = await self._analytics_request(params)
        rows = raw.get("rows", [])

        demographics: dict[str, Any] = {
            "channel_id": channel_id,
            "age_groups": {},
            "gender_split": {},
            "breakdown": [],
        }

        gender_totals: dict[str, float] = {}
        age_totals: dict[str, float] = {}

        for row in rows:
            age_group = row[0] if len(row) > 0 else "unknown"
            gender = row[1] if len(row) > 1 else "unknown"
            percentage = row[2] if len(row) > 2 else 0.0

            demographics["breakdown"].append({
                "age_group": age_group,
                "gender": gender,
                "viewer_percentage": percentage,
            })

            gender_totals[gender] = gender_totals.get(gender, 0.0) + percentage
            age_totals[age_group] = age_totals.get(age_group, 0.0) + percentage

        demographics["gender_split"] = gender_totals
        demographics["age_groups"] = age_totals
        return demographics

    # ------------------------------------------------------------------
    # Traffic sources
    # ------------------------------------------------------------------

    @cached("youtube:analytics")
    async def get_traffic_sources(self, video_id: str) -> dict[str, Any]:
        """Retrieve traffic source breakdown for a specific video."""
        logger.info("youtube_analytics.traffic_sources", video_id=video_id)

        # We need the channel ID to query analytics; fetch from Data API
        data_response = await self._data_request("videos", {
            "part": "snippet",
            "id": video_id,
        })
        items = data_response.get("items", [])
        if not items:
            return {"video_id": video_id, "sources": []}

        channel_id = items[0]["snippet"]["channelId"]

        params: dict[str, Any] = {
            "ids": f"channel=={channel_id}",
            "startDate": "2020-01-01",
            "endDate": date.today().isoformat(),
            "metrics": "views,estimatedMinutesWatched",
            "dimensions": "insightTrafficSourceType",
            "filters": f"video=={video_id}",
            "sort": "-views",
        }

        raw = await self._analytics_request(params)
        rows = raw.get("rows", [])

        total_views = sum(r[1] for r in rows if len(r) > 1)
        sources = []
        for row in rows:
            source_type = row[0] if len(row) > 0 else "unknown"
            views = row[1] if len(row) > 1 else 0
            watch_minutes = row[2] if len(row) > 2 else 0.0
            sources.append({
                "source_type": source_type,
                "views": views,
                "watch_time_minutes": watch_minutes,
                "percentage": round(views / total_views * 100, 2) if total_views else 0.0,
            })

        return {
            "video_id": video_id,
            "total_views": total_views,
            "sources": sources,
        }

    # ------------------------------------------------------------------
    # Audience retention curve
    # ------------------------------------------------------------------

    @cached("youtube:analytics")
    async def get_retention_curve(self, video_id: str) -> dict[str, Any]:
        """Retrieve the audience retention curve for a specific video.

        Returns elapsed-time-ratio vs. audience-retention-percentage data points,
        which represent the percentage of viewers still watching at each point.
        """
        logger.info("youtube_analytics.retention", video_id=video_id)

        # Resolve channel ID
        data_response = await self._data_request("videos", {
            "part": "snippet,contentDetails",
            "id": video_id,
        })
        items = data_response.get("items", [])
        if not items:
            return {"video_id": video_id, "curve": []}

        channel_id = items[0]["snippet"]["channelId"]
        duration_iso = items[0].get("contentDetails", {}).get("duration", "PT0S")

        params: dict[str, Any] = {
            "ids": f"channel=={channel_id}",
            "startDate": "2020-01-01",
            "endDate": date.today().isoformat(),
            "metrics": "audienceWatchRatio,relativeRetentionPerformance",
            "dimensions": "elapsedVideoTimeRatio",
            "filters": f"video=={video_id}",
            "sort": "elapsedVideoTimeRatio",
        }

        try:
            raw = await self._analytics_request(params)
        except httpx.HTTPStatusError:
            logger.warning(
                "youtube_analytics.retention_unavailable", video_id=video_id
            )
            return {"video_id": video_id, "curve": [], "available": False}

        rows = raw.get("rows", [])
        curve = []
        for row in rows:
            elapsed_ratio = row[0] if len(row) > 0 else 0.0
            watch_ratio = row[1] if len(row) > 1 else 0.0
            relative_retention = row[2] if len(row) > 2 else 0.0
            curve.append({
                "elapsed_ratio": elapsed_ratio,
                "audience_watch_ratio": watch_ratio,
                "relative_retention": relative_retention,
            })

        return {
            "video_id": video_id,
            "duration_iso": duration_iso,
            "data_points": len(curve),
            "curve": curve,
        }

    # ------------------------------------------------------------------
    # Private formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_channel_analytics(
        raw: dict[str, Any],
        channel_id: str,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Transform raw Analytics API response into a structured dict."""
        column_headers = [h.get("name", "") for h in raw.get("columnHeaders", [])]
        rows = raw.get("rows", [])

        daily_data: list[dict[str, Any]] = []
        totals: dict[str, float] = {}

        for row in rows:
            entry: dict[str, Any] = {}
            for i, header in enumerate(column_headers):
                value = row[i] if i < len(row) else 0
                entry[header] = value
                if header != "day":
                    totals[header] = totals.get(header, 0) + (
                        float(value) if value is not None else 0.0
                    )
            daily_data.append(entry)

        num_days = max(len(rows), 1)
        averages = {k: round(v / num_days, 4) for k, v in totals.items()}

        return {
            "channel_id": channel_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "totals": totals,
            "daily_averages": averages,
            "daily": daily_data,
        }

    @staticmethod
    def _format_video_analytics(
        video_id: str,
        snippet: dict[str, Any],
        stats: dict[str, Any],
        content_details: dict[str, Any],
        analytics_raw: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge Data API and Analytics API responses into a unified video report."""
        analytics_rows = analytics_raw.get("rows", [])
        analytics_columns = [
            h.get("name", "") for h in analytics_raw.get("columnHeaders", [])
        ]

        analytics_totals: dict[str, Any] = {}
        if analytics_rows:
            row = analytics_rows[0]
            for i, header in enumerate(analytics_columns):
                analytics_totals[header] = row[i] if i < len(row) else 0

        return {
            "video_id": video_id,
            "found": True,
            "title": snippet.get("title", ""),
            "channel_id": snippet.get("channelId", ""),
            "published_at": snippet.get("publishedAt", ""),
            "duration": content_details.get("duration", ""),
            "statistics": {
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "favorites": int(stats.get("favoriteCount", 0)),
            },
            "analytics": analytics_totals,
        }
