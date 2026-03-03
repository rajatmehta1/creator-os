"""Prompt templates for Creator OS agents.

Re-exports shared template utilities and all agent-specific prompt constants
for convenient access.
"""

from app.core.prompts.idea_generator import (
    BRAINSTORM_EVERGREEN_PROMPT,
    BRAINSTORM_TREND_IDEAS_PROMPT,
    CROSS_POLLINATE_PROMPT,
    SCORE_IDEAS_PROMPT,
)
from app.core.prompts.script_architect import (
    DRAFT_SCRIPT_PROMPT,
    GENERATE_VARIANTS_PROMPT,
    INJECT_HOOKS_PROMPT,
    OUTLINE_PROMPT,
    RESEARCH_PROMPT,
    TONE_CHECK_PROMPT,
)
from app.core.prompts.seo_optimizer import (
    BLOG_SEO_PROMPT,
    EXTRACT_KEYWORDS_PROMPT,
    GENERATE_DESCRIPTION_PROMPT,
    GENERATE_TAGS_PROMPT,
    GENERATE_TITLES_PROMPT,
    THUMBNAIL_CONCEPTS_PROMPT,
)
from app.core.prompts.templates import (
    DNA_CONDITIONING_TEMPLATE,
    SYSTEM_BASE_TEMPLATE,
    format_dna_prompt,
    format_system_prompt,
)
from app.core.prompts.trend_scout import (
    CLUSTER_TRENDS_PROMPT,
    GENERATE_RECOMMENDATIONS_PROMPT,
    SCORE_RELEVANCE_PROMPT,
)

__all__ = [
    # Shared templates
    "DNA_CONDITIONING_TEMPLATE",
    "SYSTEM_BASE_TEMPLATE",
    "format_dna_prompt",
    "format_system_prompt",
    # Trend Scout
    "SCORE_RELEVANCE_PROMPT",
    "CLUSTER_TRENDS_PROMPT",
    "GENERATE_RECOMMENDATIONS_PROMPT",
    # Idea Generator
    "BRAINSTORM_TREND_IDEAS_PROMPT",
    "BRAINSTORM_EVERGREEN_PROMPT",
    "CROSS_POLLINATE_PROMPT",
    "SCORE_IDEAS_PROMPT",
    # Script Architect
    "RESEARCH_PROMPT",
    "OUTLINE_PROMPT",
    "DRAFT_SCRIPT_PROMPT",
    "INJECT_HOOKS_PROMPT",
    "TONE_CHECK_PROMPT",
    "GENERATE_VARIANTS_PROMPT",
    # SEO Optimizer
    "EXTRACT_KEYWORDS_PROMPT",
    "GENERATE_TITLES_PROMPT",
    "GENERATE_DESCRIPTION_PROMPT",
    "GENERATE_TAGS_PROMPT",
    "THUMBNAIL_CONCEPTS_PROMPT",
    "BLOG_SEO_PROMPT",
]
