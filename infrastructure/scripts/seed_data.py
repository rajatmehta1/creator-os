"""Development seed data for Creator OS."""

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models import Base
from app.models.user import User
from app.models.trend import Trend, TrendSource, TrendVelocity
from app.models.idea import Idea, IdeaStatus, IdeaDifficulty


async def seed() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # Create demo user
        user = User(
            id=uuid.uuid4(),
            email="demo@creatorOS.ai",
            name="Demo Creator",
            niche="technology",
            topics=["AI", "programming", "startups", "productivity"],
        )
        session.add(user)
        await session.flush()

        # Create sample trends
        trends = [
            Trend(
                title="AI Agents Are Replacing SaaS",
                summary="Growing discussion about AI agents making traditional SaaS tools obsolete",
                source=TrendSource.REDDIT,
                category="AI",
                relevance_score=92.0,
                velocity=TrendVelocity.EMERGING,
                competition_level="medium",
                detected_at=datetime.now(timezone.utc),
                niche_angle="Show how to build your own AI agents to replace expensive SaaS tools",
                suggested_content_types=["youtube_video", "blog_post", "twitter_thread"],
                time_sensitivity="this_week",
                related_topics=["AI automation", "no-code", "LangGraph"],
            ),
            Trend(
                title="Claude 4 Release Impact on Developers",
                summary="Developer community excited about new Claude capabilities",
                source=TrendSource.GOOGLE_TRENDS,
                category="AI",
                relevance_score=88.0,
                velocity=TrendVelocity.PEAKING,
                competition_level="high",
                detected_at=datetime.now(timezone.utc),
                niche_angle="Hands-on comparison of Claude 4 vs previous models for coding tasks",
                suggested_content_types=["youtube_video", "youtube_short"],
                time_sensitivity="post_today",
            ),
            Trend(
                title="Cursor IDE Productivity Tips",
                summary="Rising interest in AI-powered code editors and productivity hacks",
                source=TrendSource.YOUTUBE_TRENDING,
                category="programming",
                relevance_score=75.0,
                velocity=TrendVelocity.EMERGING,
                competition_level="low",
                detected_at=datetime.now(timezone.utc),
                niche_angle="10 hidden features that 10x your coding speed",
                suggested_content_types=["youtube_video", "blog_post"],
                time_sensitivity="this_week",
            ),
        ]
        for trend in trends:
            session.add(trend)
        await session.flush()

        # Create sample ideas
        ideas = [
            Idea(
                user_id=user.id,
                trend_id=trends[0].id,
                title="I Built AI Agents That Replaced $500/mo of SaaS Tools",
                hook="I was paying $500/month for tools that an AI agent now does for free.",
                angle="Personal journey of replacing SaaS with custom AI agents, showing real cost savings",
                content_type="youtube_video",
                secondary_types=["blog_post", "twitter_thread"],
                score=95.0,
                estimated_performance="high",
                difficulty=IdeaDifficulty.STANDARD,
                key_points=[
                    "The SaaS tools I was paying for",
                    "How I built AI agent replacements",
                    "Cost comparison: before vs after",
                    "Limitations and what still needs SaaS",
                    "Step-by-step tutorial for one agent",
                ],
                differentiation="Real cost savings with receipts, not theoretical",
                target_audience_segment="tech-savvy developers and solopreneurs",
                suggested_publish_window="This week while trend is emerging",
                status=IdeaStatus.GENERATED,
            ),
        ]
        for idea in ideas:
            session.add(idea)

        await session.commit()
        print(f"Seeded: 1 user, {len(trends)} trends, {len(ideas)} ideas")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
