"""Prompt templates for the Idea Generator agent.

Each template includes ``{creator_niche}``, ``{creator_topics}``, and
``{dna_conditioning}`` placeholder variables, plus task-specific inputs.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Brainstorm trend-based ideas
# ---------------------------------------------------------------------------

BRAINSTORM_TREND_IDEAS_PROMPT = """\
{dna_conditioning}

You are the Idea Generator agent.  Brainstorm content ideas inspired by
the provided trend recommendations.

CREATOR CONTEXT
- Niche: {creator_niche}
- Core topics: {creator_topics}
- Past top-performing content themes: {top_performing_themes}

TREND RECOMMENDATIONS (JSON):
{trend_recommendations}

INSTRUCTIONS:
1. For EACH trend, generate {ideas_per_trend} distinct content ideas that
   leverage the creator's unique angle.
2. Each idea must have a compelling hook -- the first sentence a viewer sees or
   hears -- written in the creator's voice.
3. Vary content types across ideas (YouTube long-form, Shorts, blog post,
   Twitter thread, newsletter).
4. Push beyond the obvious -- find surprising connections between the trend
   and the creator's expertise.
5. Include a difficulty estimate so the creator can plan their workload.

For each idea return a JSON object:
{{
    "idea_title": "<catchy, specific title>",
    "hook": "<opening hook in the creator's voice, max 2 sentences>",
    "angle": "<what makes this take unique>",
    "content_type": "<primary content type>",
    "secondary_types": ["<repurposing options>"],
    "trend_connection": "<which trend this stems from>",
    "estimated_performance": "<viral | high | medium | niche>",
    "target_audience_segment": "<specific audience segment>",
    "key_points": ["<point 1>", "<point 2>", "<point 3>"],
    "differentiation": "<how this differs from existing content on the topic>",
    "difficulty": "<easy | medium | hard | expert>",
    "suggested_publish_window": "<optimal timing window>"
}}

Return a JSON array of all ideas.
"""


# ---------------------------------------------------------------------------
# Brainstorm evergreen ideas
# ---------------------------------------------------------------------------

BRAINSTORM_EVERGREEN_PROMPT = """\
{dna_conditioning}

You are the Idea Generator agent.  Create evergreen content ideas that will
perform well regardless of current trends.

CREATOR CONTEXT
- Niche: {creator_niche}
- Core topics: {creator_topics}
- Audience pain points: {audience_pain_points}
- Existing content gaps: {content_gaps}

INSTRUCTIONS:
1. Generate {idea_count} evergreen content ideas rooted in the creator's
   core expertise.
2. Focus on searchable, high-intent topics that will attract new viewers
   over months or years.
3. Consider "pillar content" that can anchor a broader content strategy.
4. Each idea should solve a specific audience problem or answer a frequently
   asked question.
5. Write hooks in the creator's authentic voice.

For each idea return a JSON object:
{{
    "idea_title": "<SEO-friendly, specific title>",
    "hook": "<opening hook in the creator's voice>",
    "angle": "<what makes this take definitive or unique>",
    "content_type": "<primary content type>",
    "secondary_types": ["<repurposing options>"],
    "trend_connection": null,
    "estimated_performance": "<steady | high_search | foundational>",
    "target_audience_segment": "<specific audience segment>",
    "key_points": ["<point 1>", "<point 2>", "<point 3>"],
    "differentiation": "<how this differs from the top existing content>",
    "difficulty": "<easy | medium | hard | expert>",
    "suggested_publish_window": "<anytime | seasonal note>"
}}

Return a JSON array of {idea_count} ideas.
"""


# ---------------------------------------------------------------------------
# Cross-pollinate ideas (combine unrelated topics)
# ---------------------------------------------------------------------------

CROSS_POLLINATE_PROMPT = """\
{dna_conditioning}

You are the Idea Generator agent performing creative cross-pollination.
Combine seemingly unrelated topics or trends to produce novel content ideas
that only THIS creator could make.

CREATOR CONTEXT
- Niche: {creator_niche}
- Core topics: {creator_topics}

INPUT TOPICS / TRENDS TO COMBINE:
Topic A: {topic_a}
Topic B: {topic_b}
Additional context: {additional_context}

INSTRUCTIONS:
1. Find surprising, non-obvious connections between Topic A and Topic B.
2. Generate {idea_count} cross-pollinated ideas that would feel natural
   for this creator.
3. Each idea should make the viewer think "I never thought about it that
   way" -- that's the viral trigger.
4. Rate the novelty of each connection.

For each idea return a JSON object:
{{
    "idea_title": "<title that highlights the unexpected connection>",
    "hook": "<hook that creates curiosity about the mashup>",
    "angle": "<the surprising connection explained>",
    "content_type": "<primary content type>",
    "secondary_types": ["<repurposing options>"],
    "trend_connection": "<if applicable>",
    "estimated_performance": "<viral | high | medium | niche>",
    "target_audience_segment": "<who would be most intrigued>",
    "key_points": ["<key insight 1>", "<key insight 2>", "<key insight 3>"],
    "differentiation": "<why no one else is making this connection>",
    "difficulty": "<easy | medium | hard | expert>",
    "suggested_publish_window": "<timing recommendation>",
    "novelty_score": <float 0-10>
}}

Return a JSON array of {idea_count} ideas.
"""


# ---------------------------------------------------------------------------
# Score and rank ideas
# ---------------------------------------------------------------------------

SCORE_IDEAS_PROMPT = """\
{dna_conditioning}

You are the Idea Generator agent.  Score and rank the following content ideas
to help the creator prioritize their content calendar.

CREATOR CONTEXT
- Niche: {creator_niche}
- Core topics: {creator_topics}
- Channel size/stage: {channel_stage}
- Weekly production capacity: {production_capacity}

IDEAS TO SCORE (JSON):
{ideas}

SCORING DIMENSIONS (0-10 each):
1. **Virality Potential**: Could this break out of the creator's existing
   audience?
2. **Audience Value**: How much value does this provide to existing
   subscribers?
3. **Search Potential**: Will this rank in YouTube/Google search over time?
4. **Brand Alignment**: Does this reinforce the creator's brand positioning?
5. **Production Feasibility**: Can the creator realistically produce this
   given their resources?
6. **Revenue Potential**: Could this drive sponsorships, affiliates, or
   product sales?

INSTRUCTIONS:
1. Score each idea on all 6 dimensions.
2. Compute a weighted composite score (virality 0.20, audience_value 0.20,
   search 0.15, brand 0.15, feasibility 0.15, revenue 0.15).
3. Return ideas sorted by composite score descending.
4. Add a ``priority`` label: "must_make", "should_make", "nice_to_have", or
   "backlog".

For each scored idea return:
{{
    "idea_title": "<original title>",
    "scores": {{
        "virality": <float>,
        "audience_value": <float>,
        "search_potential": <float>,
        "brand_alignment": <float>,
        "production_feasibility": <float>,
        "revenue_potential": <float>
    }},
    "composite_score": <float 0-10>,
    "priority": "<must_make | should_make | nice_to_have | backlog>",
    "reasoning": "<brief justification>"
}}

Return a JSON array sorted by composite_score descending.
"""
