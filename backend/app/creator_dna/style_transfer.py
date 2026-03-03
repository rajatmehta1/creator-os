"""Build DNA conditioning prompt blocks for agent system prompt injection.

This module is the bridge between the stored Creator DNA fingerprint and the
agent prompt system.  It formats the DNA data into the conditioning template
defined in ``app.core.prompts.templates`` so that every agent output sounds
like the creator.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.core.prompts.templates import format_dna_prompt

logger = structlog.get_logger(__name__)

# Minimum confidence score to include full DNA conditioning.
# Below this threshold a softer, partial conditioning block is used.
_MIN_CONFIDENCE_THRESHOLD = 15.0

_LOW_CONFIDENCE_TEMPLATE = """\
=== CREATOR VOICE PROFILE (LOW CONFIDENCE) ===
The creator's voice profile is still being built (confidence: {confidence}%,
{videos_analyzed} video(s) analyzed).  Use the following partial signals as
gentle guidance, but prioritize clarity and professionalism over strict
voice matching.

Detected signals so far:
- Humor style: {humor_style}
- Hook style: {hook_style}
- Formality: {formality_level}/10
- Pacing: {pacing_pattern}
{extra_signals}
=== END CREATOR VOICE PROFILE ===
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_dna_prompt(dna: dict[str, Any]) -> str:
    """Format a Creator DNA dict into a conditioning prompt block.

    When the DNA confidence score is above the threshold, the full DNA
    conditioning template is rendered.  When confidence is low (fewer than
    ~3 videos analyzed), a softer partial-conditioning block is used instead
    so the LLM does not over-fit to noisy signals.

    Parameters
    ----------
    dna:
        A dictionary representation of the Creator DNA.  Typically produced
        by ``CreatorDNA.model_dump()`` or read from storage.

    Returns
    -------
    str
        The fully rendered conditioning block, ready to be inserted into an
        agent system prompt via the ``{dna_conditioning}`` placeholder.
    """
    confidence = dna.get("confidence_score", 0.0)
    videos_analyzed = dna.get("videos_analyzed", 0)

    if not dna or confidence <= 0:
        logger.info("style_transfer.no_dna")
        return (
            "[Creator DNA not yet available -- use a neutral, professional tone.]"
        )

    if confidence < _MIN_CONFIDENCE_THRESHOLD:
        logger.info(
            "style_transfer.low_confidence",
            confidence=confidence,
            videos=videos_analyzed,
        )
        return _build_low_confidence_block(dna)

    logger.info(
        "style_transfer.full_conditioning",
        confidence=confidence,
        videos=videos_analyzed,
    )
    return format_dna_prompt(dna)


def _build_low_confidence_block(dna: dict[str, Any]) -> str:
    """Render the low-confidence conditioning block."""
    extra_lines: list[str] = []

    sig_phrases = dna.get("signature_phrases", [])
    if sig_phrases:
        extra_lines.append(
            f"- Signature phrases spotted: {', '.join(sig_phrases[:5])}"
        )

    fillers = dna.get("filler_words", [])
    if fillers:
        extra_lines.append(
            f"- Filler words spotted: {', '.join(fillers[:5])}"
        )

    emotions = dna.get("emotional_range", [])
    if emotions:
        extra_lines.append(
            f"- Emotional range: {', '.join(emotions[:4])}"
        )

    audience = dna.get("audience_address_style")
    if audience:
        extra_lines.append(f"- Audience address: {audience}")

    extra_signals = "\n".join(extra_lines) if extra_lines else "- (no additional signals yet)"

    return _LOW_CONFIDENCE_TEMPLATE.format(
        confidence=round(dna.get("confidence_score", 0.0), 1),
        videos_analyzed=dna.get("videos_analyzed", 0),
        humor_style=dna.get("humor_style", "unknown"),
        hook_style=dna.get("hook_style", "unknown"),
        formality_level=dna.get("formality_level", 5),
        pacing_pattern=dna.get("pacing_pattern", "unknown"),
        extra_signals=extra_signals,
    )
