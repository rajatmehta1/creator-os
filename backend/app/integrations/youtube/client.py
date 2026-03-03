"""YouTube Data API v3 client."""

from typing import Any, Optional

import httpx
import structlog

from app.config import get_settings
from app.utils.cache import cached

logger = structlog.get_logger()

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeClient:
    """Async client for YouTube Data API v3."""

    def __init__(self, access_token: Optional[str] = None) -> None:
        settings = get_settings()
        self.api_key = settings.youtube_api_key
        self.access_token = access_token

    def _get_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def _get_params(self, params: dict) -> dict:
        if not self.access_token and self.api_key:
            params["key"] = self.api_key
        return params

    async def _request(self, endpoint: str, params: dict) -> dict[str, Any]:
        url = f"{YOUTUBE_API_BASE}/{endpoint}"
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                params=self._get_params(params),
                headers=self._get_headers(),
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    @cached("youtube:channel")
    async def get_channel_info(self, channel_id: str) -> dict[str, Any]:
        """Get channel statistics and snippet."""
        return await self._request("channels", {
            "part": "snippet,statistics,brandingSettings",
            "id": channel_id,
        })

    @cached("youtube:channel")
    async def get_my_channel(self) -> dict[str, Any]:
        """Get the authenticated user's channel."""
        return await self._request("channels", {
            "part": "snippet,statistics,brandingSettings",
            "mine": "true",
        })

    @cached("youtube:video")
    async def get_video_details(self, video_id: str) -> dict[str, Any]:
        """Get detailed info for a specific video."""
        return await self._request("videos", {
            "part": "snippet,statistics,contentDetails,topicDetails",
            "id": video_id,
        })

    async def list_channel_videos(
        self,
        channel_id: str,
        max_results: int = 50,
        page_token: Optional[str] = None,
    ) -> dict[str, Any]:
        """List videos from a channel."""
        params: dict[str, Any] = {
            "part": "snippet",
            "channelId": channel_id,
            "type": "video",
            "order": "date",
            "maxResults": max_results,
        }
        if page_token:
            params["pageToken"] = page_token
        return await self._request("search", params)

    async def get_video_captions(self, video_id: str) -> dict[str, Any]:
        """List available captions for a video."""
        return await self._request("captions", {
            "part": "snippet",
            "videoId": video_id,
        })

    @cached("youtube:search")
    async def search_videos(
        self,
        query: str,
        max_results: int = 10,
        order: str = "relevance",
    ) -> dict[str, Any]:
        """Search YouTube videos."""
        return await self._request("search", {
            "part": "snippet",
            "q": query,
            "type": "video",
            "order": order,
            "maxResults": max_results,
        })

    async def get_trending_videos(
        self,
        region_code: str = "US",
        category_id: Optional[str] = None,
        max_results: int = 50,
    ) -> dict[str, Any]:
        """Get trending videos."""
        params: dict[str, Any] = {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": region_code,
            "maxResults": max_results,
        }
        if category_id:
            params["videoCategoryId"] = category_id
        return await self._request("videos", params)
