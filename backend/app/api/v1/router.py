"""Main API v1 router aggregating all sub-routers."""

from fastapi import APIRouter

from app.api.v1 import (
    analytics,
    auth,
    content,
    graph,
    ideas,
    media_kit,
    orchestrator,
    profile,
    scripts,
    seo,
    trends,
)

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_v1_router.include_router(trends.router, prefix="/trends", tags=["trends"])
api_v1_router.include_router(ideas.router, prefix="/ideas", tags=["ideas"])
api_v1_router.include_router(scripts.router, prefix="/scripts", tags=["scripts"])
api_v1_router.include_router(seo.router, prefix="/seo", tags=["seo"])
api_v1_router.include_router(content.router, prefix="/content", tags=["content"])
api_v1_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_v1_router.include_router(media_kit.router, prefix="/media-kit", tags=["media-kit"])
api_v1_router.include_router(orchestrator.router, prefix="/orchestrator", tags=["orchestrator"])
api_v1_router.include_router(graph.router, prefix="/graph", tags=["knowledge-graph"])
