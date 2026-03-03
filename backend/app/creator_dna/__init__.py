"""Creator DNA module -- voice fingerprinting and style transfer for Creator OS.

This package analyzes a creator's transcripts to build a unique voice
fingerprint (the "Creator DNA") and provides tools to inject that voice
profile into agent prompts for consistent, authentic content generation.

* ``analyzer`` -- Analyze individual transcripts via LLM.
* ``fingerprint`` -- Aggregate analyses into a CreatorDNA model.
* ``embeddings`` -- Generate and store DNA embedding vectors in ChromaDB.
* ``style_transfer`` -- Build DNA conditioning blocks for agent prompts.
"""

from app.creator_dna.analyzer import analyze_transcript
from app.creator_dna.embeddings import generate_dna_embedding
from app.creator_dna.fingerprint import CreatorDNA, build_fingerprint
from app.creator_dna.style_transfer import build_dna_prompt

__all__ = [
    "analyze_transcript",
    "build_fingerprint",
    "generate_dna_embedding",
    "build_dna_prompt",
    "CreatorDNA",
]
