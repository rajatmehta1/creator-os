"""Analyze video transcripts via LLM to extract Creator DNA characteristics.

This module sends a transcript through the LLM and returns a structured
dictionary of voice and style attributes that feed into the Creator DNA
fingerprint.
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm, invoke_with_retry

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Analysis prompt
# ---------------------------------------------------------------------------

_TRANSCRIPT_ANALYSIS_SYSTEM = """\
You are an expert linguist and content analyst specializing in creator voice
fingerprinting.  Your job is to analyze a video transcript and extract
measurable stylistic characteristics.

Be precise and quantitative where possible.  Base your analysis ONLY on
evidence present in the transcript -- do not infer traits that are not
demonstrated.
"""

_TRANSCRIPT_ANALYSIS_USER = """\
Analyze the following video transcript and extract the creator's stylistic
characteristics.

TRANSCRIPT:
---
{transcript}
---

Extract the following attributes and return them as a JSON object.  Use the
exact keys specified.

{{
    "vocabulary_complexity": <float 1-10, where 1 = very simple / conversational
        and 10 = highly technical / academic>,
    "sentence_rhythm": {{
        "avg_sentence_length_words": <float>,
        "short_sentence_ratio": <float 0-1, sentences under 8 words>,
        "long_sentence_ratio": <float 0-1, sentences over 25 words>,
        "rhythm_pattern": "<staccato | flowing | mixed | punchy>"
    }},
    "humor_style": "<self_deprecating | observational | absurdist | sarcastic |
        dry_wit | physical | none>",
    "humor_frequency": <float 0-10, where 0 = no humor and 10 = comedy-focused>,
    "formality_level": <float 1-10, where 1 = extremely casual and
        10 = very formal/professional>,
    "hook_style": "<question | bold_claim | story | statistic | contrast |
        direct_challenge | curiosity_gap>",
    "pacing_pattern": "<rapid_fire | steady | building | varied | slow_burn>",
    "filler_words": [<list of filler words/phrases the creator uses, e.g.
        "you know", "like", "basically", "right">],
    "signature_phrases": [<list of recurring phrases or verbal tics unique
        to this creator, max 10>],
    "audience_address_style": "<direct_you | inclusive_we | third_person |
        mixed>",
    "vulnerability_level": <float 0-10, how openly the creator shares
        personal struggles or uncertainty>,
    "storytelling_frequency": <float 0-10, how often the creator uses
        anecdotes and narratives>,
    "call_to_action_style": "<aggressive | subtle | organic | none>",
    "emotional_range": [<list of primary emotions expressed, e.g.
        "enthusiasm", "frustration", "wonder">],
    "technical_depth": <float 1-10, how deep into technical details they go>
}}

Return ONLY the JSON object.  No additional text.
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def analyze_transcript(
    transcript: str,
    *,
    model: str | None = None,
    temperature: float = 0.3,
) -> dict[str, Any]:
    """Analyze a single transcript and extract voice/style attributes.

    Parameters
    ----------
    transcript:
        The full text of a video transcript.
    model:
        Optional model override.  Defaults to the configured primary LLM.
    temperature:
        Sampling temperature -- kept low for analytical consistency.

    Returns
    -------
    dict
        A dictionary of extracted stylistic characteristics.  Keys match
        the JSON schema defined in the analysis prompt.

    Raises
    ------
    ValueError
        If the transcript is empty or the LLM returns unparseable output.
    """
    transcript = transcript.strip()
    if not transcript:
        raise ValueError("Cannot analyze an empty transcript.")

    logger.info(
        "creator_dna.analyze_transcript",
        transcript_length=len(transcript),
    )

    llm = get_llm(model=model, temperature=temperature, fallback=True)

    messages = [
        SystemMessage(content=_TRANSCRIPT_ANALYSIS_SYSTEM),
        HumanMessage(
            content=_TRANSCRIPT_ANALYSIS_USER.format(transcript=transcript)
        ),
    ]

    response = await invoke_with_retry(llm, messages)
    raw_text = response.content.strip()

    # Strip markdown code fences if present.
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        # Remove first and last fence lines.
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw_text = "\n".join(lines)

    try:
        analysis: dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.error(
            "creator_dna.analyze_transcript.parse_error",
            raw_text=raw_text[:500],
            error=str(exc),
        )
        raise ValueError(
            f"LLM returned unparseable JSON for transcript analysis: {exc}"
        ) from exc

    logger.info(
        "creator_dna.analyze_transcript.complete",
        keys=list(analysis.keys()),
    )

    return analysis
