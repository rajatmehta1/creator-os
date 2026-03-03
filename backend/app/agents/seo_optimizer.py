"""LangGraph agent implementation for the SEO Optimizer.

The SEO Optimizer takes a script (or content body) and produces a complete
SEO package -- titles, descriptions, tags, thumbnail concepts, blog SEO,
and a predicted search-visibility score.

Graph topology (parallel fan-out / fan-in)::

    extract_keywords
        -> parallel(research_competitors, analyze_search_intent)
        -> parallel(generate_titles, generate_descriptions,
                    generate_tags, thumbnail_concepts, blog_seo)
        -> score_package
        -> END

LangGraph implements fan-out by routing the same node output to multiple
downstream nodes, and fan-in by specifying all upstream nodes as
prerequisites for the join node.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from app.agents.state import SEOOptimizerState
from app.agents.tools import google_search, search_youtube, get_video_details
from app.core.llm import get_llm, invoke_with_retry
from app.core.output_parsers import seo_package_parser
from app.core.prompts.seo_optimizer import (
    BLOG_SEO_PROMPT,
    EXTRACT_KEYWORDS_PROMPT,
    GENERATE_DESCRIPTION_PROMPT,
    GENERATE_TAGS_PROMPT,
    GENERATE_TITLES_PROMPT,
    THUMBNAIL_CONCEPTS_PROMPT,
)
from app.creator_dna.style_transfer import build_dna_prompt
from app.schemas.content import SEOPackage

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SEARCH_INTENT_SYSTEM = """\
You are an SEO search-intent analyst.  Given a list of keywords, classify
each keyword's dominant search intent.  Return a JSON object mapping each
keyword to its intent classification.

Intent types:
- **informational**: The user wants to learn something.
- **transactional**: The user wants to take a specific action (buy, download, sign up).
- **navigational**: The user is looking for a specific page or brand.
- **commercial_investigation**: The user is comparing options before a decision.
"""

_SCORE_SYSTEM = """\
You are an SEO scoring engine.  Given a complete SEO package (titles,
descriptions, tags, blog meta, thumbnails, and keyword research), predict
the search visibility score on a 0-100 scale.

Scoring factors (weighted):
- Keyword placement in titles and descriptions: 25%
- Tag relevance and coverage: 15%
- Title click-through-rate potential: 20%
- Description keyword density and CTA strength: 15%
- Blog meta-title and meta-description quality: 10%
- Thumbnail concept click appeal: 10%
- Overall coherence and brand consistency: 5%

Return a JSON object:
{
    "search_visibility_score": <float 0-100>,
    "factor_scores": {
        "keyword_placement": <float 0-100>,
        "tag_relevance": <float 0-100>,
        "title_ctr_potential": <float 0-100>,
        "description_quality": <float 0-100>,
        "blog_seo_quality": <float 0-100>,
        "thumbnail_appeal": <float 0-100>,
        "overall_coherence": <float 0-100>
    },
    "top_improvements": [
        "<actionable improvement suggestion>"
    ],
    "confidence": "<high | medium | low>"
}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_json(text: str) -> dict[str, Any] | list[dict[str, Any]]:
    """Parse JSON from an LLM response, stripping markdown fences if present."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    return json.loads(cleaned)


def _get_dna_prompt(state: SEOOptimizerState) -> str:
    """Build DNA conditioning or a neutral placeholder."""
    # SEOOptimizerState does not carry creator_dna directly; we embed
    # niche context in the dna_conditioning slot instead.
    return (
        f"[Creator niche context: content_type={state.get('content_type', 'youtube_video')}, "
        f"target_keywords={state.get('target_keywords', [])}]"
    )


def _content_summary(body: str, max_chars: int = 3000) -> str:
    """Return a truncated summary of the content body."""
    if len(body) <= max_chars:
        return body
    return body[:max_chars] + "\n... [truncated]"


# ---------------------------------------------------------------------------
# Node: extract_keywords
# ---------------------------------------------------------------------------


async def extract_keywords(state: SEOOptimizerState) -> dict[str, Any]:
    """Pull primary and secondary keywords from the content body."""
    logger.info("seo_optimizer.extract_keywords.start")

    title: str = state.get("title", "")
    body: str = state.get("body", "")
    content_type: str = state.get("content_type", "youtube_video")
    target_keywords: list[str] = state.get("target_keywords", [])

    dna_conditioning = _get_dna_prompt(state)

    prompt_text = EXTRACT_KEYWORDS_PROMPT.format(
        dna_conditioning=dna_conditioning,
        content_title=title,
        content_type=content_type,
        content_body=_content_summary(body, 5000),
        creator_niche=", ".join(target_keywords[:3]) if target_keywords else "general",
        creator_topics=", ".join(target_keywords) if target_keywords else title,
    )

    llm = get_llm(temperature=0.3, max_tokens=4096)
    messages = [HumanMessage(content=prompt_text)]

    response = await invoke_with_retry(llm, messages)
    try:
        kw_data: dict[str, Any] = _safe_json(response.content)  # type: ignore[assignment]
    except (json.JSONDecodeError, TypeError):
        logger.warning("seo_optimizer.extract_keywords.parse_failed")
        kw_data = {
            "primary_keyword": target_keywords[0] if target_keywords else title.split()[0],
            "secondary_keywords": [],
            "long_tail_keywords": [],
            "related_queries": [],
            "negative_keywords": [],
        }

    logger.info(
        "seo_optimizer.extract_keywords.complete",
        primary=kw_data.get("primary_keyword"),
    )

    return {
        "keyword_research": kw_data,
        "target_keywords": [kw_data.get("primary_keyword", "")]
        + [kw.get("keyword", kw) if isinstance(kw, dict) else kw
           for kw in kw_data.get("secondary_keywords", [])],
        "status": "keywords_extracted",
    }


# ---------------------------------------------------------------------------
# Node: research_competitors
# ---------------------------------------------------------------------------


async def research_competitors(state: SEOOptimizerState) -> dict[str, Any]:
    """Analyze top-ranking videos for target keywords using YouTube tools."""
    logger.info("seo_optimizer.research_competitors.start")

    kw_research: dict[str, Any] = state.get("keyword_research", {})
    primary_kw: str = kw_research.get("primary_keyword", state.get("title", ""))
    content_type: str = state.get("content_type", "youtube_video")

    competitor_data: list[dict[str, Any]] = []

    # Search YouTube for top results on the primary keyword
    try:
        yt_results = await search_youtube.ainvoke(
            {"query": primary_kw, "max_results": 10, "order": "relevance"}
        )
        top_videos: list[dict[str, Any]] = yt_results.get("results", [])[:5]
    except Exception as exc:
        logger.warning("seo_optimizer.research_competitors.yt_search_failed", error=str(exc))
        top_videos = []

    # Fetch detailed stats for each top video
    for video in top_videos:
        video_id: str = video.get("video_id", "")
        if not video_id:
            continue
        try:
            details = await get_video_details.ainvoke({"video_id": video_id})
            competitor_data.append({
                "video_id": video_id,
                "title": details.get("title", ""),
                "description": (details.get("description", ""))[:500],
                "tags": details.get("tags", []),
                "view_count": details.get("view_count", 0),
                "like_count": details.get("like_count", 0),
                "comment_count": details.get("comment_count", 0),
                "channel_title": details.get("channel_title", ""),
                "duration": details.get("duration", ""),
            })
        except Exception as exc:
            logger.warning(
                "seo_optimizer.research_competitors.detail_failed",
                video_id=video_id,
                error=str(exc),
            )

    # Also search Google for blog/web competitors
    web_competitors: list[dict[str, Any]] = []
    if content_type in ("blog", "newsletter"):
        try:
            web_results = await google_search.ainvoke(
                {"query": primary_kw, "num_results": 10}
            )
            web_competitors = web_results.get("items", [])[:5]
        except Exception as exc:
            logger.warning(
                "seo_optimizer.research_competitors.web_search_failed",
                error=str(exc),
            )

    logger.info(
        "seo_optimizer.research_competitors.complete",
        yt_competitors=len(competitor_data),
        web_competitors=len(web_competitors),
    )

    return {
        "competitor_seo": competitor_data,
        "serp_analysis": {
            **state.get("serp_analysis", {}),
            "youtube_competitors": competitor_data,
            "web_competitors": web_competitors,
        },
        "status": "competitors_researched",
    }


# ---------------------------------------------------------------------------
# Node: analyze_search_intent
# ---------------------------------------------------------------------------


async def analyze_search_intent(state: SEOOptimizerState) -> dict[str, Any]:
    """Classify search intent for each keyword."""
    logger.info("seo_optimizer.analyze_search_intent.start")

    kw_research: dict[str, Any] = state.get("keyword_research", {})
    primary_kw: str = kw_research.get("primary_keyword", "")
    secondary_kws: list[Any] = kw_research.get("secondary_keywords", [])
    long_tail_kws: list[Any] = kw_research.get("long_tail_keywords", [])

    # Collect all keywords into a flat list
    all_keywords: list[str] = [primary_kw] if primary_kw else []
    for kw in secondary_kws:
        keyword_text = kw.get("keyword", kw) if isinstance(kw, dict) else str(kw)
        if keyword_text:
            all_keywords.append(keyword_text)
    for kw in long_tail_kws:
        keyword_text = kw.get("keyword", kw) if isinstance(kw, dict) else str(kw)
        if keyword_text:
            all_keywords.append(keyword_text)

    # De-duplicate while preserving order
    seen: set[str] = set()
    unique_keywords: list[str] = []
    for kw in all_keywords:
        lower = kw.lower()
        if lower not in seen:
            seen.add(lower)
            unique_keywords.append(kw)

    if not unique_keywords:
        logger.warning("seo_optimizer.analyze_search_intent.no_keywords")
        return {
            "serp_analysis": {**state.get("serp_analysis", {}), "intent_map": {}},
            "status": "intent_analyzed",
        }

    llm = get_llm(temperature=0.2, max_tokens=2048)
    messages = [
        SystemMessage(content=_SEARCH_INTENT_SYSTEM),
        HumanMessage(
            content=f"Classify the search intent for each keyword:\n\n"
            f"{json.dumps(unique_keywords, indent=2)}"
        ),
    ]

    response = await invoke_with_retry(llm, messages)
    try:
        intent_data: dict[str, Any] = _safe_json(response.content)  # type: ignore[assignment]
    except (json.JSONDecodeError, TypeError):
        logger.warning("seo_optimizer.analyze_search_intent.parse_failed")
        intent_data = {kw: "informational" for kw in unique_keywords}

    logger.info(
        "seo_optimizer.analyze_search_intent.complete",
        keyword_count=len(unique_keywords),
    )

    return {
        "serp_analysis": {
            **state.get("serp_analysis", {}),
            "intent_map": intent_data,
            "keyword_count": len(unique_keywords),
        },
        "status": "intent_analyzed",
    }


# ---------------------------------------------------------------------------
# Node: generate_titles
# ---------------------------------------------------------------------------


async def generate_titles(state: SEOOptimizerState) -> dict[str, Any]:
    """Create 10 SEO-optimized title variants."""
    logger.info("seo_optimizer.generate_titles.start")

    title: str = state.get("title", "")
    content_type: str = state.get("content_type", "youtube_video")
    kw_research: dict[str, Any] = state.get("keyword_research", {})
    primary_kw: str = kw_research.get("primary_keyword", "")
    secondary_kws: list[Any] = kw_research.get("secondary_keywords", [])

    secondary_kw_str: str = ", ".join(
        kw.get("keyword", kw) if isinstance(kw, dict) else str(kw)
        for kw in secondary_kws[:8]
    )

    dna_conditioning = _get_dna_prompt(state)

    prompt_text = GENERATE_TITLES_PROMPT.format(
        dna_conditioning=dna_conditioning,
        working_title=title,
        content_type=content_type,
        primary_keyword=primary_kw,
        secondary_keywords=secondary_kw_str,
        creator_niche=primary_kw or "general",
        creator_topics=secondary_kw_str or title,
    )

    llm = get_llm(temperature=0.8, max_tokens=4096)
    messages = [HumanMessage(content=prompt_text)]

    response = await invoke_with_retry(llm, messages)
    try:
        titles_data = _safe_json(response.content)
        if isinstance(titles_data, dict):
            titles_list: list[dict[str, Any]] = titles_data.get("titles", [titles_data])
        else:
            titles_list = titles_data  # type: ignore[assignment]
    except (json.JSONDecodeError, TypeError):
        logger.warning("seo_optimizer.generate_titles.parse_failed")
        titles_list = [{"title": title, "estimated_ctr_rating": "medium"}]

    logger.info(
        "seo_optimizer.generate_titles.complete",
        title_count=len(titles_list),
    )

    return {
        "title_options": titles_list,
        "status": "titles_generated",
    }


# ---------------------------------------------------------------------------
# Node: generate_descriptions
# ---------------------------------------------------------------------------


async def generate_descriptions(state: SEOOptimizerState) -> dict[str, Any]:
    """Write SEO-optimized descriptions."""
    logger.info("seo_optimizer.generate_descriptions.start")

    title: str = state.get("title", "")
    body: str = state.get("body", "")
    content_type: str = state.get("content_type", "youtube_video")
    kw_research: dict[str, Any] = state.get("keyword_research", {})
    primary_kw: str = kw_research.get("primary_keyword", "")
    secondary_kws: list[Any] = kw_research.get("secondary_keywords", [])

    secondary_kw_str: str = ", ".join(
        kw.get("keyword", kw) if isinstance(kw, dict) else str(kw)
        for kw in secondary_kws[:8]
    )

    dna_conditioning = _get_dna_prompt(state)

    prompt_text = GENERATE_DESCRIPTION_PROMPT.format(
        dna_conditioning=dna_conditioning,
        content_title=title,
        content_type=content_type,
        content_summary=_content_summary(body, 3000),
        primary_keyword=primary_kw,
        secondary_keywords=secondary_kw_str,
        creator_niche=primary_kw or "general",
        creator_topics=secondary_kw_str or title,
    )

    llm = get_llm(temperature=0.6, max_tokens=4096)
    messages = [HumanMessage(content=prompt_text)]

    response = await invoke_with_retry(llm, messages)
    try:
        desc_data: dict[str, Any] = _safe_json(response.content)  # type: ignore[assignment]
    except (json.JSONDecodeError, TypeError):
        logger.warning("seo_optimizer.generate_descriptions.parse_failed")
        desc_data = {"description": response.content, "chapters": [], "hashtags": []}

    description_text: str = desc_data.get("description", "")
    chapters: list[dict[str, Any]] = desc_data.get("chapters", [])
    hashtags: list[str] = desc_data.get("hashtags", [])

    logger.info(
        "seo_optimizer.generate_descriptions.complete",
        word_count=len(description_text.split()),
    )

    return {
        "description": description_text,
        "hashtags": hashtags,
        "chapters": chapters,
        "status": "descriptions_generated",
    }


# ---------------------------------------------------------------------------
# Node: generate_tags
# ---------------------------------------------------------------------------


async def generate_tags(state: SEOOptimizerState) -> dict[str, Any]:
    """Produce an optimized tag set for maximum discoverability."""
    logger.info("seo_optimizer.generate_tags.start")

    title: str = state.get("title", "")
    content_type: str = state.get("content_type", "youtube_video")
    kw_research: dict[str, Any] = state.get("keyword_research", {})
    primary_kw: str = kw_research.get("primary_keyword", "")
    secondary_kws: list[Any] = kw_research.get("secondary_keywords", [])
    related_queries: list[str] = kw_research.get("related_queries", [])

    secondary_kw_str: str = ", ".join(
        kw.get("keyword", kw) if isinstance(kw, dict) else str(kw)
        for kw in secondary_kws[:10]
    )

    dna_conditioning = _get_dna_prompt(state)

    prompt_text = GENERATE_TAGS_PROMPT.format(
        dna_conditioning=dna_conditioning,
        content_title=title,
        content_type=content_type,
        primary_keyword=primary_kw,
        secondary_keywords=secondary_kw_str,
        related_queries=", ".join(related_queries[:10]),
        creator_niche=primary_kw or "general",
        creator_topics=secondary_kw_str or title,
    )

    llm = get_llm(temperature=0.5, max_tokens=2048)
    messages = [HumanMessage(content=prompt_text)]

    response = await invoke_with_retry(llm, messages)
    try:
        tags_data: dict[str, Any] = _safe_json(response.content)  # type: ignore[assignment]
    except (json.JSONDecodeError, TypeError):
        logger.warning("seo_optimizer.generate_tags.parse_failed")
        tags_data = {"tags": [primary_kw] + [title]}

    tags_list: list[str] = tags_data.get("tags", [])

    logger.info(
        "seo_optimizer.generate_tags.complete",
        tag_count=len(tags_list),
    )

    return {
        "tags": tags_list,
        "status": "tags_generated",
    }


# ---------------------------------------------------------------------------
# Node: thumbnail_concepts
# ---------------------------------------------------------------------------


async def thumbnail_concepts(state: SEOOptimizerState) -> dict[str, Any]:
    """Suggest thumbnail compositions optimized for CTR."""
    logger.info("seo_optimizer.thumbnail_concepts.start")

    title: str = state.get("title", "")
    content_type: str = state.get("content_type", "youtube_video")
    kw_research: dict[str, Any] = state.get("keyword_research", {})
    primary_kw: str = kw_research.get("primary_keyword", "")

    dna_conditioning = _get_dna_prompt(state)

    prompt_text = THUMBNAIL_CONCEPTS_PROMPT.format(
        dna_conditioning=dna_conditioning,
        content_title=title,
        content_type=content_type,
        key_emotion="curiosity",
        primary_keyword=primary_kw,
        creator_niche=primary_kw or "general",
        creator_topics=title,
    )

    llm = get_llm(temperature=0.8, max_tokens=4096)
    messages = [HumanMessage(content=prompt_text)]

    response = await invoke_with_retry(llm, messages)
    try:
        thumb_data = _safe_json(response.content)
        if isinstance(thumb_data, dict):
            thumb_list: list[dict[str, Any]] = thumb_data.get(
                "concepts", thumb_data.get("thumbnail_concepts", [thumb_data])
            )
        else:
            thumb_list = thumb_data  # type: ignore[assignment]
    except (json.JSONDecodeError, TypeError):
        logger.warning("seo_optimizer.thumbnail_concepts.parse_failed")
        thumb_list = [{"concept_name": "default", "layout_description": response.content}]

    logger.info(
        "seo_optimizer.thumbnail_concepts.complete",
        concept_count=len(thumb_list),
    )

    return {
        "thumbnail_concepts": thumb_list,
        "status": "thumbnails_generated",
    }


# ---------------------------------------------------------------------------
# Node: blog_seo
# ---------------------------------------------------------------------------


async def blog_seo(state: SEOOptimizerState) -> dict[str, Any]:
    """Generate a blog SEO package (meta title, description, headers, schema)."""
    logger.info("seo_optimizer.blog_seo.start")

    title: str = state.get("title", "")
    body: str = state.get("body", "")
    content_type: str = state.get("content_type", "youtube_video")
    kw_research: dict[str, Any] = state.get("keyword_research", {})
    primary_kw: str = kw_research.get("primary_keyword", "")
    secondary_kws: list[Any] = kw_research.get("secondary_keywords", [])

    secondary_kw_str: str = ", ".join(
        kw.get("keyword", kw) if isinstance(kw, dict) else str(kw)
        for kw in secondary_kws[:8]
    )

    dna_conditioning = _get_dna_prompt(state)

    prompt_text = BLOG_SEO_PROMPT.format(
        dna_conditioning=dna_conditioning,
        content_title=title,
        content_body=_content_summary(body, 4000),
        primary_keyword=primary_kw,
        secondary_keywords=secondary_kw_str,
        creator_niche=primary_kw or "general",
        creator_topics=secondary_kw_str or title,
    )

    llm = get_llm(temperature=0.5, max_tokens=4096)
    messages = [HumanMessage(content=prompt_text)]

    response = await invoke_with_retry(llm, messages)
    try:
        blog_data: dict[str, Any] = _safe_json(response.content)  # type: ignore[assignment]
    except (json.JSONDecodeError, TypeError):
        logger.warning("seo_optimizer.blog_seo.parse_failed")
        blog_data = {
            "meta_title": title[:60],
            "meta_description": title[:160],
            "suggested_headers": [],
        }

    logger.info("seo_optimizer.blog_seo.complete")

    return {
        "seo_package": {
            **state.get("seo_package", {}),
            "meta_title": blog_data.get("meta_title", ""),
            "meta_description": blog_data.get("meta_description", ""),
            "suggested_headers": blog_data.get("suggested_headers", []),
            "target_word_count": blog_data.get("target_word_count", 0),
            "schema_markup": blog_data.get("schema_markup", []),
            "featured_snippet_opportunity": blog_data.get(
                "featured_snippet_opportunity", {}
            ),
            "internal_link_suggestions": blog_data.get(
                "internal_link_suggestions", []
            ),
        },
        "status": "blog_seo_generated",
    }


# ---------------------------------------------------------------------------
# Node: score_package
# ---------------------------------------------------------------------------


async def score_package(state: SEOOptimizerState) -> dict[str, Any]:
    """Predict search visibility score for the assembled SEO package."""
    logger.info("seo_optimizer.score_package.start")

    # Assemble everything generated so far into a summary for scoring
    package_summary: dict[str, Any] = {
        "keyword_research": state.get("keyword_research", {}),
        "title_options": state.get("title_options", []),
        "description": state.get("description", ""),
        "tags": state.get("tags", []),
        "hashtags": state.get("hashtags", []),
        "chapters": state.get("chapters", []),
        "thumbnail_concepts": state.get("thumbnail_concepts", []),
        "seo_package_blog": state.get("seo_package", {}),
        "competitor_seo": state.get("competitor_seo", [])[:3],
        "serp_analysis": state.get("serp_analysis", {}),
    }

    llm = get_llm(temperature=0.2, max_tokens=2048)
    messages = [
        SystemMessage(content=_SCORE_SYSTEM),
        HumanMessage(
            content=f"Score the following SEO package:\n\n"
            f"{json.dumps(package_summary, default=str)[:8000]}"
        ),
    ]

    response = await invoke_with_retry(llm, messages)
    try:
        score_data: dict[str, Any] = _safe_json(response.content)  # type: ignore[assignment]
    except (json.JSONDecodeError, TypeError):
        logger.warning("seo_optimizer.score_package.parse_failed")
        score_data = {"search_visibility_score": 50.0, "confidence": "low"}

    visibility_score: float = float(score_data.get("search_visibility_score", 50.0))

    # Assemble the final seo_package dict with all fields
    kw_research: dict[str, Any] = state.get("keyword_research", {})
    primary_kw: str = kw_research.get("primary_keyword", "")
    secondary_kws: list[Any] = kw_research.get("secondary_keywords", [])
    secondary_kw_strs: list[str] = [
        kw.get("keyword", kw) if isinstance(kw, dict) else str(kw)
        for kw in secondary_kws
    ]

    blog_seo_data: dict[str, Any] = state.get("seo_package", {})

    final_seo_package: dict[str, Any] = {
        # YouTube
        "title_options": state.get("title_options", []),
        "description": state.get("description", ""),
        "tags": state.get("tags", []),
        "hashtags": state.get("hashtags", []),
        "chapters": state.get("chapters", []),
        "thumbnail_concepts": state.get("thumbnail_concepts", []),
        # Blog
        "meta_title": blog_seo_data.get("meta_title", ""),
        "meta_description": blog_seo_data.get("meta_description", ""),
        "suggested_headers": blog_seo_data.get("suggested_headers", []),
        "target_word_count": blog_seo_data.get("target_word_count", 0),
        # Keywords
        "primary_keyword": primary_kw,
        "secondary_keywords": secondary_kw_strs,
        # Scoring
        "search_visibility_score": visibility_score,
        "factor_scores": score_data.get("factor_scores", {}),
        "top_improvements": score_data.get("top_improvements", []),
        "scoring_confidence": score_data.get("confidence", "medium"),
    }

    logger.info(
        "seo_optimizer.score_package.complete",
        visibility_score=visibility_score,
    )

    return {
        "seo_package": final_seo_package,
        "search_visibility_score": visibility_score,
        "status": "scored",
    }


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def create_seo_optimizer_graph() -> StateGraph:
    """Build and compile the SEO Optimizer LangGraph StateGraph.

    Topology::

        extract_keywords
            -> research_competitors   (fan-out A)
            -> analyze_search_intent  (fan-out A)
            -------- fan-in --------
            -> generate_titles         (fan-out B)
            -> generate_descriptions   (fan-out B)
            -> generate_tags           (fan-out B)
            -> thumbnail_concepts      (fan-out B)
            -> blog_seo                (fan-out B)
            -------- fan-in --------
            -> score_package
            -> END

    Returns
    -------
    langgraph.graph.StateGraph
        The compiled graph ready for ``.ainvoke()`` or ``.astream()``.
    """
    graph = StateGraph(SEOOptimizerState)

    # Register all nine nodes
    graph.add_node("extract_keywords", extract_keywords)
    graph.add_node("research_competitors", research_competitors)
    graph.add_node("analyze_search_intent", analyze_search_intent)
    graph.add_node("generate_titles", generate_titles)
    graph.add_node("generate_descriptions", generate_descriptions)
    graph.add_node("generate_tags", generate_tags)
    graph.add_node("thumbnail_concepts", thumbnail_concepts)
    graph.add_node("blog_seo", blog_seo)
    graph.add_node("score_package", score_package)

    # Entry point
    graph.set_entry_point("extract_keywords")

    # Fan-out A: extract_keywords -> research_competitors, analyze_search_intent
    graph.add_edge("extract_keywords", "research_competitors")
    graph.add_edge("extract_keywords", "analyze_search_intent")

    # Fan-in then fan-out B: both competitors nodes feed into all generators
    graph.add_edge("research_competitors", "generate_titles")
    graph.add_edge("research_competitors", "generate_descriptions")
    graph.add_edge("research_competitors", "generate_tags")
    graph.add_edge("research_competitors", "thumbnail_concepts")
    graph.add_edge("research_competitors", "blog_seo")

    graph.add_edge("analyze_search_intent", "generate_titles")
    graph.add_edge("analyze_search_intent", "generate_descriptions")
    graph.add_edge("analyze_search_intent", "generate_tags")
    graph.add_edge("analyze_search_intent", "thumbnail_concepts")
    graph.add_edge("analyze_search_intent", "blog_seo")

    # Fan-in B: all generators feed into score_package
    graph.add_edge("generate_titles", "score_package")
    graph.add_edge("generate_descriptions", "score_package")
    graph.add_edge("generate_tags", "score_package")
    graph.add_edge("thumbnail_concepts", "score_package")
    graph.add_edge("blog_seo", "score_package")

    # Final edge
    graph.add_edge("score_package", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# High-level runner
# ---------------------------------------------------------------------------


async def run_seo_optimizer(
    script: str,
    content_type: str,
    creator_niche: str,
    *,
    title: Optional[str] = None,
    target_keywords: Optional[list[str]] = None,
    user_id: Optional[str] = None,
    content_id: Optional[str] = None,
) -> SEOPackage:
    """Run the full SEO Optimizer pipeline and return an ``SEOPackage``.

    Parameters
    ----------
    script:
        The script body or content text to optimise.
    content_type:
        Target platform -- ``"youtube_video"``, ``"blog"``, ``"podcast"``, etc.
    creator_niche:
        The creator's primary niche (e.g. ``"machine learning"``,
        ``"cooking"``).
    title:
        Optional working title.  If not provided, the first line of the
        script is used.
    target_keywords:
        Optional seed keywords.  When absent the LLM extracts them.
    user_id:
        Optional user identifier for traceability.
    content_id:
        Optional content UUID for traceability.

    Returns
    -------
    SEOPackage
        A populated Pydantic model containing all SEO metadata.
    """
    # Derive a title from the script if not provided
    if not title:
        first_line = script.strip().split("\n")[0]
        title = first_line[:120].strip("# ").strip()

    logger.info(
        "seo_optimizer.run.start",
        title=title,
        content_type=content_type,
        creator_niche=creator_niche,
        user_id=user_id,
    )

    graph = create_seo_optimizer_graph()

    initial_state: SEOOptimizerState = {
        "title": title,
        "body": script,
        "content_type": content_type,
        "target_keywords": target_keywords or [creator_niche],
        "keyword_research": {},
        "competitor_seo": [],
        "serp_analysis": {},
        "seo_package": {},
        "title_options": [],
        "description": "",
        "tags": [],
        "hashtags": [],
        "chapters": [],
        "thumbnail_concepts": [],
        "search_visibility_score": 0.0,
        "status": "starting",
    }

    if user_id:
        initial_state["user_id"] = user_id
    if content_id:
        initial_state["content_id"] = content_id

    try:
        result = await graph.ainvoke(initial_state)
    except Exception as exc:
        logger.exception("seo_optimizer.run.error", error=str(exc))
        return SEOPackage(
            primary_keyword=creator_niche,
            search_visibility_score=0.0,
        )

    # Build the SEOPackage Pydantic model from the final state
    seo_pkg_data: dict[str, Any] = result.get("seo_package", {})

    seo_package = SEOPackage(
        # YouTube fields
        title_options=seo_pkg_data.get("title_options", result.get("title_options", [])),
        description=seo_pkg_data.get("description", result.get("description", "")),
        tags=seo_pkg_data.get("tags", result.get("tags", [])),
        hashtags=seo_pkg_data.get("hashtags", result.get("hashtags", [])),
        chapters=seo_pkg_data.get("chapters", result.get("chapters", [])),
        thumbnail_concepts=seo_pkg_data.get(
            "thumbnail_concepts", result.get("thumbnail_concepts", [])
        ),
        # Blog fields
        meta_title=seo_pkg_data.get("meta_title", ""),
        meta_description=seo_pkg_data.get("meta_description", ""),
        suggested_headers=seo_pkg_data.get("suggested_headers", []),
        target_word_count=seo_pkg_data.get("target_word_count", 0),
        # Keywords
        primary_keyword=seo_pkg_data.get("primary_keyword", creator_niche),
        secondary_keywords=seo_pkg_data.get("secondary_keywords", []),
        # Score
        search_visibility_score=float(
            seo_pkg_data.get(
                "search_visibility_score",
                result.get("search_visibility_score", 0.0),
            )
        ),
    )

    logger.info(
        "seo_optimizer.run.complete",
        visibility_score=seo_package.search_visibility_score,
        title_count=len(seo_package.title_options),
        tag_count=len(seo_package.tags),
    )

    return seo_package
