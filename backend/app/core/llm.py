"""Centralized LLM client factory for Creator OS.

Provides a single entry point for obtaining configured LangChain ChatModel
instances with automatic fallback from Anthropic to OpenAI and retry logic.
"""

from __future__ import annotations

from typing import Optional

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_ANTHROPIC_MODELS = frozenset(
    {
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
        "claude-haiku-235-20241022",
    }
)


def _is_anthropic_model(model: str) -> bool:
    """Return True when *model* is an Anthropic model identifier."""
    return model in _ANTHROPIC_MODELS or model.startswith("claude")


def _build_anthropic(
    model: str,
    *,
    streaming: bool,
    temperature: float,
    max_tokens: int,
) -> ChatAnthropic:
    settings = get_settings()
    return ChatAnthropic(
        model=model,
        anthropic_api_key=settings.anthropic_api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=streaming,
        default_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
    )


def _build_openai(
    model: str,
    *,
    streaming: bool,
    temperature: float,
    max_tokens: int,
) -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=model,
        api_key=settings.openai_api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=streaming,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_llm(
    model: Optional[str] = None,
    *,
    streaming: bool = False,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    fallback: bool = True,
) -> BaseChatModel:
    """Return a ready-to-use LangChain ChatModel.

    Parameters
    ----------
    model:
        Model identifier.  Defaults to the value of ``settings.default_llm``
        (``claude-sonnet-4-20250514``).
    streaming:
        Whether the model should yield tokens incrementally.
    temperature:
        Sampling temperature.
    max_tokens:
        Maximum tokens in the completion.
    fallback:
        When *True* and the primary model is Anthropic, attach an OpenAI
        fallback via ``with_fallbacks``.

    Returns
    -------
    BaseChatModel
        A configured LangChain chat model (optionally with fallback).
    """
    settings = get_settings()
    model = model or settings.default_llm

    logger.info(
        "llm.get",
        model=model,
        streaming=streaming,
        temperature=temperature,
        fallback=fallback,
    )

    build_kwargs = dict(
        streaming=streaming,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    if _is_anthropic_model(model):
        primary = _build_anthropic(model, **build_kwargs)
        if fallback and settings.openai_api_key:
            fallback_llm = _build_openai("gpt-4o", **build_kwargs)
            logger.info("llm.fallback_attached", fallback_model="gpt-4o")
            return primary.with_fallbacks([fallback_llm])
        return primary

    # Non-Anthropic model requested (e.g. gpt-4o directly)
    return _build_openai(model, **build_kwargs)


def get_streaming_llm(
    model: Optional[str] = None,
    *,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> BaseChatModel:
    """Convenience wrapper that returns a streaming-enabled model for SSE responses."""
    return get_llm(
        model,
        streaming=True,
        temperature=temperature,
        max_tokens=max_tokens,
    )


# ---------------------------------------------------------------------------
# Retry-wrapped invocation helpers
# ---------------------------------------------------------------------------


@retry(
    retry=retry_if_exception_type((Exception,)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
    before_sleep=lambda retry_state: logger.warning(
        "llm.retry",
        attempt=retry_state.attempt_number,
        error=str(retry_state.outcome.exception()) if retry_state.outcome else None,
    ),
)
async def invoke_with_retry(
    llm: BaseChatModel,
    messages: list,
    **kwargs,
) -> object:
    """Invoke *llm* with automatic retries on transient failures.

    Wraps ``llm.ainvoke`` with tenacity exponential-backoff retry logic
    (up to 3 attempts).
    """
    return await llm.ainvoke(messages, **kwargs)


@retry(
    retry=retry_if_exception_type((Exception,)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
    before_sleep=lambda retry_state: logger.warning(
        "llm.stream_retry",
        attempt=retry_state.attempt_number,
        error=str(retry_state.outcome.exception()) if retry_state.outcome else None,
    ),
)
async def stream_with_retry(
    llm: BaseChatModel,
    messages: list,
    **kwargs,
):
    """Async-stream tokens from *llm* with retry on the initial connection.

    Yields ``AIMessageChunk`` objects as they arrive.
    """
    async for chunk in llm.astream(messages, **kwargs):
        yield chunk


# ---------------------------------------------------------------------------
# Token counting utility
# ---------------------------------------------------------------------------


async def count_tokens(text: str, model: Optional[str] = None) -> int:
    """Return an approximate token count for *text*.

    Uses the model's ``get_num_tokens`` when available (Anthropic / tiktoken),
    otherwise falls back to a simple whitespace heuristic.
    """
    settings = get_settings()
    model = model or settings.default_llm

    try:
        if _is_anthropic_model(model):
            llm = _build_anthropic(
                model, streaming=False, temperature=0.0, max_tokens=1
            )
        else:
            llm = _build_openai(
                model, streaming=False, temperature=0.0, max_tokens=1
            )
        return llm.get_num_tokens(text)
    except Exception as exc:
        logger.warning("llm.count_tokens_fallback", error=str(exc))
        # Rough heuristic: ~4 chars per token for English text
        return max(1, len(text) // 4)
