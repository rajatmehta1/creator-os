"""Idea Generator agent — LangGraph StateGraph implementation.

Takes scored trend recommendations and the creator's DNA to produce
ranked, diversified content ideas with hooks, angles, and differentiation
notes.  Includes a human-in-the-loop approval gate so the creator can
review top ideas before they enter the production pipeline.

Graph structure::

    START
      │
      ├─ analyze_content_gaps ─────────────────┐
      ├─ brainstorm_trend_ideas ───────────────┤
      └─ brainstorm_evergreen_ideas ───────────┘
                                               ▼
                                       cross_pollinate
                                               ▼
                                          score_ideas
                                               ▼
                                       diversify_output
                                               ▼
                                          human_gate
                                               ▼
                                              END
"""

from __future__ import annotations

import asyncio
import json
import random
from itertools import combinations
from typing import Any

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.agents.state import IdeaGeneratorState
from app.agents.tools.neo4j_tools import query_content_gaps
from app.core.embeddings import generate_embedding
from app.core.llm import get_llm, invoke_with_retry
from app.core.output_parsers import ContentIdeaParser
from app.core.prompts import (
    BRAINSTORM_EVERGREEN_PROMPT,
    BRAINSTORM_TREND_IDEAS_PROMPT,
    CROSS_POLLINATE_PROMPT,
    SCORE_IDEAS_PROMPT,
)
from app.creator_dna.style_transfer import build_dna_prompt
from app.schemas.idea import ContentIdea

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Content type buckets used by the diversify node to ensure variety
_CONTENT_TYPES: list[str] = [
    "youtube_long_form",
    "youtube_short",
    "blog_post",
    "twitter_thread",
    "newsletter",
    "podcast_segment",
]

_DIFFICULTY_LEVELS: list[str] = ["easy", "medium", "hard", "expert"]


# =========================================================================
# Node implementations
# =========================================================================


async def analyze_content_gaps(state: IdeaGeneratorState) -> dict[str, Any]:
    """Query the knowledge graph for topics the creator has not yet covered.

    Populates ``gap_analysis`` in the state with uncovered topics that have
    audience demand or trending signals.
    """
    niche: str = state.get("niche", "")
    content_history: list[dict[str, Any]] = state.get("content_history", [])

    existing_topics: list[str] = []
    for content in content_history:
        # Each content record may have a "topics" list or a "title"
        topics = content.get("topics", [])
        if topics:
            existing_topics.extend(topics)
        elif content.get("title"):
            existing_topics.append(content["title"])

    # De-duplicate
    existing_topics = list(set(existing_topics))

    logger.info(
        "idea_generator.analyze_content_gaps",
        niche=niche,
        existing_topic_count=len(existing_topics),
        user_id=state.get("user_id"),
    )

    try:
        result = await query_content_gaps.ainvoke({
            "niche": niche,
            "existing_topics": existing_topics,
            "limit": 15,
        })

        gap_topics: list[dict[str, Any]] = result.get("gap_topics", [])

        gap_analysis: dict[str, Any] = {
            "gap_topics": gap_topics,
            "total_gaps": len(gap_topics),
            "existing_topic_count": len(existing_topics),
            "top_gaps": [g.get("topic", "") for g in gap_topics[:5]],
        }

        logger.info(
            "idea_generator.analyze_content_gaps.complete",
            gap_count=len(gap_topics),
        )
        return {"gap_analysis": gap_analysis}

    except Exception as exc:
        logger.error("idea_generator.analyze_content_gaps.error", error=str(exc))
        return {
            "gap_analysis": {
                "gap_topics": [],
                "total_gaps": 0,
                "existing_topic_count": len(existing_topics),
                "top_gaps": [],
                "error": str(exc),
            },
        }


async def brainstorm_trend_ideas(state: IdeaGeneratorState) -> dict[str, Any]:
    """Use the LLM to brainstorm content ideas driven by current trends.

    Reads ``scored_trends`` and the creator DNA, then generates creative
    ideas for each trend.  Results are appended to ``raw_ideas``.
    """
    niche: str = state.get("niche", "")
    creator_dna: dict[str, Any] = state.get("creator_dna", {})
    scored_trends: list[dict[str, Any]] = state.get("scored_trends", [])
    content_history: list[dict[str, Any]] = state.get("content_history", [])

    if not scored_trends:
        logger.info("idea_generator.brainstorm_trend_ideas.no_trends")
        return {"raw_ideas": state.get("raw_ideas", [])}

    logger.info(
        "idea_generator.brainstorm_trend_ideas",
        trend_count=len(scored_trends),
        user_id=state.get("user_id"),
    )

    dna_conditioning = build_dna_prompt(creator_dna)
    topics_str = ", ".join(
        creator_dna.get("primary_topics", [])
        if isinstance(creator_dna.get("primary_topics"), list)
        else [niche]
    )

    # Derive top-performing themes from content history
    top_themes: list[str] = []
    sorted_history = sorted(
        content_history,
        key=lambda c: c.get("view_count", 0),
        reverse=True,
    )
    for item in sorted_history[:10]:
        title = item.get("title", "")
        if title:
            top_themes.append(title)
    top_performing_themes = "; ".join(top_themes[:5]) if top_themes else "Not enough data yet"

    # Prepare trend data for the prompt
    trend_data = [
        {
            "trend_title": t.get("trend_title", t.get("title", "")),
            "trend_summary": t.get("trend_summary", t.get("summary", "")),
            "relevance_score": t.get("relevance_score", 0),
            "niche_angle": t.get("niche_angle", ""),
            "velocity": t.get("velocity", ""),
        }
        for t in scored_trends[:10]
    ]

    ideas_per_trend = max(2, min(4, 20 // len(trend_data)))

    prompt = BRAINSTORM_TREND_IDEAS_PROMPT.format(
        dna_conditioning=dna_conditioning,
        creator_niche=niche,
        creator_topics=topics_str,
        top_performing_themes=top_performing_themes,
        trend_recommendations=json.dumps(trend_data, indent=2, default=str),
        ideas_per_trend=ideas_per_trend,
    )

    llm = get_llm(temperature=0.8, max_tokens=4096)
    messages = [
        SystemMessage(
            content=(
                "You are a creative content strategist. "
                "Respond only in valid JSON (an array of idea objects)."
            )
        ),
        HumanMessage(content=prompt),
    ]

    try:
        result = await invoke_with_retry(llm, messages)
        content = result.content if hasattr(result, "content") else str(result)

        cleaned = _strip_code_fences(content)
        ideas = json.loads(cleaned)
        if not isinstance(ideas, list):
            ideas = [ideas]

        # Tag each idea as trend-based
        for idea in ideas:
            idea["idea_source"] = "trend"

        logger.info(
            "idea_generator.brainstorm_trend_ideas.complete",
            idea_count=len(ideas),
        )

        existing_ideas = state.get("raw_ideas", [])
        return {"raw_ideas": existing_ideas + ideas}

    except Exception as exc:
        logger.error(
            "idea_generator.brainstorm_trend_ideas.error",
            error=str(exc),
        )
        return {"raw_ideas": state.get("raw_ideas", [])}


async def brainstorm_evergreen_ideas(state: IdeaGeneratorState) -> dict[str, Any]:
    """Generate evergreen (non-trend) content ideas using the LLM.

    Focuses on searchable, long-term-value topics that fill gaps in the
    creator's existing content portfolio.
    """
    niche: str = state.get("niche", "")
    creator_dna: dict[str, Any] = state.get("creator_dna", {})
    gap_analysis: dict[str, Any] = state.get("gap_analysis", {})

    logger.info(
        "idea_generator.brainstorm_evergreen_ideas",
        user_id=state.get("user_id"),
    )

    dna_conditioning = build_dna_prompt(creator_dna)
    topics_str = ", ".join(
        creator_dna.get("primary_topics", [])
        if isinstance(creator_dna.get("primary_topics"), list)
        else [niche]
    )

    # Build pain points from gap analysis and DNA
    gap_topics = gap_analysis.get("gap_topics", [])
    audience_pain_points = "; ".join(
        g.get("topic", "") for g in gap_topics[:5]
    ) or "Not yet determined"

    content_gaps = json.dumps(
        gap_analysis.get("top_gaps", []),
        default=str,
    )

    idea_count = 5

    prompt = BRAINSTORM_EVERGREEN_PROMPT.format(
        dna_conditioning=dna_conditioning,
        creator_niche=niche,
        creator_topics=topics_str,
        audience_pain_points=audience_pain_points,
        content_gaps=content_gaps,
        idea_count=idea_count,
    )

    llm = get_llm(temperature=0.8, max_tokens=4096)
    messages = [
        SystemMessage(
            content=(
                "You are a content strategy expert specialising in evergreen content. "
                "Respond only in valid JSON (an array of idea objects)."
            )
        ),
        HumanMessage(content=prompt),
    ]

    try:
        result = await invoke_with_retry(llm, messages)
        content = result.content if hasattr(result, "content") else str(result)

        cleaned = _strip_code_fences(content)
        ideas = json.loads(cleaned)
        if not isinstance(ideas, list):
            ideas = [ideas]

        for idea in ideas:
            idea["idea_source"] = "evergreen"

        logger.info(
            "idea_generator.brainstorm_evergreen_ideas.complete",
            idea_count=len(ideas),
        )

        existing_ideas = state.get("raw_ideas", [])
        return {"raw_ideas": existing_ideas + ideas}

    except Exception as exc:
        logger.error(
            "idea_generator.brainstorm_evergreen_ideas.error",
            error=str(exc),
        )
        return {"raw_ideas": state.get("raw_ideas", [])}


async def cross_pollinate(state: IdeaGeneratorState) -> dict[str, Any]:
    """Combine ideas from different categories to produce novel mashups.

    Picks pairs of topics from the trend-based and evergreen pools, then
    asks the LLM to find surprising connections between them.
    """
    niche: str = state.get("niche", "")
    creator_dna: dict[str, Any] = state.get("creator_dna", {})
    raw_ideas: list[dict[str, Any]] = state.get("raw_ideas", [])

    logger.info(
        "idea_generator.cross_pollinate",
        raw_idea_count=len(raw_ideas),
        user_id=state.get("user_id"),
    )

    if len(raw_ideas) < 2:
        logger.info("idea_generator.cross_pollinate.not_enough_ideas")
        return {"raw_ideas": raw_ideas}

    dna_conditioning = build_dna_prompt(creator_dna)
    topics_str = ", ".join(
        creator_dna.get("primary_topics", [])
        if isinstance(creator_dna.get("primary_topics"), list)
        else [niche]
    )

    # Select cross-pollination pairs: one trend-based + one evergreen, or
    # two unrelated ideas from different sources
    trend_ideas = [i for i in raw_ideas if i.get("idea_source") == "trend"]
    evergreen_ideas = [i for i in raw_ideas if i.get("idea_source") == "evergreen"]

    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []

    # Cross trend+evergreen pairs
    if trend_ideas and evergreen_ideas:
        for t_idea in trend_ideas[:3]:
            for e_idea in evergreen_ideas[:2]:
                pairs.append((t_idea, e_idea))

    # Also try combining unrelated trends
    if len(trend_ideas) >= 2:
        for pair in list(combinations(trend_ideas[:5], 2))[:3]:
            pairs.append(pair)

    # Limit the number of cross-pollination attempts
    pairs = pairs[:5]

    if not pairs:
        logger.info("idea_generator.cross_pollinate.no_pairs")
        return {"raw_ideas": raw_ideas}

    llm = get_llm(temperature=0.9, max_tokens=2048)
    cross_ideas: list[dict[str, Any]] = []

    tasks = []
    for topic_a, topic_b in pairs:
        additional_context = json.dumps({
            "topic_a_details": {
                "title": topic_a.get("idea_title", ""),
                "angle": topic_a.get("angle", ""),
                "source": topic_a.get("idea_source", ""),
            },
            "topic_b_details": {
                "title": topic_b.get("idea_title", ""),
                "angle": topic_b.get("angle", ""),
                "source": topic_b.get("idea_source", ""),
            },
        }, default=str)

        prompt = CROSS_POLLINATE_PROMPT.format(
            dna_conditioning=dna_conditioning,
            creator_niche=niche,
            creator_topics=topics_str,
            topic_a=topic_a.get("idea_title", ""),
            topic_b=topic_b.get("idea_title", ""),
            additional_context=additional_context,
            idea_count=1,
        )

        messages = [
            SystemMessage(
                content=(
                    "You are a creative ideation specialist. "
                    "Respond only in valid JSON (an array of idea objects)."
                )
            ),
            HumanMessage(content=prompt),
        ]
        tasks.append(invoke_with_retry(llm, messages))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            logger.warning(
                "idea_generator.cross_pollinate.llm_error",
                error=str(result),
            )
            continue

        try:
            content = result.content if hasattr(result, "content") else str(result)
            cleaned = _strip_code_fences(content)
            ideas = json.loads(cleaned)
            if not isinstance(ideas, list):
                ideas = [ideas]

            for idea in ideas:
                idea["idea_source"] = "cross_pollination"
            cross_ideas.extend(ideas)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning(
                "idea_generator.cross_pollinate.parse_error",
                error=str(exc),
            )

    logger.info(
        "idea_generator.cross_pollinate.complete",
        cross_idea_count=len(cross_ideas),
    )
    return {"raw_ideas": raw_ideas + cross_ideas}


async def score_ideas(state: IdeaGeneratorState) -> dict[str, Any]:
    """Score and rank all brainstormed ideas on multiple dimensions.

    Evaluates virality, audience value, search potential, brand alignment,
    production feasibility, and revenue potential.  Populates ``ranked_ideas``.
    """
    niche: str = state.get("niche", "")
    creator_dna: dict[str, Any] = state.get("creator_dna", {})
    raw_ideas: list[dict[str, Any]] = state.get("raw_ideas", [])

    if not raw_ideas:
        logger.warning("idea_generator.score_ideas.no_ideas")
        return {"ranked_ideas": []}

    logger.info(
        "idea_generator.score_ideas",
        idea_count=len(raw_ideas),
        user_id=state.get("user_id"),
    )

    dna_conditioning = build_dna_prompt(creator_dna)
    topics_str = ", ".join(
        creator_dna.get("primary_topics", [])
        if isinstance(creator_dna.get("primary_topics"), list)
        else [niche]
    )

    # Derive channel stage from DNA
    videos_analyzed = creator_dna.get("videos_analyzed", 0)
    if videos_analyzed > 200:
        channel_stage = "established (200+ videos)"
    elif videos_analyzed > 50:
        channel_stage = "growing (50-200 videos)"
    elif videos_analyzed > 10:
        channel_stage = "early growth (10-50 videos)"
    else:
        channel_stage = "early stage (<10 videos)"

    production_capacity = creator_dna.get("production_capacity", "2-3 videos per week")

    # Prepare ideas for the prompt — trim to fit context
    trimmed_ideas = [
        {
            "idea_title": idea.get("idea_title", ""),
            "hook": idea.get("hook", "")[:200],
            "angle": idea.get("angle", "")[:200],
            "content_type": idea.get("content_type", ""),
            "difficulty": idea.get("difficulty", "medium"),
            "idea_source": idea.get("idea_source", ""),
            "trend_connection": idea.get("trend_connection"),
            "estimated_performance": idea.get("estimated_performance", "medium"),
        }
        for idea in raw_ideas[:30]
    ]

    # Score in batches to handle large sets
    batch_size = 15
    all_scored: list[dict[str, Any]] = []

    for batch_start in range(0, len(trimmed_ideas), batch_size):
        batch = trimmed_ideas[batch_start : batch_start + batch_size]

        prompt = SCORE_IDEAS_PROMPT.format(
            dna_conditioning=dna_conditioning,
            creator_niche=niche,
            creator_topics=topics_str,
            channel_stage=channel_stage,
            production_capacity=production_capacity,
            ideas=json.dumps(batch, indent=2, default=str),
        )

        llm = get_llm(temperature=0.3, max_tokens=4096)
        messages = [
            SystemMessage(
                content=(
                    "You are a content strategy analyst. "
                    "Respond only in valid JSON (an array of scored idea objects)."
                )
            ),
            HumanMessage(content=prompt),
        ]

        try:
            result = await invoke_with_retry(llm, messages)
            content = result.content if hasattr(result, "content") else str(result)

            cleaned = _strip_code_fences(content)
            scored_batch = json.loads(cleaned)
            if not isinstance(scored_batch, list):
                scored_batch = [scored_batch]

            # Merge scores back into the full idea objects
            score_lookup: dict[str, dict[str, Any]] = {
                s.get("idea_title", ""): s for s in scored_batch
            }

            original_batch = raw_ideas[batch_start : batch_start + batch_size]
            for idea in original_batch:
                title = idea.get("idea_title", "")
                scoring = score_lookup.get(title, {})

                merged: dict[str, Any] = {
                    **idea,
                    "scores": scoring.get("scores", {}),
                    "composite_score": scoring.get("composite_score", 5.0),
                    "priority": scoring.get("priority", "nice_to_have"),
                    "scoring_reasoning": scoring.get("reasoning", ""),
                }
                all_scored.append(merged)

        except Exception as exc:
            logger.error(
                "idea_generator.score_ideas.batch_error",
                batch_start=batch_start,
                error=str(exc),
            )
            # Include unscored ideas with default scores
            original_batch = raw_ideas[batch_start : batch_start + batch_size]
            for idea in original_batch:
                all_scored.append({
                    **idea,
                    "scores": {},
                    "composite_score": 5.0,
                    "priority": "nice_to_have",
                    "scoring_reasoning": "Scoring unavailable — default applied.",
                })

    # Sort by composite score descending
    all_scored.sort(
        key=lambda i: i.get("composite_score", 0),
        reverse=True,
    )

    logger.info(
        "idea_generator.score_ideas.complete",
        scored_count=len(all_scored),
        top_score=all_scored[0].get("composite_score") if all_scored else 0,
    )
    return {"ranked_ideas": all_scored}


async def diversify_output(state: IdeaGeneratorState) -> dict[str, Any]:
    """Ensure the final idea set has a healthy mix of content types and
    difficulty levels.

    Re-ranks ideas to avoid clustering of a single content type or
    difficulty level at the top.  The goal is to give the creator a
    varied menu of actionable ideas.
    """
    ranked_ideas: list[dict[str, Any]] = state.get("ranked_ideas", [])

    if not ranked_ideas:
        logger.warning("idea_generator.diversify_output.no_ideas")
        return {"ranked_ideas": []}

    logger.info(
        "idea_generator.diversify_output",
        idea_count=len(ranked_ideas),
        user_id=state.get("user_id"),
    )

    # ------------------------------------------------------------------
    # Strategy: Interleave ideas to maximise variety while mostly
    # preserving the composite_score ordering.
    # ------------------------------------------------------------------

    # Bucket ideas by content type
    by_type: dict[str, list[dict[str, Any]]] = {}
    for idea in ranked_ideas:
        ctype = _normalise_content_type(idea.get("content_type", "other"))
        by_type.setdefault(ctype, []).append(idea)

    # Round-robin pick from each bucket (highest score first within bucket)
    diversified: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    max_iterations = len(ranked_ideas) * 2  # safety bound
    iteration = 0

    while any(by_type.values()) and iteration < max_iterations:
        iteration += 1
        for ctype in list(by_type.keys()):
            bucket = by_type.get(ctype, [])
            if not bucket:
                by_type.pop(ctype, None)
                continue

            idea = bucket.pop(0)
            title = idea.get("idea_title", "")

            # De-duplicate by title
            if title in seen_titles:
                continue
            seen_titles.add(title)
            diversified.append(idea)

            if not bucket:
                by_type.pop(ctype, None)

    # ------------------------------------------------------------------
    # Ensure difficulty spread: if the top N ideas are all the same
    # difficulty, promote one easier and one harder idea.
    # ------------------------------------------------------------------
    if len(diversified) >= 5:
        top_5_difficulties = [d.get("difficulty", "medium") for d in diversified[:5]]
        if len(set(top_5_difficulties)) == 1:
            # All same difficulty — swap in variety
            for idx in range(5, len(diversified)):
                if diversified[idx].get("difficulty") != top_5_difficulties[0]:
                    # Swap into position 2 (after the top two)
                    diversified.insert(2, diversified.pop(idx))
                    break

    # ------------------------------------------------------------------
    # Ensure source diversity: at least one trend, one evergreen, and one
    # cross-pollinated idea in the top 10 if available.
    # ------------------------------------------------------------------
    _ensure_source_in_top(diversified, "trend", top_n=10)
    _ensure_source_in_top(diversified, "evergreen", top_n=10)
    _ensure_source_in_top(diversified, "cross_pollination", top_n=10)

    logger.info(
        "idea_generator.diversify_output.complete",
        diversified_count=len(diversified),
        content_types=list({_normalise_content_type(i.get("content_type", "")) for i in diversified}),
    )
    return {"ranked_ideas": diversified}


async def human_gate(state: IdeaGeneratorState) -> dict[str, Any]:
    """Present top ideas for human review (configurable approval step).

    In the current implementation this node prepares the ``selected_idea``
    and ``ranked_ideas`` for external review.  When used inside the
    Orchestrator with a human gate enabled, execution pauses here and
    resumes once the creator approves / edits the ideas.

    When no human gate is configured the node passes through with the
    top-ranked idea pre-selected.
    """
    ranked_ideas: list[dict[str, Any]] = state.get("ranked_ideas", [])

    logger.info(
        "idea_generator.human_gate",
        idea_count=len(ranked_ideas),
        user_id=state.get("user_id"),
    )

    if not ranked_ideas:
        return {
            "ranked_ideas": [],
            "selected_idea": None,
            "status": "completed_no_ideas",
        }

    # Auto-select the highest-ranked idea (the orchestrator or UI can
    # override this via gate_approval data).
    selected = ranked_ideas[0]

    # Validate top ideas through the Pydantic schema for clean output
    validated_ideas: list[dict[str, Any]] = []
    for idea in ranked_ideas:
        try:
            # Extract the fields that ContentIdea expects
            idea_fields = {
                "idea_title": idea.get("idea_title", ""),
                "hook": idea.get("hook", ""),
                "angle": idea.get("angle", ""),
                "content_type": idea.get("content_type", ""),
                "secondary_types": idea.get("secondary_types", []),
                "trend_connection": idea.get("trend_connection"),
                "estimated_performance": idea.get("estimated_performance", "medium"),
                "target_audience_segment": idea.get("target_audience_segment", ""),
                "key_points": idea.get("key_points", []),
                "differentiation": idea.get("differentiation", ""),
                "difficulty": idea.get("difficulty", "medium"),
                "suggested_publish_window": idea.get("suggested_publish_window", "anytime"),
            }
            validated = ContentIdea.model_validate(idea_fields)
            # Preserve scoring metadata alongside the validated fields
            full_idea = {
                **validated.model_dump(),
                "scores": idea.get("scores", {}),
                "composite_score": idea.get("composite_score", 0),
                "priority": idea.get("priority", ""),
                "idea_source": idea.get("idea_source", ""),
                "scoring_reasoning": idea.get("scoring_reasoning", ""),
            }
            validated_ideas.append(full_idea)
        except Exception as exc:
            logger.warning(
                "idea_generator.human_gate.validation_error",
                idea_title=idea.get("idea_title", "unknown"),
                error=str(exc),
            )
            # Keep the raw dict if it has minimum fields
            if idea.get("idea_title") and idea.get("hook"):
                validated_ideas.append(idea)

    logger.info(
        "idea_generator.human_gate.complete",
        validated_count=len(validated_ideas),
        selected_title=selected.get("idea_title", ""),
    )
    return {
        "ranked_ideas": validated_ideas,
        "selected_idea": selected,
        "status": "completed",
    }


# =========================================================================
# Helper functions
# =========================================================================


def _strip_code_fences(text: str) -> str:
    """Remove Markdown code fences from LLM output."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("```", 1)[0]
    return cleaned.strip()


def _normalise_content_type(ctype: str) -> str:
    """Map various content type strings to a canonical form."""
    ctype_lower = ctype.lower().strip()
    mapping: dict[str, str] = {
        "youtube_long_form": "youtube_long_form",
        "youtube long-form": "youtube_long_form",
        "youtube video": "youtube_long_form",
        "youtube_video": "youtube_long_form",
        "long-form video": "youtube_long_form",
        "youtube_short": "youtube_short",
        "youtube short": "youtube_short",
        "youtube shorts": "youtube_short",
        "short": "youtube_short",
        "shorts": "youtube_short",
        "blog_post": "blog_post",
        "blog post": "blog_post",
        "blog": "blog_post",
        "article": "blog_post",
        "twitter_thread": "twitter_thread",
        "twitter thread": "twitter_thread",
        "twitter": "twitter_thread",
        "x thread": "twitter_thread",
        "thread": "twitter_thread",
        "newsletter": "newsletter",
        "email": "newsletter",
        "podcast_segment": "podcast_segment",
        "podcast": "podcast_segment",
    }
    return mapping.get(ctype_lower, ctype_lower)


def _ensure_source_in_top(
    ideas: list[dict[str, Any]],
    source: str,
    top_n: int = 10,
) -> None:
    """Promote one idea with the given source into the top_n if absent.

    Modifies the list in place.
    """
    top_sources = {i.get("idea_source") for i in ideas[:top_n]}
    if source in top_sources:
        return

    for idx in range(top_n, len(ideas)):
        if ideas[idx].get("idea_source") == source:
            idea = ideas.pop(idx)
            insert_pos = min(top_n - 1, len(ideas))
            ideas.insert(insert_pos, idea)
            return


# =========================================================================
# Graph construction
# =========================================================================


def create_idea_generator_graph() -> StateGraph:
    """Build and compile the Idea Generator LangGraph StateGraph.

    Returns
    -------
    StateGraph
        A compiled graph ready for invocation via ``.ainvoke()``.
    """
    graph = StateGraph(IdeaGeneratorState)

    # Add nodes
    graph.add_node("analyze_content_gaps", analyze_content_gaps)
    graph.add_node("brainstorm_trend_ideas", brainstorm_trend_ideas)
    graph.add_node("brainstorm_evergreen_ideas", brainstorm_evergreen_ideas)
    graph.add_node("cross_pollinate", cross_pollinate)
    graph.add_node("score_ideas", score_ideas)
    graph.add_node("diversify_output", diversify_output)
    graph.add_node("human_gate", human_gate)

    # Edges: START fans out to three parallel branches
    graph.add_edge(START, "analyze_content_gaps")
    graph.add_edge(START, "brainstorm_trend_ideas")
    graph.add_edge(START, "brainstorm_evergreen_ideas")

    # All three converge into cross_pollinate
    graph.add_edge("analyze_content_gaps", "cross_pollinate")
    graph.add_edge("brainstorm_trend_ideas", "cross_pollinate")
    graph.add_edge("brainstorm_evergreen_ideas", "cross_pollinate")

    # Sequential: cross_pollinate -> score -> diversify -> human_gate -> END
    graph.add_edge("cross_pollinate", "score_ideas")
    graph.add_edge("score_ideas", "diversify_output")
    graph.add_edge("diversify_output", "human_gate")
    graph.add_edge("human_gate", END)

    compiled = graph.compile()
    logger.info("idea_generator.graph_compiled")
    return compiled


# =========================================================================
# Public runner
# =========================================================================


async def run_idea_generator(
    creator_id: str,
    trends: list[dict[str, Any]],
    creator_dna: dict[str, Any],
    *,
    count: int = 10,
    content_history: list[dict[str, Any]] | None = None,
    niche: str | None = None,
) -> list[ContentIdea]:
    """Run the Idea Generator agent end-to-end.

    Parameters
    ----------
    creator_id:
        Unique user / creator identifier.
    trends:
        List of scored trend dicts (typically the output of Trend Scout).
    creator_dna:
        Creator DNA dict for voice-aware idea generation.
    count:
        Target number of ideas to return.
    content_history:
        Optional list of the creator's past content for gap analysis.
    niche:
        Creator's niche.  When ``None``, extracted from ``creator_dna``.

    Returns
    -------
    list[ContentIdea]
        A ranked, diversified list of content ideas.
    """
    # Derive niche from DNA if not provided explicitly
    effective_niche = niche
    if not effective_niche:
        primary_topics = creator_dna.get("primary_topics", [])
        if isinstance(primary_topics, list) and primary_topics:
            effective_niche = primary_topics[0]
        else:
            effective_niche = str(primary_topics) if primary_topics else "general"

    logger.info(
        "idea_generator.run",
        creator_id=creator_id,
        niche=effective_niche,
        trend_count=len(trends),
        target_count=count,
    )

    graph = create_idea_generator_graph()

    initial_state: IdeaGeneratorState = {
        "user_id": creator_id,
        "niche": effective_niche,
        "creator_dna": creator_dna,
        "scored_trends": trends,
        "content_history": content_history or [],
        "knowledge_graph_context": {},
        "raw_ideas": [],
        "gap_analysis": {},
        "competitor_ideas": [],
        "ranked_ideas": [],
        "selected_idea": None,
        "status": "starting",
        "error": None,
    }

    final_state = await graph.ainvoke(initial_state)

    raw_ranked = final_state.get("ranked_ideas", [])

    # Convert to ContentIdea models and trim to requested count
    ideas: list[ContentIdea] = []
    for idea_dict in raw_ranked[:count]:
        try:
            idea_fields = {
                "idea_title": idea_dict.get("idea_title", ""),
                "hook": idea_dict.get("hook", ""),
                "angle": idea_dict.get("angle", ""),
                "content_type": idea_dict.get("content_type", ""),
                "secondary_types": idea_dict.get("secondary_types", []),
                "trend_connection": idea_dict.get("trend_connection"),
                "estimated_performance": idea_dict.get("estimated_performance", "medium"),
                "target_audience_segment": idea_dict.get("target_audience_segment", ""),
                "key_points": idea_dict.get("key_points", []),
                "differentiation": idea_dict.get("differentiation", ""),
                "difficulty": idea_dict.get("difficulty", "medium"),
                "suggested_publish_window": idea_dict.get("suggested_publish_window", "anytime"),
            }
            if isinstance(idea_dict, ContentIdea):
                ideas.append(idea_dict)
            else:
                ideas.append(ContentIdea.model_validate(idea_fields))
        except Exception as exc:
            logger.warning(
                "idea_generator.run.parse_idea_error",
                idea_title=idea_dict.get("idea_title", "unknown"),
                error=str(exc),
            )

    logger.info(
        "idea_generator.run.complete",
        creator_id=creator_id,
        idea_count=len(ideas),
        status=final_state.get("status", "unknown"),
    )
    return ideas
