"""LangChain PydanticOutputParser wrappers for all agent output schemas.

Each parser is a thin wrapper that provides:
* ``get_format_instructions()`` -- returns a string to inject into the prompt
  so the LLM knows the expected JSON structure.
* ``parse(text)`` -- validates the raw LLM output and returns a typed
  Pydantic model instance.

Parsers are exposed both as module-level singletons (for convenience) and as
factory functions (for cases that need a fresh instance).
"""

from __future__ import annotations

import structlog
from langchain_core.output_parsers import PydanticOutputParser

from app.schemas.content import SEOPackage
from app.schemas.idea import ContentIdea
from app.schemas.trend import TrendRecommendation

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Parser classes
# ---------------------------------------------------------------------------


class TrendRecommendationParser(PydanticOutputParser):
    """Parses LLM output into a ``TrendRecommendation`` schema."""

    def __init__(self) -> None:
        super().__init__(pydantic_object=TrendRecommendation)


class ContentIdeaParser(PydanticOutputParser):
    """Parses LLM output into a ``ContentIdea`` schema."""

    def __init__(self) -> None:
        super().__init__(pydantic_object=ContentIdea)


class SEOPackageParser(PydanticOutputParser):
    """Parses LLM output into an ``SEOPackage`` schema."""

    def __init__(self) -> None:
        super().__init__(pydantic_object=SEOPackage)


# ---------------------------------------------------------------------------
# Module-level singleton instances
# ---------------------------------------------------------------------------

trend_recommendation_parser = TrendRecommendationParser()
content_idea_parser = ContentIdeaParser()
seo_package_parser = SEOPackageParser()


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def get_trend_format_instructions() -> str:
    """Return format instructions for the TrendRecommendation schema."""
    return trend_recommendation_parser.get_format_instructions()


def get_idea_format_instructions() -> str:
    """Return format instructions for the ContentIdea schema."""
    return content_idea_parser.get_format_instructions()


def get_seo_format_instructions() -> str:
    """Return format instructions for the SEOPackage schema."""
    return seo_package_parser.get_format_instructions()
