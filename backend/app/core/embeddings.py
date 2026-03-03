"""Embedding generation using OpenAI text-embedding-3-small.

Provides thin async wrappers around the OpenAI embeddings API with batching,
retry logic, and input validation.
"""

from __future__ import annotations

from typing import Sequence

import structlog
from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings

logger = structlog.get_logger(__name__)

# OpenAI embedding API accepts at most 2048 items per request.
_MAX_BATCH_SIZE = 2048

# text-embedding-3-small produces 1536-dim vectors by default.
# We can request fewer dimensions for efficiency.
_DEFAULT_DIMENSIONS: int | None = None  # None = use model default (1536)


def _get_client() -> AsyncOpenAI:
    """Return a configured async OpenAI client."""
    settings = get_settings()
    return AsyncOpenAI(api_key=settings.openai_api_key)


@retry(
    retry=retry_if_exception_type((Exception,)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
    before_sleep=lambda rs: logger.warning(
        "embeddings.retry",
        attempt=rs.attempt_number,
        error=str(rs.outcome.exception()) if rs.outcome else None,
    ),
)
async def generate_embedding(
    text: str,
    *,
    model: str | None = None,
    dimensions: int | None = _DEFAULT_DIMENSIONS,
) -> list[float]:
    """Generate a single embedding vector for *text*.

    Parameters
    ----------
    text:
        The input text to embed. Whitespace is stripped; empty strings raise
        ``ValueError``.
    model:
        Embedding model name. Defaults to ``settings.embedding_model``
        (``text-embedding-3-small``).
    dimensions:
        Optional dimension override (only supported by ``text-embedding-3-*``
        models).

    Returns
    -------
    list[float]
        The embedding vector.
    """
    text = text.strip()
    if not text:
        raise ValueError("Cannot generate embedding for empty text.")

    settings = get_settings()
    model = model or settings.embedding_model
    client = _get_client()

    logger.debug("embeddings.generate", model=model, text_len=len(text))

    kwargs: dict = {"input": text, "model": model}
    if dimensions is not None:
        kwargs["dimensions"] = dimensions

    response = await client.embeddings.create(**kwargs)
    return response.data[0].embedding


@retry(
    retry=retry_if_exception_type((Exception,)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
    before_sleep=lambda rs: logger.warning(
        "embeddings.batch_retry",
        attempt=rs.attempt_number,
        error=str(rs.outcome.exception()) if rs.outcome else None,
    ),
)
async def generate_embeddings_batch(
    texts: Sequence[str],
    *,
    model: str | None = None,
    dimensions: int | None = _DEFAULT_DIMENSIONS,
) -> list[list[float]]:
    """Generate embedding vectors for multiple texts in a single API call.

    Texts are automatically chunked into batches of at most
    ``_MAX_BATCH_SIZE`` items.

    Parameters
    ----------
    texts:
        A sequence of input texts.
    model:
        Embedding model name. Defaults to ``settings.embedding_model``.
    dimensions:
        Optional dimension override.

    Returns
    -------
    list[list[float]]
        A list of embedding vectors, one per input text, in the same order.
    """
    if not texts:
        return []

    cleaned = [t.strip() for t in texts]
    if any(not t for t in cleaned):
        raise ValueError("All texts must be non-empty after stripping whitespace.")

    settings = get_settings()
    model = model or settings.embedding_model
    client = _get_client()

    logger.info(
        "embeddings.generate_batch",
        model=model,
        count=len(cleaned),
    )

    all_embeddings: list[list[float]] = []

    for start in range(0, len(cleaned), _MAX_BATCH_SIZE):
        batch = cleaned[start : start + _MAX_BATCH_SIZE]

        kwargs: dict = {"input": batch, "model": model}
        if dimensions is not None:
            kwargs["dimensions"] = dimensions

        response = await client.embeddings.create(**kwargs)

        # The API may return embeddings out of order; sort by index.
        sorted_data = sorted(response.data, key=lambda d: d.index)
        all_embeddings.extend([d.embedding for d in sorted_data])

    return all_embeddings
