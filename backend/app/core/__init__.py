"""Core module for Creator OS -- LLM clients, embeddings, parsers, and prompts.

This package provides the foundational AI infrastructure used by all agents:

* ``llm`` -- Centralized LLM client factory with Anthropic primary / OpenAI fallback.
* ``embeddings`` -- Embedding generation via OpenAI text-embedding-3-small.
* ``output_parsers`` -- Typed PydanticOutputParser wrappers for agent schemas.
* ``prompts`` -- All prompt templates including the DNA conditioning block.
"""

from app.core.embeddings import generate_embedding, generate_embeddings_batch
from app.core.llm import (
    count_tokens,
    get_llm,
    get_streaming_llm,
    invoke_with_retry,
    stream_with_retry,
)
from app.core.output_parsers import (
    ContentIdeaParser,
    SEOPackageParser,
    TrendRecommendationParser,
    content_idea_parser,
    seo_package_parser,
    trend_recommendation_parser,
)

__all__ = [
    # LLM
    "get_llm",
    "get_streaming_llm",
    "invoke_with_retry",
    "stream_with_retry",
    "count_tokens",
    # Embeddings
    "generate_embedding",
    "generate_embeddings_batch",
    # Output parsers
    "TrendRecommendationParser",
    "ContentIdeaParser",
    "SEOPackageParser",
    "trend_recommendation_parser",
    "content_idea_parser",
    "seo_package_parser",
]
