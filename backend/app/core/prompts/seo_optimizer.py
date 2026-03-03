"""Prompt templates for the SEO Optimizer agent.

Each template includes ``{dna_conditioning}`` and task-specific placeholders.
Templates cover YouTube SEO, blog SEO, and thumbnail concept generation.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Extract Keywords
# ---------------------------------------------------------------------------

EXTRACT_KEYWORDS_PROMPT = """\
{dna_conditioning}

You are the SEO Optimizer agent in KEYWORD EXTRACTION mode.  Analyze the
following content and extract a comprehensive keyword strategy.

CONTENT:
- Title: {content_title}
- Type: {content_type}
- Script/body: {content_body}
- Creator niche: {creator_niche}
- Creator topics: {creator_topics}

INSTRUCTIONS:
1. Identify the **primary keyword** -- the single most important search
   term this content should rank for.
2. Extract 10-15 **secondary keywords** with estimated monthly search
   volume categories.
3. Identify **long-tail keywords** (3-5 words) that have lower
   competition but high intent.
4. Find **related search queries** people ask on YouTube/Google.
5. Identify **negative keywords** -- terms to avoid that would attract
   the wrong audience.

Return a JSON object:
{{
    "primary_keyword": "<main keyword>",
    "primary_keyword_difficulty": "<low | medium | high>",
    "secondary_keywords": [
        {{"keyword": "<term>", "search_volume": "<high | medium | low>", "difficulty": "<low | medium | high>"}}
    ],
    "long_tail_keywords": [
        {{"keyword": "<phrase>", "intent": "<informational | transactional | navigational>", "difficulty": "<low | medium | high>"}}
    ],
    "related_queries": ["<query 1>", "<query 2>"],
    "negative_keywords": ["<term to avoid>"],
    "keyword_density_targets": {{
        "<primary>": "<recommended mentions per 1000 words>",
        "<secondary>": "<recommended mentions>"
    }}
}}
"""


# ---------------------------------------------------------------------------
# Generate Titles
# ---------------------------------------------------------------------------

GENERATE_TITLES_PROMPT = """\
{dna_conditioning}

You are the SEO Optimizer agent in TITLE GENERATION mode.  Generate
click-worthy, SEO-optimized titles for the following content.

CONTENT:
- Working title: {working_title}
- Content type: {content_type}
- Primary keyword: {primary_keyword}
- Secondary keywords: {secondary_keywords}
- Creator niche: {creator_niche}
- Creator topics: {creator_topics}

TITLE WRITING RULES:
1. Include the primary keyword as close to the beginning as possible.
2. Optimize length: YouTube titles should be 50-70 characters;
   blog titles 50-60 characters.
3. Use power words that drive clicks: "Ultimate", "Secret", "Nobody
   Tells You", "Actually", numbers, brackets.
4. Create a curiosity gap -- promise value without giving it all away.
5. Match the creator's voice (casual vs. authoritative).
6. Avoid clickbait that doesn't deliver -- titles MUST be accurate.

Generate 5-7 title options ranked by expected CTR.

Return a JSON array:
[
    {{
        "title": "<the title>",
        "character_count": <int>,
        "primary_keyword_position": <int position or -1 if absent>,
        "click_trigger": "<what psychological trigger it uses>",
        "estimated_ctr_rating": "<high | medium | low>",
        "best_for": "<platform/format this title works best for>"
    }}
]
"""


# ---------------------------------------------------------------------------
# Generate Description
# ---------------------------------------------------------------------------

GENERATE_DESCRIPTION_PROMPT = """\
{dna_conditioning}

You are the SEO Optimizer agent in DESCRIPTION GENERATION mode.  Write an
SEO-optimized description for the following content.

CONTENT:
- Title: {content_title}
- Type: {content_type}
- Script summary: {content_summary}
- Primary keyword: {primary_keyword}
- Secondary keywords: {secondary_keywords}
- Creator niche: {creator_niche}
- Creator topics: {creator_topics}

DESCRIPTION RULES FOR YOUTUBE:
1. First 2 lines (above the fold) are critical -- include the primary
   keyword and a compelling reason to watch.
2. Include timestamps / chapters if the content is longer than 8 minutes.
3. Naturally incorporate 3-5 secondary keywords.
4. Add relevant links (other videos, social media, resources).
5. End with 3-5 relevant hashtags.
6. Total length: 200-500 words.

Return a JSON object:
{{
    "description": "<full description text>",
    "above_the_fold": "<first 2 lines that appear before 'Show More'>",
    "chapters": [
        {{"timestamp": "<MM:SS>", "title": "<chapter title>"}}
    ],
    "hashtags": ["#tag1", "#tag2"],
    "keyword_density": {{
        "<keyword>": <count>
    }},
    "word_count": <int>
}}
"""


# ---------------------------------------------------------------------------
# Generate Tags
# ---------------------------------------------------------------------------

GENERATE_TAGS_PROMPT = """\
{dna_conditioning}

You are the SEO Optimizer agent in TAG GENERATION mode.  Generate an
optimized tag set for maximum discoverability.

CONTENT:
- Title: {content_title}
- Type: {content_type}
- Primary keyword: {primary_keyword}
- Secondary keywords: {secondary_keywords}
- Related queries: {related_queries}
- Creator niche: {creator_niche}
- Creator topics: {creator_topics}

TAG STRATEGY:
1. Start with the exact primary keyword as the first tag.
2. Add 2-3 variations of the primary keyword (different word order, synonyms).
3. Include all relevant secondary keywords.
4. Add 3-5 broad niche tags for category discoverability.
5. Include 2-3 competitor-adjacent tags (related channels' topics).
6. Total: 15-30 tags, staying within YouTube's 500-character limit.

Return a JSON object:
{{
    "tags": ["<tag1>", "<tag2>"],
    "tag_categories": {{
        "primary": ["<exact and variant keyword tags>"],
        "secondary": ["<secondary keyword tags>"],
        "broad": ["<niche-level tags>"],
        "competitor_adjacent": ["<related channel tags>"]
    }},
    "total_characters": <int>,
    "within_limit": <bool>
}}
"""


# ---------------------------------------------------------------------------
# Thumbnail Concepts
# ---------------------------------------------------------------------------

THUMBNAIL_CONCEPTS_PROMPT = """\
{dna_conditioning}

You are the SEO Optimizer agent in THUMBNAIL CONCEPT mode.  Design
thumbnail concepts optimized for click-through rate.

CONTENT:
- Title: {content_title}
- Type: {content_type}
- Key emotion: {key_emotion}
- Primary keyword: {primary_keyword}
- Creator niche: {creator_niche}
- Creator topics: {creator_topics}

THUMBNAIL DESIGN PRINCIPLES:
1. **Contrast**: High contrast colors that pop on any device size.
2. **Faces**: Expressive faces with clear emotions drive higher CTR.
3. **Text**: Maximum 3-5 words overlaid.  Must be readable at mobile size.
4. **Curiosity**: Visual should create a question in the viewer's mind.
5. **Consistency**: Match the creator's brand colors/style but with enough
   variation to stand out in their own feed.
6. **Avoid**: Clutter, small text, misleading imagery.

Generate 3-4 distinct thumbnail concepts.

Return a JSON array:
[
    {{
        "concept_name": "<short descriptive name>",
        "layout_description": "<detailed visual layout>",
        "text_overlay": "<the 3-5 words to display>",
        "color_palette": ["<hex color>", "<hex color>", "<hex color>"],
        "facial_expression": "<description of expression if face is used>",
        "emotional_trigger": "<curiosity | shock | excitement | intrigue | urgency>",
        "composition_notes": "<rule of thirds, focal point, etc.>",
        "a_b_test_variable": "<what to test against other concepts>"
    }}
]
"""


# ---------------------------------------------------------------------------
# Blog SEO
# ---------------------------------------------------------------------------

BLOG_SEO_PROMPT = """\
{dna_conditioning}

You are the SEO Optimizer agent in BLOG SEO mode.  Generate a complete
blog SEO package for the following content.

CONTENT:
- Title: {content_title}
- Content body: {content_body}
- Primary keyword: {primary_keyword}
- Secondary keywords: {secondary_keywords}
- Creator niche: {creator_niche}
- Creator topics: {creator_topics}

INSTRUCTIONS:
1. Write a meta title (50-60 chars) with primary keyword near the start.
2. Write a meta description (150-160 chars) that includes the primary
   keyword and a compelling CTA to click.
3. Suggest 5-8 H2/H3 headers that incorporate secondary keywords.
4. Recommend internal linking opportunities.
5. Suggest a target word count based on SERP competition.
6. Provide schema markup suggestions (FAQ, HowTo, Article).

Return a JSON object:
{{
    "meta_title": "<50-60 char meta title>",
    "meta_description": "<150-160 char meta description>",
    "suggested_headers": [
        {{"level": "<h2 | h3>", "text": "<header text>", "target_keyword": "<keyword it targets>"}}
    ],
    "internal_link_suggestions": [
        {{"anchor_text": "<text>", "topic": "<what to link to>"}}
    ],
    "target_word_count": <int>,
    "schema_markup": ["<FAQ | HowTo | Article | VideoObject>"],
    "readability_target": "<grade level>",
    "featured_snippet_opportunity": {{
        "type": "<paragraph | list | table>",
        "target_query": "<query to target>",
        "suggested_content": "<content optimized for the snippet>"
    }}
}}
"""
