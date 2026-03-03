"""Trend Scout agent — LangGraph StateGraph implementation.

Monitors Google Trends, Reddit, YouTube trending, and news sources,
then scores each trend for niche relevance, clusters similar trends,
and generates actionable recommendations for the creator.

Graph structure::

    START
      ├─ fetch_google_trends ──┐
      ├─ fetch_reddit_trends ──┤
      ├─ fetch_youtube_trending┤
      └─ fetch_news ───────────┘
                               ▼
                        score_relevance
                               ▼
                        cluster_trends
                               ▼
                    generate_recommendations
                               ▼
                              END
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.agents.state import TrendScoutState
from app.agents.tools.trend_tools import (
    get_google_trends,
    get_reddit_hot,
    search_news_articles,
)
from app.agents.tools.vector_tools import query_similar, upsert_embedding
from app.agents.tools.youtube_tools import get_trending_videos
from app.core.embeddings import generate_embedding, generate_embeddings_batch
from app.core.llm import get_llm, invoke_with_retry
from app.core.output_parsers import TrendRecommendationParser
from app.core.prompts import (
    CLUSTER_TRENDS_PROMPT,
    GENERATE_RECOMMENDATIONS_PROMPT,
    SCORE_RELEVANCE_PROMPT,
)
from app.creator_dna.style_transfer import build_dna_prompt
from app.schemas.trend import TrendCluster, TrendRecommendation

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Default subreddits per broad niche — used when the caller does not supply
# subreddits explicitly.
# ---------------------------------------------------------------------------

_DEFAULT_SUBREDDITS: dict[str, list[str]] = {
    "technology": ["technology", "programming", "MachineLearning"],
    "gaming": ["gaming", "Games", "pcgaming"],
    "finance": ["finance", "investing", "CryptoCurrency"],
    "fitness": ["fitness", "bodyweightfitness", "nutrition"],
    "cooking": ["Cooking", "recipes", "MealPrepSunday"],
    "education": ["learnprogramming", "education", "AskScience"],
    "music": ["Music", "WeAreTheMusicMakers", "hiphopheads"],
    "business": ["Entrepreneur", "smallbusiness", "startups"],
}

_FALLBACK_SUBREDDITS: list[str] = ["popular", "all"]


def _subreddits_for_niche(niche: str) -> list[str]:
    """Return a sensible list of subreddits for the given niche."""
    key = niche.lower().strip()
    for known, subs in _DEFAULT_SUBREDDITS.items():
        if known in key or key in known:
            return subs
    return _FALLBACK_SUBREDDITS


# =========================================================================
# Node implementations
# =========================================================================


async def fetch_google_trends(state: TrendScoutState) -> dict[str, Any]:
    """Fetch trending data from Google Trends for the creator's topics.

    Populates ``raw_google_trends`` in the state.
    """
    niche: str = state.get("niche", "")
    topics: list[str] = state.get("topics", [])
    keywords = topics[:5] if topics else [niche]

    logger.info(
        "trend_scout.fetch_google_trends",
        keywords=keywords,
        user_id=state.get("user_id"),
    )

    try:
        result = await get_google_trends.ainvoke(
            {"keywords": keywords, "timeframe": "today 3-m"},
        )

        # Normalise into a flat list of trend dicts
        trends: list[dict[str, Any]] = []

        for ts in result.get("trending_searches", []):
            trends.append({
                "title": ts if isinstance(ts, str) else str(ts),
                "summary": f"Trending search: {ts}",
                "source": "google_trends",
                "raw_data": {"type": "trending_search"},
            })

        for kw, queries in result.get("rising_queries", {}).items():
            for q in queries[:10]:
                query_text = q.get("query", "") if isinstance(q, dict) else str(q)
                value = q.get("value", 0) if isinstance(q, dict) else 0
                trends.append({
                    "title": query_text,
                    "summary": f"Rising query for '{kw}' with growth {value}%",
                    "source": "google_trends",
                    "raw_data": {
                        "type": "rising_query",
                        "keyword": kw,
                        "value": value,
                    },
                })

        logger.info(
            "trend_scout.fetch_google_trends.complete",
            trend_count=len(trends),
        )
        return {"raw_google_trends": trends}

    except Exception as exc:
        logger.error("trend_scout.fetch_google_trends.error", error=str(exc))
        return {"raw_google_trends": [], "error": f"Google Trends error: {exc}"}


async def fetch_reddit_trends(state: TrendScoutState) -> dict[str, Any]:
    """Fetch hot and rising posts from relevant subreddits.

    Populates ``raw_reddit_posts`` in the state.
    """
    niche: str = state.get("niche", "")
    subreddits: list[str] = state.get("subreddits", []) or _subreddits_for_niche(niche)

    logger.info(
        "trend_scout.fetch_reddit_trends",
        subreddits=subreddits,
        user_id=state.get("user_id"),
    )

    try:
        # Fetch from all subreddits concurrently
        tasks = [
            get_reddit_hot.ainvoke({"subreddit": sub, "limit": 15})
            for sub in subreddits[:5]
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        trends: list[dict[str, Any]] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning(
                    "trend_scout.fetch_reddit_trends.sub_error",
                    error=str(result),
                )
                continue

            for post in result.get("hot_posts", []):
                trends.append({
                    "title": post.get("title", ""),
                    "summary": post.get("selftext", "")[:300]
                    or post.get("title", ""),
                    "source": "reddit",
                    "raw_data": {
                        "subreddit": post.get("subreddit", ""),
                        "score": post.get("score", 0),
                        "num_comments": post.get("num_comments", 0),
                        "upvote_ratio": post.get("upvote_ratio", 0),
                        "url": post.get("permalink", ""),
                    },
                })

            for post in result.get("rising_posts", []):
                trends.append({
                    "title": post.get("title", ""),
                    "summary": post.get("selftext", "")[:300]
                    or post.get("title", ""),
                    "source": "reddit",
                    "raw_data": {
                        "subreddit": post.get("subreddit", ""),
                        "score": post.get("score", 0),
                        "num_comments": post.get("num_comments", 0),
                        "upvote_ratio": post.get("upvote_ratio", 0),
                        "url": post.get("permalink", ""),
                        "is_rising": True,
                    },
                })

        logger.info(
            "trend_scout.fetch_reddit_trends.complete",
            trend_count=len(trends),
        )
        return {"raw_reddit_posts": trends}

    except Exception as exc:
        logger.error("trend_scout.fetch_reddit_trends.error", error=str(exc))
        return {"raw_reddit_posts": [], "error": f"Reddit error: {exc}"}


async def fetch_youtube_trending(state: TrendScoutState) -> dict[str, Any]:
    """Fetch currently trending YouTube videos.

    Populates ``raw_youtube_trending`` in the state.
    """
    logger.info(
        "trend_scout.fetch_youtube_trending",
        user_id=state.get("user_id"),
    )

    try:
        result = await get_trending_videos.ainvoke(
            {"region_code": "US", "max_results": 25},
        )

        trends: list[dict[str, Any]] = []
        for video in result.get("trending", []):
            trends.append({
                "title": video.get("title", ""),
                "summary": (
                    f"Trending video by {video.get('channel_title', 'unknown')} "
                    f"with {video.get('view_count', 0):,} views"
                ),
                "source": "youtube_trending",
                "raw_data": {
                    "video_id": video.get("video_id", ""),
                    "channel_title": video.get("channel_title", ""),
                    "view_count": video.get("view_count", 0),
                    "like_count": video.get("like_count", 0),
                    "comment_count": video.get("comment_count", 0),
                    "tags": video.get("tags", []),
                    "published_at": video.get("published_at", ""),
                },
            })

        logger.info(
            "trend_scout.fetch_youtube_trending.complete",
            trend_count=len(trends),
        )
        return {"raw_youtube_trending": trends}

    except Exception as exc:
        logger.error("trend_scout.fetch_youtube_trending.error", error=str(exc))
        return {"raw_youtube_trending": [], "error": f"YouTube error: {exc}"}


async def fetch_news(state: TrendScoutState) -> dict[str, Any]:
    """Fetch recent news articles related to the creator's niche.

    Populates ``raw_news_articles`` in the state.
    """
    niche: str = state.get("niche", "")
    topics: list[str] = state.get("topics", [])

    # Build a combined query from niche and top topics
    query_parts = [niche] + topics[:3]
    query = " OR ".join(f'"{q}"' for q in query_parts if q)

    logger.info(
        "trend_scout.fetch_news",
        query=query,
        user_id=state.get("user_id"),
    )

    try:
        result = await search_news_articles.ainvoke({"query": query, "days": 7})

        trends: list[dict[str, Any]] = []
        for article in result.get("articles", []):
            trends.append({
                "title": article.get("title", ""),
                "summary": article.get("description", "") or article.get("title", ""),
                "source": "news",
                "raw_data": {
                    "source_name": article.get("source", ""),
                    "url": article.get("url", ""),
                    "author": article.get("author"),
                    "published_at": article.get("published_at", ""),
                },
            })

        logger.info(
            "trend_scout.fetch_news.complete",
            trend_count=len(trends),
        )
        return {"raw_news_articles": trends}

    except Exception as exc:
        logger.error("trend_scout.fetch_news.error", error=str(exc))
        return {"raw_news_articles": [], "error": f"News error: {exc}"}


async def score_relevance(state: TrendScoutState) -> dict[str, Any]:
    """Score every collected trend for niche relevance using the LLM.

    Reads raw trends from all four sources, asks the LLM to evaluate each
    one, and populates ``scored_trends``.
    """
    niche: str = state.get("niche", "")
    topics: list[str] = state.get("topics", [])
    creator_dna: dict[str, Any] = state.get("creator_dna", {})

    # Merge all raw trends from the four fetch nodes
    all_trends: list[dict[str, Any]] = [
        *state.get("raw_google_trends", []),
        *state.get("raw_reddit_posts", []),
        *state.get("raw_youtube_trending", []),
        *state.get("raw_news_articles", []),
    ]

    if not all_trends:
        logger.warning("trend_scout.score_relevance.no_trends")
        return {"scored_trends": [], "status": "no_trends_found"}

    logger.info(
        "trend_scout.score_relevance",
        total_trends=len(all_trends),
        user_id=state.get("user_id"),
    )

    dna_conditioning = build_dna_prompt(creator_dna)
    topics_str = ", ".join(topics) if topics else niche
    llm = get_llm(temperature=0.3, max_tokens=1024)

    # Score in batches to manage concurrency and avoid rate limits
    batch_size = 10
    scored: list[dict[str, Any]] = []

    for batch_start in range(0, len(all_trends), batch_size):
        batch = all_trends[batch_start : batch_start + batch_size]
        tasks = []

        for trend in batch:
            prompt = SCORE_RELEVANCE_PROMPT.format(
                dna_conditioning=dna_conditioning,
                creator_niche=niche,
                creator_topics=topics_str,
                trend_title=trend.get("title", ""),
                trend_summary=trend.get("summary", ""),
                trend_source=trend.get("source", ""),
                trend_raw_data=json.dumps(trend.get("raw_data", {}), default=str),
            )

            messages = [
                SystemMessage(content="You are a trend analysis expert. Respond only in valid JSON."),
                HumanMessage(content=prompt),
            ]
            tasks.append(invoke_with_retry(llm, messages))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for trend, result in zip(batch, results, strict=False):
            if isinstance(result, Exception):
                logger.warning(
                    "trend_scout.score_relevance.llm_error",
                    trend_title=trend.get("title", ""),
                    error=str(result),
                )
                continue

            try:
                content = result.content if hasattr(result, "content") else str(result)
                # Strip markdown code fences if present
                cleaned = content.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[-1]
                if cleaned.endswith("```"):
                    cleaned = cleaned.rsplit("```", 1)[0]
                cleaned = cleaned.strip()

                score_data = json.loads(cleaned)

                scored_trend: dict[str, Any] = {
                    **trend,
                    "relevance_score": float(score_data.get("relevance_score", 0)),
                    "velocity": score_data.get("velocity", "stable"),
                    "competition_level": score_data.get("competition_level", "medium"),
                    "niche_angle": score_data.get("niche_angle", ""),
                    "time_sensitivity": score_data.get("time_sensitivity", "this_month"),
                    "reasoning": score_data.get("reasoning", ""),
                }
                scored.append(scored_trend)

            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                logger.warning(
                    "trend_scout.score_relevance.parse_error",
                    trend_title=trend.get("title", ""),
                    error=str(exc),
                )
                # Still include the trend with a low default score
                scored.append({
                    **trend,
                    "relevance_score": 3.0,
                    "velocity": "stable",
                    "competition_level": "medium",
                    "niche_angle": "",
                    "time_sensitivity": "this_month",
                    "reasoning": "Unable to parse LLM score — default applied.",
                })

    # Sort by relevance_score descending and keep the top items
    scored.sort(key=lambda t: t.get("relevance_score", 0), reverse=True)
    top_scored = scored[:50]  # keep top 50 for clustering

    logger.info(
        "trend_scout.score_relevance.complete",
        scored_count=len(top_scored),
        top_score=top_scored[0].get("relevance_score") if top_scored else 0,
    )
    return {"scored_trends": top_scored, "status": "scored"}


async def cluster_trends(state: TrendScoutState) -> dict[str, Any]:
    """Cluster scored trends by semantic similarity using embeddings.

    Uses the embedding model to vectorise trend descriptions, then groups
    near-neighbours together.  Falls back to the LLM-based clustering prompt
    when the number of trends is small enough to fit in a single context.
    """
    scored_trends: list[dict[str, Any]] = state.get("scored_trends", [])
    niche: str = state.get("niche", "")
    topics: list[str] = state.get("topics", [])
    creator_dna: dict[str, Any] = state.get("creator_dna", {})

    if not scored_trends:
        logger.warning("trend_scout.cluster_trends.no_scored_trends")
        return {"trend_clusters": []}

    logger.info(
        "trend_scout.cluster_trends",
        trend_count=len(scored_trends),
        user_id=state.get("user_id"),
    )

    # ------------------------------------------------------------------
    # Step 1: Generate embeddings for each trend
    # ------------------------------------------------------------------
    texts = [
        f"{t.get('title', '')}. {t.get('summary', '')}" for t in scored_trends
    ]

    try:
        embeddings = await generate_embeddings_batch(texts)
    except Exception as exc:
        logger.error("trend_scout.cluster_trends.embedding_error", error=str(exc))
        # Fall back to pure-LLM clustering
        embeddings = []

    # ------------------------------------------------------------------
    # Step 2: Cluster via embeddings (greedy nearest-neighbour)
    # ------------------------------------------------------------------
    clusters: list[dict[str, Any]] = []

    if embeddings and len(embeddings) == len(scored_trends):
        try:
            clusters = _cluster_by_embedding(scored_trends, embeddings)
        except Exception as exc:
            logger.warning(
                "trend_scout.cluster_trends.embedding_cluster_error",
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Step 3: If embedding clustering produced nothing, fall back to LLM
    # ------------------------------------------------------------------
    if not clusters:
        clusters = await _cluster_by_llm(scored_trends, niche, topics, creator_dna)

    # ------------------------------------------------------------------
    # Step 4: Store trend embeddings in ChromaDB for future similarity
    # ------------------------------------------------------------------
    if embeddings and len(embeddings) == len(scored_trends):
        try:
            store_tasks = []
            for idx, (trend, emb) in enumerate(zip(scored_trends, embeddings, strict=False)):
                doc_id = f"trend-{uuid.uuid4().hex[:12]}"
                store_tasks.append(
                    upsert_embedding(
                        collection_name="trend_embeddings",
                        doc_id=doc_id,
                        embedding=emb,
                        document=texts[idx],
                        metadata={
                            "source": trend.get("source", ""),
                            "relevance_score": trend.get("relevance_score", 0),
                            "niche": niche,
                        },
                    )
                )
            await asyncio.gather(*store_tasks, return_exceptions=True)
            logger.debug("trend_scout.cluster_trends.embeddings_stored", count=len(store_tasks))
        except Exception as exc:
            logger.warning("trend_scout.cluster_trends.store_error", error=str(exc))

    logger.info(
        "trend_scout.cluster_trends.complete",
        cluster_count=len(clusters),
    )
    return {"trend_clusters": clusters, "status": "clustered"}


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _cluster_by_embedding(
    trends: list[dict[str, Any]],
    embeddings: list[list[float]],
    threshold: float = 0.78,
) -> list[dict[str, Any]]:
    """Greedy single-linkage clustering by cosine similarity.

    Returns a list of cluster dicts compatible with the ``trend_clusters``
    state field.
    """
    n = len(trends)
    assigned: list[int] = [-1] * n  # cluster ID per trend
    cluster_id = 0

    for i in range(n):
        if assigned[i] >= 0:
            continue
        # Start a new cluster with trend i
        assigned[i] = cluster_id
        for j in range(i + 1, n):
            if assigned[j] >= 0:
                continue
            sim = _cosine_similarity(embeddings[i], embeddings[j])
            if sim >= threshold:
                assigned[j] = cluster_id
        cluster_id += 1

    # Build cluster dicts
    cluster_map: dict[int, list[dict[str, Any]]] = {}
    for idx, cid in enumerate(assigned):
        cluster_map.setdefault(cid, []).append(trends[idx])

    clusters: list[dict[str, Any]] = []
    for cid, members in sorted(cluster_map.items()):
        scores = [m.get("relevance_score", 0) for m in members]
        avg_score = sum(scores) / len(scores) if scores else 0

        # Boost clusters that have signals from multiple sources
        sources = {m.get("source") for m in members}
        source_boost = min(len(sources) * 0.3, 1.0)
        combined = min(avg_score + source_boost, 10.0)

        # Use the highest-scoring trend's title as the cluster name
        top_trend = max(members, key=lambda m: m.get("relevance_score", 0))
        cluster_name = top_trend.get("title", f"Cluster {cid + 1}")

        clusters.append({
            "cluster_name": cluster_name,
            "trends": members,
            "combined_score": round(combined, 2),
            "cluster_reasoning": (
                f"Grouped {len(members)} trend(s) from {', '.join(sources)} "
                f"with average relevance {avg_score:.1f}/10."
            ),
        })

    # Sort clusters by combined_score descending
    clusters.sort(key=lambda c: c.get("combined_score", 0), reverse=True)
    return clusters


async def _cluster_by_llm(
    trends: list[dict[str, Any]],
    niche: str,
    topics: list[str],
    creator_dna: dict[str, Any],
) -> list[dict[str, Any]]:
    """Fall back to LLM-based clustering when embeddings are unavailable."""
    dna_conditioning = build_dna_prompt(creator_dna)
    topics_str = ", ".join(topics) if topics else niche

    # Prepare a trimmed version of trends to avoid exceeding token limits
    trimmed = [
        {
            "title": t.get("title", ""),
            "summary": t.get("summary", "")[:200],
            "source": t.get("source", ""),
            "relevance_score": t.get("relevance_score", 0),
        }
        for t in trends[:30]
    ]

    prompt = CLUSTER_TRENDS_PROMPT.format(
        dna_conditioning=dna_conditioning,
        creator_niche=niche,
        creator_topics=topics_str,
        scored_trends=json.dumps(trimmed, indent=2, default=str),
    )

    llm = get_llm(temperature=0.4, max_tokens=4096)
    messages = [
        SystemMessage(
            content="You are a trend clustering expert. Respond only in valid JSON (an array)."
        ),
        HumanMessage(content=prompt),
    ]

    try:
        result = await invoke_with_retry(llm, messages)
        content = result.content if hasattr(result, "content") else str(result)

        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        clusters = json.loads(cleaned)
        if not isinstance(clusters, list):
            clusters = [clusters]
        return clusters

    except Exception as exc:
        logger.error("trend_scout.cluster_by_llm.error", error=str(exc))
        # Last resort: single cluster with all trends
        return [{
            "cluster_name": "All Trends",
            "trends": trends,
            "combined_score": (
                sum(t.get("relevance_score", 0) for t in trends) / max(len(trends), 1)
            ),
            "cluster_reasoning": "Fallback single cluster due to clustering failure.",
        }]


async def generate_recommendations(state: TrendScoutState) -> dict[str, Any]:
    """Generate final trend recommendations from the clustered trends.

    Uses the LLM to produce structured recommendations that include niche
    angles, suggested content types, and timing advice.
    """
    niche: str = state.get("niche", "")
    topics: list[str] = state.get("topics", [])
    creator_dna: dict[str, Any] = state.get("creator_dna", {})
    trend_clusters: list[dict[str, Any]] = state.get("trend_clusters", [])

    if not trend_clusters:
        logger.warning("trend_scout.generate_recommendations.no_clusters")
        return {"recommendations": [], "status": "no_clusters"}

    logger.info(
        "trend_scout.generate_recommendations",
        cluster_count=len(trend_clusters),
        user_id=state.get("user_id"),
    )

    dna_conditioning = build_dna_prompt(creator_dna)
    topics_str = ", ".join(topics) if topics else niche

    # Trim cluster data to fit within context window
    trimmed_clusters = []
    for cluster in trend_clusters:
        trimmed_trends = [
            {
                "title": t.get("title", ""),
                "summary": t.get("summary", "")[:200],
                "source": t.get("source", ""),
                "relevance_score": t.get("relevance_score", 0),
                "velocity": t.get("velocity", ""),
                "niche_angle": t.get("niche_angle", ""),
            }
            for t in cluster.get("trends", [])[:10]
        ]
        trimmed_clusters.append({
            "cluster_name": cluster.get("cluster_name", ""),
            "combined_score": cluster.get("combined_score", 0),
            "trends": trimmed_trends,
        })

    recommendation_count = min(10, max(3, len(trend_clusters) * 2))

    prompt = GENERATE_RECOMMENDATIONS_PROMPT.format(
        dna_conditioning=dna_conditioning,
        creator_niche=niche,
        creator_topics=topics_str,
        trend_clusters=json.dumps(trimmed_clusters, indent=2, default=str),
        recommendation_count=recommendation_count,
    )

    llm = get_llm(temperature=0.5, max_tokens=4096)
    messages = [
        SystemMessage(
            content=(
                "You are a trend recommendation specialist. "
                "Respond only in valid JSON (an array of recommendation objects)."
            )
        ),
        HumanMessage(content=prompt),
    ]

    try:
        result = await invoke_with_retry(llm, messages)
        content = result.content if hasattr(result, "content") else str(result)

        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        raw_recommendations = json.loads(cleaned)
        if not isinstance(raw_recommendations, list):
            raw_recommendations = [raw_recommendations]

        # Validate each recommendation through the Pydantic schema
        parser = TrendRecommendationParser()
        validated: list[dict[str, Any]] = []

        for rec in raw_recommendations:
            try:
                validated_rec = TrendRecommendation.model_validate(rec)
                validated.append(validated_rec.model_dump())
            except Exception as parse_exc:
                logger.warning(
                    "trend_scout.generate_recommendations.validation_error",
                    error=str(parse_exc),
                    rec_title=rec.get("trend_title", "unknown"),
                )
                # Keep the raw dict if it has the minimum required fields
                if rec.get("trend_title") and rec.get("trend_summary"):
                    validated.append(rec)

        # Sort by relevance_score descending
        validated.sort(
            key=lambda r: r.get("relevance_score", 0),
            reverse=True,
        )

        logger.info(
            "trend_scout.generate_recommendations.complete",
            recommendation_count=len(validated),
        )
        return {
            "recommendations": validated,
            "status": "completed",
        }

    except Exception as exc:
        logger.error(
            "trend_scout.generate_recommendations.error",
            error=str(exc),
        )
        return {
            "recommendations": [],
            "status": "error",
            "error": f"Recommendation generation failed: {exc}",
        }


# =========================================================================
# Graph construction
# =========================================================================


def create_trend_scout_graph() -> StateGraph:
    """Build and compile the Trend Scout LangGraph StateGraph.

    Returns
    -------
    StateGraph
        A compiled graph ready for invocation via ``.ainvoke()``.
    """
    graph = StateGraph(TrendScoutState)

    # Add nodes
    graph.add_node("fetch_google_trends", fetch_google_trends)
    graph.add_node("fetch_reddit_trends", fetch_reddit_trends)
    graph.add_node("fetch_youtube_trending", fetch_youtube_trending)
    graph.add_node("fetch_news", fetch_news)
    graph.add_node("score_relevance", score_relevance)
    graph.add_node("cluster_trends", cluster_trends)
    graph.add_node("generate_recommendations", generate_recommendations)

    # Edges: START fans out to all four fetch nodes in parallel
    graph.add_edge(START, "fetch_google_trends")
    graph.add_edge(START, "fetch_reddit_trends")
    graph.add_edge(START, "fetch_youtube_trending")
    graph.add_edge(START, "fetch_news")

    # All fetches converge into scoring
    graph.add_edge("fetch_google_trends", "score_relevance")
    graph.add_edge("fetch_reddit_trends", "score_relevance")
    graph.add_edge("fetch_youtube_trending", "score_relevance")
    graph.add_edge("fetch_news", "score_relevance")

    # Sequential: score -> cluster -> recommend -> END
    graph.add_edge("score_relevance", "cluster_trends")
    graph.add_edge("cluster_trends", "generate_recommendations")
    graph.add_edge("generate_recommendations", END)

    compiled = graph.compile()
    logger.info("trend_scout.graph_compiled")
    return compiled


# =========================================================================
# Public runner
# =========================================================================


async def run_trend_scout(
    creator_id: str,
    niche: str,
    topics: list[str],
    *,
    subreddits: list[str] | None = None,
    creator_dna: dict[str, Any] | None = None,
) -> list[TrendRecommendation]:
    """Run the Trend Scout agent end-to-end.

    Parameters
    ----------
    creator_id:
        Unique user / creator identifier.
    niche:
        The creator's content niche (e.g. ``"machine learning"``).
    topics:
        List of core topics the creator covers.
    subreddits:
        Optional explicit list of subreddits to monitor.
    creator_dna:
        Optional Creator DNA dict for voice-aware scoring.

    Returns
    -------
    list[TrendRecommendation]
        A ranked list of trend recommendations.
    """
    logger.info(
        "trend_scout.run",
        creator_id=creator_id,
        niche=niche,
        topic_count=len(topics),
    )

    graph = create_trend_scout_graph()

    initial_state: TrendScoutState = {
        "user_id": creator_id,
        "niche": niche,
        "topics": topics,
        "subreddits": subreddits or [],
        "creator_dna": creator_dna or {},
        "raw_google_trends": [],
        "raw_reddit_posts": [],
        "raw_youtube_trending": [],
        "raw_news_articles": [],
        "scored_trends": [],
        "trend_clusters": [],
        "recommendations": [],
        "status": "starting",
        "error": None,
    }

    final_state = await graph.ainvoke(initial_state)

    raw_recommendations = final_state.get("recommendations", [])

    # Convert dicts to TrendRecommendation models
    recommendations: list[TrendRecommendation] = []
    for rec in raw_recommendations:
        try:
            if isinstance(rec, TrendRecommendation):
                recommendations.append(rec)
            else:
                recommendations.append(TrendRecommendation.model_validate(rec))
        except Exception as exc:
            logger.warning(
                "trend_scout.run.parse_recommendation_error",
                error=str(exc),
            )

    logger.info(
        "trend_scout.run.complete",
        creator_id=creator_id,
        recommendation_count=len(recommendations),
        status=final_state.get("status", "unknown"),
    )
    return recommendations
