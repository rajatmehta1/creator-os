"""Prompt templates for the Trend Scout agent.

Each template expects ``{creator_niche}``, ``{creator_topics}``, and
``{dna_conditioning}`` as placeholder variables, along with any
task-specific variables noted in their docstrings.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Score Relevance
# ---------------------------------------------------------------------------

SCORE_RELEVANCE_PROMPT = """\
{dna_conditioning}

You are the Trend Scout agent evaluating how relevant a trend is to a specific
creator's niche and audience.

CREATOR CONTEXT
- Niche: {creator_niche}
- Core topics: {creator_topics}

TREND TO EVALUATE
- Title: {trend_title}
- Summary: {trend_summary}
- Source: {trend_source}
- Raw data: {trend_raw_data}

SCORING CRITERIA (weight each 0-10, then compute weighted average):
1. **Niche Alignment** (weight 3): How closely does this trend relate to the
   creator's niche and topics?
2. **Audience Interest** (weight 2.5): Would the creator's existing audience
   care about this?
3. **Timeliness** (weight 2): How time-sensitive is this trend?  Is there a
   first-mover advantage?
4. **Content Potential** (weight 1.5): Can this trend be turned into
   compelling content (video, blog, thread)?
5. **Competition Gap** (weight 1): Is there an underserved angle the creator
   can own?

Return a JSON object with exactly these fields:
{{
    "relevance_score": <float 0-10>,
    "velocity": "<rising | peaking | stable | declining>",
    "competition_level": "<low | medium | high | saturated>",
    "niche_angle": "<specific angle this creator should take>",
    "time_sensitivity": "<act_now | this_week | this_month | evergreen>",
    "reasoning": "<brief explanation of the score>"
}}
"""


# ---------------------------------------------------------------------------
# Cluster Trends
# ---------------------------------------------------------------------------

CLUSTER_TRENDS_PROMPT = """\
{dna_conditioning}

You are the Trend Scout agent.  Group the following scored trends into
semantically related clusters so the creator can see macro-themes at a glance.

CREATOR CONTEXT
- Niche: {creator_niche}
- Core topics: {creator_topics}

SCORED TRENDS (JSON array):
{scored_trends}

INSTRUCTIONS:
1. Identify 3-7 thematic clusters from the trends above.
2. Each cluster should have a descriptive name that resonates with the
   creator's niche.
3. Assign every trend to exactly one cluster.
4. Compute a ``combined_score`` for each cluster (average of member scores,
   boosted if multiple sources converge).

Return a JSON array of cluster objects:
[
    {{
        "cluster_name": "<descriptive cluster name>",
        "trends": [<list of trend objects as provided>],
        "combined_score": <float 0-10>,
        "cluster_reasoning": "<why these trends belong together>"
    }}
]
"""


# ---------------------------------------------------------------------------
# Generate Recommendations
# ---------------------------------------------------------------------------

GENERATE_RECOMMENDATIONS_PROMPT = """\
{dna_conditioning}

You are the Trend Scout agent producing the final set of prioritized trend
recommendations for the creator.

CREATOR CONTEXT
- Niche: {creator_niche}
- Core topics: {creator_topics}

TREND CLUSTERS (JSON):
{trend_clusters}

INSTRUCTIONS:
1. Select the **top {recommendation_count}** most actionable trends across
   all clusters.
2. For each trend, craft a specific content angle that differentiates the
   creator from what's already out there.
3. Suggest 2-3 content types (e.g., YouTube video, blog post, Twitter thread)
   that would work well for each trend.
4. Identify related topics the creator could chain into a content series.

For each recommendation, return a JSON object matching this schema:
{{
    "trend_title": "<concise trend title>",
    "trend_summary": "<2-3 sentence summary>",
    "relevance_score": <float 0-10>,
    "velocity": "<rising | peaking | stable | declining>",
    "sources": [
        {{"source": "<platform>", "url": "<optional url>", "raw_score": <optional float>}}
    ],
    "niche_angle": "<unique angle for THIS creator>",
    "competition_level": "<low | medium | high | saturated>",
    "suggested_content_types": ["<type1>", "<type2>"],
    "related_topics": ["<topic1>", "<topic2>"],
    "time_sensitivity": "<act_now | this_week | this_month | evergreen>"
}}

Return a JSON array of {recommendation_count} recommendation objects.
"""
