"""Shared prompt templates and the Creator DNA conditioning block.

The DNA conditioning template is the cornerstone of voice-consistent content
generation.  It is injected into every agent system prompt so that outputs
match the creator's unique style.
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# DNA conditioning block -- injected into every agent system prompt
# ---------------------------------------------------------------------------

DNA_CONDITIONING_TEMPLATE = """\
=== CREATOR VOICE PROFILE ===
You are generating content that MUST match the following creator's unique style.
Study these characteristics carefully and apply them consistently.

VOCABULARY & LANGUAGE
- Complexity level: {vocabulary_complexity}/10
- Signature phrases: {signature_phrases}
- Filler words (use sparingly for authenticity): {filler_words}
- Formality level: {formality_level}/10

SENTENCE RHYTHM & PACING
- Rhythm pattern: {sentence_rhythm}
- Pacing style: {pacing_pattern}
- Average sentence length variation: {sentence_length_variation}

HUMOR & TONE
- Humor style: {humor_style}
- Humor frequency: {humor_frequency}/10
- Audience address style: {audience_address_style}
- Vulnerability level: {vulnerability_level}/10

CONTENT STRUCTURE
- Hook style: {hook_style}
- Storytelling frequency: {storytelling_frequency}/10
- Call-to-action style: {call_to_action_style}

TOPIC EXPERTISE
- Primary topics: {primary_topics}
- Expertise depth by topic: {expertise_depth}

CONFIDENCE: {confidence_score}% (based on {videos_analyzed} videos analyzed)
=== END CREATOR VOICE PROFILE ===
"""

# ---------------------------------------------------------------------------
# Base system template -- wraps agent-specific instructions
# ---------------------------------------------------------------------------

SYSTEM_BASE_TEMPLATE = """\
You are a specialized AI agent inside Creator OS, a content creation platform
for YouTube creators.  You operate as the **{agent_name}** agent.

{dna_conditioning}

{agent_instructions}

Always respond in valid JSON matching the required output schema unless
explicitly told otherwise.  Be concise, specific, and actionable.
"""


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def format_dna_prompt(dna_data: dict[str, Any]) -> str:
    """Format a Creator DNA dict into the conditioning template string.

    Missing keys are replaced with sensible defaults so the template never
    raises a ``KeyError``.

    Parameters
    ----------
    dna_data:
        A dictionary (typically ``CreatorDNA.model_dump()``) containing voice
        profile fields.

    Returns
    -------
    str
        The fully rendered DNA conditioning block ready for prompt injection.
    """
    defaults: dict[str, Any] = {
        "vocabulary_complexity": 5,
        "signature_phrases": "N/A",
        "filler_words": "N/A",
        "formality_level": 5,
        "sentence_rhythm": "mixed",
        "pacing_pattern": "moderate",
        "sentence_length_variation": "moderate",
        "humor_style": "none detected",
        "humor_frequency": 0,
        "audience_address_style": "direct",
        "vulnerability_level": 3,
        "hook_style": "question-based",
        "storytelling_frequency": 5,
        "call_to_action_style": "standard",
        "primary_topics": "general",
        "expertise_depth": "{}",
        "confidence_score": 0,
        "videos_analyzed": 0,
    }

    merged = {**defaults, **dna_data}

    # Ensure list values are rendered as comma-separated strings.
    for key in ("signature_phrases", "filler_words", "primary_topics"):
        value = merged[key]
        if isinstance(value, list):
            merged[key] = ", ".join(str(v) for v in value) if value else "N/A"

    # Ensure dict values are rendered readably.
    for key in ("expertise_depth", "sentence_rhythm"):
        value = merged[key]
        if isinstance(value, dict):
            merged[key] = ", ".join(f"{k}: {v}" for k, v in value.items()) or "N/A"

    try:
        rendered = DNA_CONDITIONING_TEMPLATE.format(**merged)
    except KeyError as exc:
        logger.error("prompts.format_dna_prompt.missing_key", key=str(exc))
        raise

    logger.debug(
        "prompts.format_dna_prompt",
        confidence=merged.get("confidence_score"),
        videos=merged.get("videos_analyzed"),
    )

    return rendered


def format_system_prompt(
    agent_name: str,
    agent_instructions: str,
    dna_data: dict[str, Any] | None = None,
) -> str:
    """Build a complete system prompt for an agent.

    Parameters
    ----------
    agent_name:
        Human-readable agent name (e.g. ``"Trend Scout"``).
    agent_instructions:
        The agent-specific instruction block.
    dna_data:
        Optional Creator DNA dict.  When provided the DNA conditioning block
        is injected; otherwise a placeholder note is used.

    Returns
    -------
    str
        The fully rendered system prompt.
    """
    if dna_data:
        dna_block = format_dna_prompt(dna_data)
    else:
        dna_block = (
            "[Creator DNA not yet available -- use a neutral, professional tone.]"
        )

    return SYSTEM_BASE_TEMPLATE.format(
        agent_name=agent_name,
        dna_conditioning=dna_block,
        agent_instructions=agent_instructions,
    )
