"""YouTube OAuth2 flow handler."""

import base64
import json
from typing import Any

from cryptography.fernet import Fernet
import httpx
import structlog

from app.config import Settings

logger = structlog.get_logger()

YOUTUBE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
YOUTUBE_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def generate_auth_url(settings: Settings) -> str:
    """Generate the YouTube OAuth authorization URL."""
    params = {
        "client_id": settings.youtube_client_id,
        "redirect_uri": settings.youtube_redirect_uri,
        "response_type": "code",
        "scope": " ".join(YOUTUBE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{YOUTUBE_AUTH_URL}?{query}"


async def exchange_code(code: str, settings: Settings) -> dict[str, Any]:
    """Exchange the authorization code for access and refresh tokens."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            YOUTUBE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.youtube_client_id,
                "client_secret": settings.youtube_client_secret,
                "redirect_uri": settings.youtube_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        tokens = response.json()
        logger.info("youtube.tokens_exchanged")
        return tokens


async def refresh_access_token(refresh_token: str, settings: Settings) -> dict[str, Any]:
    """Refresh an expired access token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            YOUTUBE_TOKEN_URL,
            data={
                "refresh_token": refresh_token,
                "client_id": settings.youtube_client_id,
                "client_secret": settings.youtube_client_secret,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        return response.json()


def encrypt_tokens(tokens: dict, secret_key: str) -> str:
    """Encrypt OAuth tokens for storage."""
    key = base64.urlsafe_b64encode(secret_key.encode().ljust(32)[:32])
    f = Fernet(key)
    return f.encrypt(json.dumps(tokens).encode()).decode()


def decrypt_tokens(encrypted: str, secret_key: str) -> dict:
    """Decrypt stored OAuth tokens."""
    key = base64.urlsafe_b64encode(secret_key.encode().ljust(32)[:32])
    f = Fernet(key)
    return json.loads(f.decrypt(encrypted.encode()).decode())
