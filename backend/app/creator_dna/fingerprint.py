"""Aggregate per-video analyses into a unified Creator DNA fingerprint.

Takes a list of individual transcript analysis dicts (from ``analyzer.py``)
and computes averages, distributions, and a confidence score to produce a
single ``CreatorDNA`` Pydantic model.
"""

from __future__ import annotations

import math
from collections import Counter
from datetime import datetime, timezone
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# CreatorDNA Pydantic model
# ---------------------------------------------------------------------------


class CreatorDNA(BaseModel):
    """The complete Creator DNA fingerprint.

    This is the canonical representation of a creator's voice, style, and
    content characteristics.  It is built by aggregating multiple transcript
    analyses.
    """

    # Voice characteristics
    vocabulary_complexity: float = Field(
        default=5.0, ge=1.0, le=10.0, description="Average vocabulary complexity."
    )
    sentence_rhythm: dict[str, Any] = Field(
        default_factory=dict,
        description="Aggregate sentence rhythm metrics.",
    )
    filler_words: list[str] = Field(
        default_factory=list,
        description="Most common filler words across all transcripts.",
    )
    signature_phrases: list[str] = Field(
        default_factory=list,
        description="Most frequently recurring signature phrases.",
    )
    humor_style: str = Field(
        default="none",
        description="Dominant humor style.",
    )
    humor_frequency: float = Field(
        default=0.0, ge=0.0, le=10.0, description="Average humor frequency."
    )

    # Topic profile
    topic_clusters: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Detected topic clusters.",
    )
    expertise_depth: dict[str, float] = Field(
        default_factory=dict,
        description="Expertise depth per topic.",
    )

    # Audience relationship
    formality_level: float = Field(
        default=5.0, ge=1.0, le=10.0, description="Average formality level."
    )
    audience_address_style: str = Field(
        default="direct_you",
        description="Dominant audience address style.",
    )
    vulnerability_level: float = Field(
        default=3.0, ge=0.0, le=10.0, description="Average vulnerability level."
    )
    call_to_action_style: str = Field(
        default="standard",
        description="Dominant CTA style.",
    )

    # Content structure
    preferred_format_length: dict[str, float] = Field(
        default_factory=dict,
        description="Preferred content lengths by format.",
    )
    hook_style: str = Field(
        default="question",
        description="Dominant hook style.",
    )
    pacing_pattern: str = Field(
        default="moderate",
        description="Dominant pacing pattern.",
    )
    storytelling_frequency: float = Field(
        default=5.0,
        ge=0.0,
        le=10.0,
        description="Average storytelling frequency.",
    )

    # Emotional profile
    emotional_range: list[str] = Field(
        default_factory=list,
        description="Most common emotions expressed.",
    )
    technical_depth: float = Field(
        default=5.0, ge=1.0, le=10.0, description="Average technical depth."
    )

    # Meta
    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Confidence percentage based on number of videos analyzed.",
    )
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the fingerprint was last computed.",
    )
    videos_analyzed: int = Field(
        default=0,
        ge=0,
        description="Number of transcripts that contributed to this fingerprint.",
    )


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------


def _mean(values: list[float | int]) -> float:
    """Safe arithmetic mean that returns 0.0 for empty lists."""
    return sum(values) / len(values) if values else 0.0


def _most_common(values: list[str], n: int = 1) -> str:
    """Return the most common string, or fallback to the first value."""
    if not values:
        return "unknown"
    counter = Counter(values)
    return counter.most_common(n)[0][0]


def _top_n_items(values: list[str], n: int = 10) -> list[str]:
    """Return the *n* most common items preserving rank order."""
    if not values:
        return []
    counter = Counter(values)
    return [item for item, _ in counter.most_common(n)]


def _compute_confidence(num_videos: int) -> float:
    """Compute a confidence score (0-100) based on the number of videos.

    The curve follows a logarithmic shape:
    - 1 video   ~  15%
    - 3 videos  ~  40%
    - 5 videos  ~  55%
    - 10 videos ~  75%
    - 20 videos ~  90%
    - 50+ videos ~ 99%
    """
    if num_videos <= 0:
        return 0.0
    # Logarithmic growth capped at 100
    raw = 15.0 * math.log2(num_videos + 1)
    return round(min(raw, 100.0), 1)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_fingerprint(analyses: list[dict[str, Any]]) -> CreatorDNA:
    """Aggregate individual transcript analyses into a CreatorDNA fingerprint.

    Parameters
    ----------
    analyses:
        A list of dicts, each produced by ``analyzer.analyze_transcript``.
        An empty list returns a default ``CreatorDNA`` with zero confidence.

    Returns
    -------
    CreatorDNA
        The aggregated fingerprint model.
    """
    num = len(analyses)
    if num == 0:
        logger.warning("creator_dna.fingerprint.empty_analyses")
        return CreatorDNA(videos_analyzed=0, confidence_score=0.0)

    logger.info("creator_dna.fingerprint.building", num_analyses=num)

    # --- Numeric averages ---
    vocabulary_complexity = _mean(
        [a.get("vocabulary_complexity", 5.0) for a in analyses]
    )
    humor_frequency = _mean([a.get("humor_frequency", 0.0) for a in analyses])
    formality_level = _mean([a.get("formality_level", 5.0) for a in analyses])
    vulnerability_level = _mean(
        [a.get("vulnerability_level", 3.0) for a in analyses]
    )
    storytelling_frequency = _mean(
        [a.get("storytelling_frequency", 5.0) for a in analyses]
    )
    technical_depth = _mean([a.get("technical_depth", 5.0) for a in analyses])

    # --- Sentence rhythm aggregation ---
    rhythm_dicts = [a.get("sentence_rhythm", {}) for a in analyses if isinstance(a.get("sentence_rhythm"), dict)]
    sentence_rhythm: dict[str, Any] = {}
    if rhythm_dicts:
        sentence_rhythm = {
            "avg_sentence_length_words": round(
                _mean([r.get("avg_sentence_length_words", 0) for r in rhythm_dicts]),
                1,
            ),
            "short_sentence_ratio": round(
                _mean([r.get("short_sentence_ratio", 0) for r in rhythm_dicts]),
                2,
            ),
            "long_sentence_ratio": round(
                _mean([r.get("long_sentence_ratio", 0) for r in rhythm_dicts]),
                2,
            ),
            "rhythm_pattern": _most_common(
                [r.get("rhythm_pattern", "mixed") for r in rhythm_dicts]
            ),
        }

    # --- Categorical modes ---
    humor_style = _most_common(
        [a.get("humor_style", "none") for a in analyses]
    )
    hook_style = _most_common(
        [a.get("hook_style", "question") for a in analyses]
    )
    pacing_pattern = _most_common(
        [a.get("pacing_pattern", "moderate") for a in analyses]
    )
    audience_address_style = _most_common(
        [a.get("audience_address_style", "direct_you") for a in analyses]
    )
    call_to_action_style = _most_common(
        [a.get("call_to_action_style", "standard") for a in analyses]
    )

    # --- List aggregation (flatten + count) ---
    all_fillers: list[str] = []
    all_phrases: list[str] = []
    all_emotions: list[str] = []
    for a in analyses:
        all_fillers.extend(a.get("filler_words", []))
        all_phrases.extend(a.get("signature_phrases", []))
        all_emotions.extend(a.get("emotional_range", []))

    filler_words = _top_n_items(all_fillers, n=10)
    signature_phrases = _top_n_items(all_phrases, n=15)
    emotional_range = _top_n_items(all_emotions, n=8)

    # --- Confidence ---
    confidence_score = _compute_confidence(num)

    fingerprint = CreatorDNA(
        vocabulary_complexity=round(vocabulary_complexity, 1),
        sentence_rhythm=sentence_rhythm,
        filler_words=filler_words,
        signature_phrases=signature_phrases,
        humor_style=humor_style,
        humor_frequency=round(humor_frequency, 1),
        formality_level=round(formality_level, 1),
        audience_address_style=audience_address_style,
        vulnerability_level=round(vulnerability_level, 1),
        call_to_action_style=call_to_action_style,
        hook_style=hook_style,
        pacing_pattern=pacing_pattern,
        storytelling_frequency=round(storytelling_frequency, 1),
        emotional_range=emotional_range,
        technical_depth=round(technical_depth, 1),
        confidence_score=confidence_score,
        videos_analyzed=num,
        last_updated=datetime.now(timezone.utc),
    )

    logger.info(
        "creator_dna.fingerprint.complete",
        confidence=confidence_score,
        videos=num,
    )

    return fingerprint
