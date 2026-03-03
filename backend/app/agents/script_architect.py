"""LangGraph agent implementation for the Script Architect.

The Script Architect transforms an approved content idea into a full script
with retention hooks, creator-DNA voice matching, and multi-platform variant
generation.  The graph exposes a human-gate node so the creator can review
the final script before it is published.

Graph topology (linear)::

    research -> outline -> draft_script -> inject_hooks
        -> tone_check -> generate_variants -> human_gate -> END
"""

from __future__ import annotations

import json
from typing import Any, Optional

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from app.agents.state import ScriptArchitectState
from app.agents.tools import google_search, search_knowledge_graph, search_youtube
from app.core.llm import get_llm, invoke_with_retry
from app.core.prompts.script_architect import (
    DRAFT_SCRIPT_PROMPT,
    GENERATE_VARIANTS_PROMPT,
    INJECT_HOOKS_PROMPT,
    OUTLINE_PROMPT,
    RESEARCH_PROMPT,
    TONE_CHECK_PROMPT,
)
from app.creator_dna.style_transfer import build_dna_prompt

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_CONTENT_TYPE = "youtube_video"

_TARGET_VARIANTS = [
    "YouTube Short / TikTok",
    "Blog Post",
    "Twitter/X Thread",
    "LinkedIn Post",
    "Newsletter",
    "Podcast Outline",
]

_TARGET_LENGTH_MAP: dict[str, str] = {
    "youtube_video": "10-15 minutes (~2,000-3,000 words)",
    "youtube_short": "60 seconds (~150-200 words)",
    "podcast": "20-30 minutes (~4,000-6,000 words)",
    "blog": "1,500-2,500 words",
    "newsletter": "500-800 words",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_json(text: str) -> dict[str, Any] | list[dict[str, Any]]:
    """Parse JSON from an LLM response, stripping markdown fences if present."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Remove opening fence (with optional language tag) and closing fence
        lines = cleaned.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    return json.loads(cleaned)


def _extract_idea_fields(idea: dict[str, Any]) -> dict[str, str]:
    """Pull common fields from an idea dict with safe defaults."""
    return {
        "idea_title": idea.get("title", idea.get("hook", "Untitled")),
        "idea_hook": idea.get("hook", ""),
        "idea_angle": idea.get("angle", idea.get("differentiation", "")),
        "key_points": ", ".join(idea.get("key_points", idea.get("talking_points", []))),
    }


def _get_dna_prompt(creator_dna: dict[str, Any]) -> str:
    """Build the DNA conditioning block, tolerating empty / missing DNA."""
    if not creator_dna:
        return "[Creator DNA not yet available -- use a neutral, professional tone.]"
    return build_dna_prompt(creator_dna)


def _dna_voice_fields(creator_dna: dict[str, Any]) -> dict[str, Any]:
    """Extract voice-specific fields used by the tone-check prompt."""
    return {
        "vocabulary_complexity": creator_dna.get("vocabulary_complexity", 5),
        "formality_level": creator_dna.get("formality_level", 5),
        "humor_style": creator_dna.get("humor_style", "none detected"),
        "signature_phrases": ", ".join(
            creator_dna.get("signature_phrases", [])
        )
        or "N/A",
        "pacing_pattern": creator_dna.get("pacing_pattern", "moderate"),
    }


# ---------------------------------------------------------------------------
# Node: research
# ---------------------------------------------------------------------------


async def research(state: ScriptArchitectState) -> dict[str, Any]:
    """Search the web and knowledge graph for supporting data and examples."""
    logger.info("script_architect.research.start")

    idea: dict[str, Any] = state.get("idea", {})
    creator_dna: dict[str, Any] = state.get("creator_dna", {})
    content_type: str = state.get("content_type", _DEFAULT_CONTENT_TYPE)

    idea_fields = _extract_idea_fields(idea)
    dna_prompt = _get_dna_prompt(creator_dna)

    # ---- Gather external data in parallel-ish fashion ----
    search_query = f"{idea_fields['idea_title']} {idea_fields['idea_angle']}"

    web_results: dict[str, Any] = {}
    kg_results: dict[str, Any] = {}
    yt_results: dict[str, Any] = {}

    try:
        web_results = await google_search.ainvoke(
            {"query": search_query, "num_results": 10, "date_restrict": "m6"}
        )
    except Exception as exc:
        logger.warning("script_architect.research.web_search_failed", error=str(exc))

    try:
        kg_results = await search_knowledge_graph.ainvoke(
            {"query": search_query, "node_types": ["Topic", "Trend", "Content"], "limit": 15}
        )
    except Exception as exc:
        logger.warning("script_architect.research.kg_search_failed", error=str(exc))

    try:
        yt_results = await search_youtube.ainvoke(
            {"query": search_query, "max_results": 10, "order": "relevance"}
        )
    except Exception as exc:
        logger.warning("script_architect.research.yt_search_failed", error=str(exc))

    # ---- Ask the LLM to synthesise a research brief ----
    llm = get_llm(temperature=0.4, max_tokens=4096)

    research_context = (
        f"Web search results:\n{json.dumps(web_results.get('items', [])[:5], default=str)}\n\n"
        f"Knowledge graph results:\n{json.dumps(kg_results.get('results', {}), default=str)}\n\n"
        f"YouTube results:\n{json.dumps(yt_results.get('results', [])[:5], default=str)}"
    )

    prompt_text = RESEARCH_PROMPT.format(
        dna_conditioning=dna_prompt,
        content_type=content_type,
        creator_niche=creator_dna.get("primary_topics", "general"),
        creator_topics=", ".join(creator_dna.get("primary_topics", []))
        if isinstance(creator_dna.get("primary_topics"), list)
        else creator_dna.get("primary_topics", "general"),
        target_audience=creator_dna.get("audience_address_style", "general audience"),
        **idea_fields,
    )

    messages = [
        SystemMessage(content="You are the Script Architect research assistant. "
                      "Use the following external data to inform your response.\n\n"
                      f"{research_context}"),
        HumanMessage(content=prompt_text),
    ]

    response = await invoke_with_retry(llm, messages)
    try:
        research_data = _safe_json(response.content)
    except (json.JSONDecodeError, TypeError):
        logger.warning("script_architect.research.parse_failed")
        research_data = {"raw_response": response.content}

    logger.info("script_architect.research.complete")

    return {
        "reference_scripts": yt_results.get("results", [])[:5],
        "idea": {
            **idea,
            "research": research_data,
            "_web_results": web_results.get("items", [])[:5],
            "_kg_results": kg_results.get("results", {}),
        },
        "status": "research_complete",
    }


# ---------------------------------------------------------------------------
# Node: outline
# ---------------------------------------------------------------------------


async def outline(state: ScriptArchitectState) -> dict[str, Any]:
    """Create a structured outline with retention hooks mapped."""
    logger.info("script_architect.outline.start")

    idea: dict[str, Any] = state.get("idea", {})
    creator_dna: dict[str, Any] = state.get("creator_dna", {})
    content_type: str = state.get("content_type", _DEFAULT_CONTENT_TYPE)
    research_data: dict[str, Any] = idea.get("research", {})

    idea_fields = _extract_idea_fields(idea)
    dna_prompt = _get_dna_prompt(creator_dna)
    target_length = _TARGET_LENGTH_MAP.get(content_type, "10-15 minutes")

    prompt_text = OUTLINE_PROMPT.format(
        dna_conditioning=dna_prompt,
        content_type=content_type,
        target_length=target_length,
        research_findings=json.dumps(research_data, default=str)[:6000],
        creator_niche=creator_dna.get("primary_topics", "general")
        if not isinstance(creator_dna.get("primary_topics"), list)
        else ", ".join(creator_dna.get("primary_topics", [])),
        creator_topics=", ".join(creator_dna.get("primary_topics", []))
        if isinstance(creator_dna.get("primary_topics"), list)
        else creator_dna.get("primary_topics", "general"),
        **idea_fields,
    )

    llm = get_llm(temperature=0.6, max_tokens=4096)
    messages = [HumanMessage(content=prompt_text)]

    response = await invoke_with_retry(llm, messages)
    try:
        outline_data: dict[str, Any] = _safe_json(response.content)  # type: ignore[assignment]
    except (json.JSONDecodeError, TypeError):
        logger.warning("script_architect.outline.parse_failed")
        outline_data = {"raw_response": response.content}

    logger.info("script_architect.outline.complete")

    return {
        "outline": outline_data,
        "status": "outline_complete",
    }


# ---------------------------------------------------------------------------
# Node: draft_script
# ---------------------------------------------------------------------------


async def draft_script(state: ScriptArchitectState) -> dict[str, Any]:
    """Write the full script using the creator's DNA voice."""
    logger.info("script_architect.draft_script.start")

    idea: dict[str, Any] = state.get("idea", {})
    creator_dna: dict[str, Any] = state.get("creator_dna", {})
    content_type: str = state.get("content_type", _DEFAULT_CONTENT_TYPE)
    outline_data: dict[str, Any] = state.get("outline", {})
    research_data: dict[str, Any] = idea.get("research", {})
    target_length = _TARGET_LENGTH_MAP.get(content_type, "10-15 minutes")

    dna_prompt = _get_dna_prompt(creator_dna)

    prompt_text = DRAFT_SCRIPT_PROMPT.format(
        dna_conditioning=dna_prompt,
        outline=json.dumps(outline_data, default=str)[:8000],
        research_findings=json.dumps(research_data, default=str)[:4000],
        content_type=content_type,
        target_length=target_length,
    )

    llm = get_llm(temperature=0.75, max_tokens=8192)
    messages = [HumanMessage(content=prompt_text)]

    response = await invoke_with_retry(llm, messages)
    try:
        script_data: dict[str, Any] = _safe_json(response.content)  # type: ignore[assignment]
        script_body: str = script_data.get("script_body", response.content)
    except (json.JSONDecodeError, TypeError):
        logger.warning("script_architect.draft_script.parse_failed")
        script_body = response.content
        script_data = {"script_body": script_body}

    hook_variants: list[str] = []
    for hp in script_data.get("hook_placements", []):
        preview = hp.get("text_preview", "")
        if preview:
            hook_variants.append(preview)

    logger.info(
        "script_architect.draft_script.complete",
        word_count=script_data.get("word_count", len(script_body.split())),
    )

    return {
        "draft_script": script_body,
        "hook_variants": hook_variants,
        "script_metadata": {
            k: v for k, v in script_data.items() if k != "script_body"
        },
        "status": "draft_complete",
    }


# ---------------------------------------------------------------------------
# Node: inject_hooks
# ---------------------------------------------------------------------------


async def inject_hooks(state: ScriptArchitectState) -> dict[str, Any]:
    """Add pattern interrupts, open loops, curiosity gaps every 60-90s."""
    logger.info("script_architect.inject_hooks.start")

    creator_dna: dict[str, Any] = state.get("creator_dna", {})
    content_type: str = state.get("content_type", _DEFAULT_CONTENT_TYPE)
    script_body: str = state.get("draft_script", "")
    hook_variants: list[str] = state.get("hook_variants", [])

    dna_prompt = _get_dna_prompt(creator_dna)

    prompt_text = INJECT_HOOKS_PROMPT.format(
        dna_conditioning=dna_prompt,
        script_body=script_body[:12000],
        content_type=content_type,
        current_hook_count=len(hook_variants),
    )

    llm = get_llm(temperature=0.7, max_tokens=8192)
    messages = [HumanMessage(content=prompt_text)]

    response = await invoke_with_retry(llm, messages)
    try:
        hooks_data: dict[str, Any] = _safe_json(response.content)  # type: ignore[assignment]
        enhanced_body: str = hooks_data.get("enhanced_script_body", script_body)
    except (json.JSONDecodeError, TypeError):
        logger.warning("script_architect.inject_hooks.parse_failed")
        enhanced_body = response.content if len(response.content) > len(script_body) * 0.5 else script_body
        hooks_data = {}

    hooks_added: int = hooks_data.get("hooks_added", 0)
    logger.info("script_architect.inject_hooks.complete", hooks_added=hooks_added)

    # Update hook_variants with newly injected hooks
    new_hook_variants = list(hook_variants)
    for detail in hooks_data.get("hook_details", []):
        text = detail.get("hook_text", "")
        if text:
            new_hook_variants.append(text)

    return {
        "draft_script": enhanced_body,
        "hook_variants": new_hook_variants,
        "script_metadata": {
            **state.get("script_metadata", {}),
            "hooks_injected": hooks_added,
            "estimated_retention_improvement": hooks_data.get(
                "estimated_retention_improvement", "N/A"
            ),
        },
        "status": "hooks_injected",
    }


# ---------------------------------------------------------------------------
# Node: tone_check
# ---------------------------------------------------------------------------


async def tone_check(state: ScriptArchitectState) -> dict[str, Any]:
    """Verify the script matches creator DNA and apply rewrites if needed."""
    logger.info("script_architect.tone_check.start")

    creator_dna: dict[str, Any] = state.get("creator_dna", {})
    script_body: str = state.get("draft_script", "")
    dna_prompt = _get_dna_prompt(creator_dna)
    voice_fields = _dna_voice_fields(creator_dna)

    prompt_text = TONE_CHECK_PROMPT.format(
        dna_conditioning=dna_prompt,
        script_body=script_body[:12000],
        **voice_fields,
    )

    llm = get_llm(temperature=0.3, max_tokens=4096)
    messages = [HumanMessage(content=prompt_text)]

    response = await invoke_with_retry(llm, messages)
    try:
        tone_data: dict[str, Any] = _safe_json(response.content)  # type: ignore[assignment]
    except (json.JSONDecodeError, TypeError):
        logger.warning("script_architect.tone_check.parse_failed")
        tone_data = {"voice_consistency_score": 0, "raw_response": response.content}

    voice_score: float = float(tone_data.get("voice_consistency_score", 0))

    # If the voice score is acceptable (>= 7), keep the script as-is.
    # Otherwise, apply the suggested rewrites automatically.
    final_script = script_body
    if voice_score < 7.0 and tone_data.get("flagged_passages"):
        logger.info(
            "script_architect.tone_check.applying_rewrites",
            voice_score=voice_score,
            flagged_count=len(tone_data["flagged_passages"]),
        )
        for passage in tone_data["flagged_passages"]:
            original = passage.get("original_text", "")
            rewrite = passage.get("suggested_rewrite", "")
            if original and rewrite and original in final_script:
                final_script = final_script.replace(original, rewrite, 1)

    logger.info(
        "script_architect.tone_check.complete",
        voice_score=voice_score,
    )

    return {
        "final_script": final_script,
        "script_metadata": {
            **state.get("script_metadata", {}),
            "voice_consistency_score": voice_score,
            "tone_check": {
                "overall_assessment": tone_data.get("overall_assessment", ""),
                "flagged_count": len(tone_data.get("flagged_passages", [])),
                "humor_check": tone_data.get("humor_check", {}),
                "signature_phrase_usage": tone_data.get("signature_phrase_usage", {}),
            },
        },
        "status": "tone_checked",
    }


# ---------------------------------------------------------------------------
# Node: generate_variants
# ---------------------------------------------------------------------------


async def generate_variants(state: ScriptArchitectState) -> dict[str, Any]:
    """Produce platform variants: blog, twitter, linkedin, newsletter, podcast, shorts."""
    logger.info("script_architect.generate_variants.start")

    creator_dna: dict[str, Any] = state.get("creator_dna", {})
    content_type: str = state.get("content_type", _DEFAULT_CONTENT_TYPE)
    final_script: str = state.get("final_script", state.get("draft_script", ""))
    script_metadata: dict[str, Any] = state.get("script_metadata", {})
    title: str = script_metadata.get("title", state.get("idea", {}).get("title", "Untitled"))

    dna_prompt = _get_dna_prompt(creator_dna)

    prompt_text = GENERATE_VARIANTS_PROMPT.format(
        dna_conditioning=dna_prompt,
        original_title=title,
        original_content_type=content_type,
        script_body=final_script[:10000],
        target_variants=", ".join(_TARGET_VARIANTS),
    )

    llm = get_llm(temperature=0.7, max_tokens=8192)
    messages = [HumanMessage(content=prompt_text)]

    response = await invoke_with_retry(llm, messages)
    try:
        variants_data = _safe_json(response.content)
        if isinstance(variants_data, dict):
            # LLM may have wrapped the array inside a key
            variants_list: list[dict[str, Any]] = variants_data.get(
                "variants", [variants_data]
            )
        else:
            variants_list = variants_data  # type: ignore[assignment]
    except (json.JSONDecodeError, TypeError):
        logger.warning("script_architect.generate_variants.parse_failed")
        variants_list = [{"variant_type": "raw", "body": response.content}]

    logger.info(
        "script_architect.generate_variants.complete",
        variant_count=len(variants_list),
    )

    return {
        "variants": variants_list,
        "status": "variants_generated",
    }


# ---------------------------------------------------------------------------
# Node: human_gate
# ---------------------------------------------------------------------------


async def human_gate(state: ScriptArchitectState) -> dict[str, Any]:
    """Present the final script for creator review.

    In a real deployment this node would emit a ``__interrupt__`` signal
    so that the LangGraph checkpoint waits for human input.  For now it
    packages everything the human UI needs and marks the run as
    ``awaiting_review``.
    """
    logger.info("script_architect.human_gate.start")

    final_script: str = state.get("final_script", state.get("draft_script", ""))
    outline_data: dict[str, Any] = state.get("outline", {})
    script_metadata: dict[str, Any] = state.get("script_metadata", {})
    variants: list[dict[str, Any]] = state.get("variants", [])
    hook_variants: list[str] = state.get("hook_variants", [])
    cta_variants: list[str] = state.get("cta_variants", [])

    # Derive CTA from outline if not already present
    if not cta_variants and outline_data.get("call_to_action"):
        cta_variants = [outline_data["call_to_action"]]

    review_package: dict[str, Any] = {
        "final_script": final_script,
        "outline": outline_data,
        "metadata": script_metadata,
        "variants_count": len(variants),
        "hook_count": len(hook_variants),
        "word_count": len(final_script.split()),
    }

    logger.info(
        "script_architect.human_gate.ready",
        word_count=review_package["word_count"],
        variants=review_package["variants_count"],
    )

    return {
        "final_script": final_script,
        "cta_variants": cta_variants,
        "script_metadata": {
            **script_metadata,
            "review_package": review_package,
        },
        "status": "awaiting_review",
    }


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def create_script_architect_graph() -> StateGraph:
    """Build and compile the Script Architect LangGraph StateGraph.

    Returns
    -------
    langgraph.graph.StateGraph
        The compiled graph ready for ``.ainvoke()`` or ``.astream()``.
    """
    graph = StateGraph(ScriptArchitectState)

    # Register nodes
    graph.add_node("research", research)
    graph.add_node("outline", outline)
    graph.add_node("draft_script", draft_script)
    graph.add_node("inject_hooks", inject_hooks)
    graph.add_node("tone_check", tone_check)
    graph.add_node("generate_variants", generate_variants)
    graph.add_node("human_gate", human_gate)

    # Linear edge chain
    graph.set_entry_point("research")
    graph.add_edge("research", "outline")
    graph.add_edge("outline", "draft_script")
    graph.add_edge("draft_script", "inject_hooks")
    graph.add_edge("inject_hooks", "tone_check")
    graph.add_edge("tone_check", "generate_variants")
    graph.add_edge("generate_variants", "human_gate")
    graph.add_edge("human_gate", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# High-level runner
# ---------------------------------------------------------------------------


async def run_script_architect(
    idea: dict[str, Any],
    creator_dna: dict[str, Any],
    content_type: str = "youtube_video",
    *,
    user_id: Optional[str] = None,
) -> dict[str, Any]:
    """Run the full Script Architect pipeline end-to-end.

    Parameters
    ----------
    idea:
        The approved content idea dictionary.  Expected keys include
        ``title``, ``hook``, ``angle``, ``key_points``, etc.
    creator_dna:
        The creator's DNA fingerprint dictionary (from ``CreatorDNA.model_dump()``).
    content_type:
        Target content format -- ``"youtube_video"``, ``"podcast"``,
        ``"youtube_short"``, ``"blog"``, or ``"newsletter"``.
    user_id:
        Optional user identifier for traceability.

    Returns
    -------
    dict[str, Any]
        The final ``ScriptArchitectState`` containing ``final_script``,
        ``outline``, ``variants``, ``script_metadata``, and ``status``.
    """
    logger.info(
        "script_architect.run.start",
        idea_title=idea.get("title", "unknown"),
        content_type=content_type,
        user_id=user_id,
    )

    graph = create_script_architect_graph()

    initial_state: ScriptArchitectState = {
        "idea": idea,
        "creator_dna": creator_dna,
        "content_type": content_type,
        "reference_scripts": [],
        "outline": {},
        "draft_script": "",
        "hook_variants": [],
        "cta_variants": [],
        "final_script": "",
        "script_metadata": {},
        "variants": [],
        "status": "starting",
    }

    if user_id:
        initial_state["user_id"] = user_id

    try:
        result = await graph.ainvoke(initial_state)
        logger.info(
            "script_architect.run.complete",
            status=result.get("status"),
            word_count=len(result.get("final_script", "").split()),
            variants=len(result.get("variants", [])),
        )
        return result
    except Exception as exc:
        logger.exception("script_architect.run.error", error=str(exc))
        return {
            **initial_state,
            "status": "error",
            "error": str(exc),
        }
