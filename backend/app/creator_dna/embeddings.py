"""Generate and store composite DNA embedding vectors.

Converts a Creator DNA fingerprint into a 768-dimensional embedding vector
by serializing the structured data into a natural-language summary and
embedding it.  The vector is stored in a ChromaDB collection for similarity
search across creators.
"""

from __future__ import annotations

import json
from typing import Any

import chromadb
import structlog

from app.config import get_settings
from app.core.embeddings import generate_embedding

logger = structlog.get_logger(__name__)

# ChromaDB collection name for DNA vectors.
_COLLECTION_NAME = "creator_dna"

# Target embedding dimensions (text-embedding-3-small supports custom dims).
_TARGET_DIMENSIONS = 768


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _dna_to_text(dna: dict[str, Any]) -> str:
    """Serialize a Creator DNA dict into a natural-language paragraph.

    This textual representation is what gets embedded.  The richer and more
    structured the text, the better the embedding captures the creator's
    unique characteristics.
    """
    parts: list[str] = []

    # Voice characteristics
    parts.append(
        f"This creator has a vocabulary complexity of "
        f"{dna.get('vocabulary_complexity', 5)}/10 "
        f"and a formality level of {dna.get('formality_level', 5)}/10."
    )

    humor = dna.get("humor_style", "none")
    humor_freq = dna.get("humor_frequency", 0)
    parts.append(
        f"Their humor style is {humor} with a frequency of {humor_freq}/10."
    )

    # Signature phrases
    phrases = dna.get("signature_phrases", [])
    if phrases:
        parts.append(
            f"Signature phrases include: {', '.join(phrases[:10])}."
        )

    fillers = dna.get("filler_words", [])
    if fillers:
        parts.append(
            f"Common filler words: {', '.join(fillers[:8])}."
        )

    # Rhythm and pacing
    rhythm = dna.get("sentence_rhythm", {})
    if isinstance(rhythm, dict) and rhythm:
        pattern = rhythm.get("rhythm_pattern", "mixed")
        parts.append(f"Sentence rhythm is {pattern}.")

    pacing = dna.get("pacing_pattern", "moderate")
    parts.append(f"Content pacing is {pacing}.")

    # Content structure
    hook = dna.get("hook_style", "question")
    parts.append(f"Preferred hook style: {hook}.")

    storytelling = dna.get("storytelling_frequency", 5)
    parts.append(f"Storytelling frequency: {storytelling}/10.")

    # Audience relationship
    address = dna.get("audience_address_style", "direct_you")
    parts.append(f"Audience address style: {address}.")

    vuln = dna.get("vulnerability_level", 3)
    parts.append(f"Vulnerability level: {vuln}/10.")

    cta = dna.get("call_to_action_style", "standard")
    parts.append(f"CTA style: {cta}.")

    # Emotional range
    emotions = dna.get("emotional_range", [])
    if emotions:
        parts.append(f"Emotional range: {', '.join(emotions[:6])}.")

    tech = dna.get("technical_depth", 5)
    parts.append(f"Technical depth: {tech}/10.")

    # Topic clusters
    topics = dna.get("topic_clusters", [])
    if topics:
        cluster_names = [
            t.get("name", t.get("cluster_name", ""))
            for t in topics
            if isinstance(t, dict)
        ]
        if cluster_names:
            parts.append(f"Topic clusters: {', '.join(cluster_names)}.")

    return " ".join(parts)


def _get_chroma_collection() -> chromadb.Collection:
    """Return the ChromaDB collection for DNA embeddings."""
    settings = get_settings()
    client = chromadb.HttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port,
    )
    return client.get_or_create_collection(
        name=_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_dna_embedding(
    dna: dict[str, Any],
    *,
    creator_id: str | None = None,
) -> list[float]:
    """Generate a 768-dim embedding vector from a Creator DNA dict.

    The DNA is first serialized into a descriptive text paragraph, then
    embedded using ``text-embedding-3-small`` with ``dimensions=768``.

    If *creator_id* is provided, the embedding is also upserted into the
    ``creator_dna`` ChromaDB collection for later similarity search.

    Parameters
    ----------
    dna:
        A dictionary representation of the Creator DNA (typically from
        ``CreatorDNA.model_dump()``).
    creator_id:
        Optional unique identifier for the creator.  When set, the vector
        is persisted in ChromaDB.

    Returns
    -------
    list[float]
        A 768-dimensional embedding vector.
    """
    text = _dna_to_text(dna)

    logger.info(
        "creator_dna.embeddings.generate",
        text_length=len(text),
        creator_id=creator_id,
    )

    embedding = await generate_embedding(
        text,
        dimensions=_TARGET_DIMENSIONS,
    )

    if creator_id:
        await _store_embedding(
            creator_id=creator_id,
            embedding=embedding,
            dna=dna,
        )

    return embedding


async def _store_embedding(
    creator_id: str,
    embedding: list[float],
    dna: dict[str, Any],
) -> None:
    """Upsert a DNA embedding into ChromaDB.

    Stored metadata includes a JSON-serialized snapshot of the DNA for
    retrieval without needing to re-query the database.
    """
    try:
        collection = _get_chroma_collection()

        # ChromaDB metadata values must be str, int, float, or bool.
        metadata = {
            "creator_id": creator_id,
            "confidence_score": dna.get("confidence_score", 0.0),
            "videos_analyzed": dna.get("videos_analyzed", 0),
            "humor_style": str(dna.get("humor_style", "")),
            "hook_style": str(dna.get("hook_style", "")),
            "pacing_pattern": str(dna.get("pacing_pattern", "")),
            "dna_snapshot": json.dumps(dna, default=str),
        }

        collection.upsert(
            ids=[creator_id],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[_dna_to_text(dna)],
        )

        logger.info(
            "creator_dna.embeddings.stored",
            creator_id=creator_id,
            collection=_COLLECTION_NAME,
        )
    except Exception as exc:
        logger.error(
            "creator_dna.embeddings.store_error",
            creator_id=creator_id,
            error=str(exc),
        )
        raise
