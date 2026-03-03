"""TypedDict state classes for all LangGraph agents.

Each state class defines the exact shape of the data that flows through
the corresponding agent's graph nodes.  They are intentionally plain
``TypedDict`` subclasses (not Pydantic models) so that LangGraph can
merge and checkpoint them efficiently.
"""

from typing import Any, Optional, TypedDict


# ------------------------------------------------------------------
# 1. Trend Scout
# ------------------------------------------------------------------

class TrendScoutState(TypedDict, total=False):
    """State carried through the Trend Scout agent graph.

    The Trend Scout monitors Google Trends, Reddit, YouTube trending,
    and news sources, then scores and clusters the results.
    """

    # Inputs
    user_id: str
    niche: str
    topics: list[str]
    subreddits: list[str]
    creator_dna: dict[str, Any]

    # Intermediate
    raw_google_trends: list[dict[str, Any]]
    raw_reddit_posts: list[dict[str, Any]]
    raw_youtube_trending: list[dict[str, Any]]
    raw_news_articles: list[dict[str, Any]]

    # Scored & clustered
    scored_trends: list[dict[str, Any]]
    trend_clusters: list[dict[str, Any]]

    # Output
    recommendations: list[dict[str, Any]]
    status: str
    error: Optional[str]


# ------------------------------------------------------------------
# 2. Idea Generator
# ------------------------------------------------------------------

class IdeaGeneratorState(TypedDict, total=False):
    """State for the Idea Generator agent.

    Takes scored trends and the creator's DNA to produce ranked content
    ideas with hooks, angles, and differentiation notes.
    """

    # Inputs
    user_id: str
    niche: str
    creator_dna: dict[str, Any]
    scored_trends: list[dict[str, Any]]
    content_history: list[dict[str, Any]]
    knowledge_graph_context: dict[str, Any]

    # Intermediate
    raw_ideas: list[dict[str, Any]]
    gap_analysis: dict[str, Any]
    competitor_ideas: list[dict[str, Any]]

    # Output
    ranked_ideas: list[dict[str, Any]]
    selected_idea: Optional[dict[str, Any]]
    status: str
    error: Optional[str]


# ------------------------------------------------------------------
# 3. Script Architect
# ------------------------------------------------------------------

class ScriptArchitectState(TypedDict, total=False):
    """State for the Script Architect agent.

    Generates full scripts or structured outlines from an approved idea,
    honouring the creator's tone, pacing, and format preferences.
    """

    # Inputs
    user_id: str
    idea: dict[str, Any]
    creator_dna: dict[str, Any]
    content_type: str
    reference_scripts: list[dict[str, Any]]

    # Intermediate
    outline: dict[str, Any]
    draft_script: str
    hook_variants: list[str]
    cta_variants: list[str]

    # Output
    final_script: str
    script_metadata: dict[str, Any]
    variants: list[dict[str, Any]]
    status: str
    error: Optional[str]


# ------------------------------------------------------------------
# 4. SEO Optimizer
# ------------------------------------------------------------------

class SEOOptimizerState(TypedDict, total=False):
    """State for the SEO Optimizer agent.

    Produces platform-specific SEO metadata (titles, descriptions, tags,
    thumbnail concepts, chapters) for a content piece.
    """

    # Inputs
    user_id: str
    content_id: str
    content_type: str
    title: str
    body: str
    target_keywords: list[str]

    # Intermediate
    keyword_research: dict[str, Any]
    competitor_seo: list[dict[str, Any]]
    serp_analysis: dict[str, Any]

    # Output
    seo_package: dict[str, Any]
    title_options: list[dict[str, Any]]
    description: str
    tags: list[str]
    hashtags: list[str]
    chapters: list[dict[str, Any]]
    thumbnail_concepts: list[dict[str, Any]]
    search_visibility_score: float
    status: str
    error: Optional[str]


# ------------------------------------------------------------------
# 5. Performance Analyst
# ------------------------------------------------------------------

class PerformanceAnalystState(TypedDict, total=False):
    """State for the Performance Analyst agent.

    Analyses published video metrics, identifies patterns across the
    channel, and generates actionable recommendations.
    """

    # Inputs
    user_id: str
    channel_id: str
    video_ids: list[str]
    access_token: str

    # Intermediate
    channel_analytics: dict[str, Any]
    video_analytics: list[dict[str, Any]]
    retention_curves: list[dict[str, Any]]
    traffic_analysis: dict[str, Any]
    demographic_data: dict[str, Any]

    # Output
    performance_summary: dict[str, Any]
    top_performers: list[dict[str, Any]]
    underperformers: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    growth_forecast: dict[str, Any]
    status: str
    error: Optional[str]


# ------------------------------------------------------------------
# 6. Media Kit
# ------------------------------------------------------------------

class MediaKitState(TypedDict, total=False):
    """State for the Media Kit agent.

    Aggregates channel stats, demographics, and engagement data into
    a brand-ready media kit with pricing suggestions.
    """

    # Inputs
    user_id: str
    channel_id: str
    access_token: str
    include_rate_card: bool
    include_brand_safety: bool
    generate_pdf: bool
    generate_public_page: bool

    # Intermediate
    channel_stats: dict[str, Any]
    demographics: dict[str, Any]
    top_videos: list[dict[str, Any]]
    engagement_metrics: dict[str, Any]
    growth_data: dict[str, Any]

    # Output
    media_kit_data: dict[str, Any]
    rate_card: dict[str, Any]
    brand_safety_score: float
    public_slug: Optional[str]
    pdf_url: Optional[str]
    status: str
    error: Optional[str]


# ------------------------------------------------------------------
# 7. Orchestrator
# ------------------------------------------------------------------

class OrchestratorState(TypedDict, total=False):
    """State for the multi-agent Orchestrator.

    Coordinates the full pipeline: Trend Scout -> Idea Generator ->
    Script Architect -> SEO Optimizer, with optional human-in-the-loop
    approval gates between stages.
    """

    # Pipeline config
    run_id: str
    user_id: str
    pipeline_type: str  # "full_pipeline" | "single_agent" | "custom"
    agents_to_run: list[str]
    human_gates: dict[str, bool]

    # Creator context
    niche: str
    topics: list[str]
    creator_dna: dict[str, Any]
    channel_id: str
    access_token: str

    # Agent outputs (populated as each agent completes)
    trend_scout_output: Optional[dict[str, Any]]
    idea_generator_output: Optional[dict[str, Any]]
    script_architect_output: Optional[dict[str, Any]]
    seo_optimizer_output: Optional[dict[str, Any]]
    performance_analyst_output: Optional[dict[str, Any]]
    media_kit_output: Optional[dict[str, Any]]

    # Gate state
    current_agent: Optional[str]
    completed_agents: list[str]
    pending_agents: list[str]
    waiting_gate: Optional[str]
    gate_approval: Optional[dict[str, Any]]

    # Overall
    status: str  # "running" | "waiting_gate" | "completed" | "error"
    error: Optional[str]
    started_at: str
    updated_at: str
