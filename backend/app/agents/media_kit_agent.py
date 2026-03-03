"""Media Kit Generator Agent — auto-generates professional media kits.

Compiles channel data, audience demographics, growth metrics, and brand safety
analysis into a professional media kit document.
"""

from typing import Any

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.agents.state import MediaKitState
from app.core.llm import get_llm, invoke_with_retry

logger = structlog.get_logger()


# --- Node Functions ---


async def pull_channel_data(state: MediaKitState) -> dict[str, Any]:
    """Fetch channel stats — subscribers, total views, video count."""
    logger.info("media_kit.pull_channel_data")
    # In production, this calls YouTubeClient.get_channel_info or
    # pulls from pre-loaded state
    channel_stats = state.get("channel_stats", {})
    return {"channel_stats": channel_stats}


async def pull_audience_data(state: MediaKitState) -> dict[str, Any]:
    """Fetch audience demographics — age, gender, geography."""
    logger.info("media_kit.pull_audience_data")
    demographics = state.get("demographics", {})
    return {"demographics": demographics}


async def calculate_growth(state: MediaKitState) -> dict[str, Any]:
    """Compute 30/60/90 day growth trajectories."""
    logger.info("media_kit.calculate_growth")
    channel = state.get("channel_stats", {})
    subscriber_count = channel.get("subscriber_count", 0)

    # In production, this would pull historical data and compute actual growth
    # For now, use placeholder growth rates
    growth = {
        "growth_30d": state.get("growth_30d", 0.0),
        "growth_60d": state.get("growth_60d", 0.0),
        "growth_90d": state.get("growth_90d", 0.0),
        "subscriber_count": subscriber_count,
        "trajectory": "growing" if state.get("growth_30d", 0) > 0 else "stable",
    }
    return {"growth_metrics": growth}


async def analyze_brand_safety(state: MediaKitState) -> dict[str, Any]:
    """Score content for brand-friendliness using LLM."""
    logger.info("media_kit.analyze_brand_safety")
    channel = state.get("channel_stats", {})
    top_videos = state.get("top_videos", [])

    if not top_videos:
        return {"brand_safety_score": 75.0, "brand_safety_analysis": "Insufficient data for analysis"}

    llm = get_llm(temperature=0.2)
    video_titles = [v.get("title", "") for v in top_videos[:20]]

    prompt = f"""Analyze these YouTube video titles for brand safety and sponsorship suitability.

Channel: {channel.get('title', 'Unknown')}
Category: {channel.get('category', 'Unknown')}
Recent Video Titles:
{chr(10).join(f'- {t}' for t in video_titles)}

Score the channel's brand safety from 0-100 based on:
- Family friendliness
- Professional tone
- Absence of controversial/divisive topics
- Advertiser suitability

Return JSON:
{{"score": 85, "analysis": "Brief explanation", "strengths": ["...", "..."], "concerns": ["...", "..."]}}"""

    response = await invoke_with_retry(
        llm,
        [SystemMessage(content="You are a brand safety analyst. Return valid JSON only."),
         HumanMessage(content=prompt)],
    )

    import json
    try:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(content)
        return {
            "brand_safety_score": result.get("score", 75),
            "brand_safety_analysis": result.get("analysis", ""),
        }
    except (json.JSONDecodeError, IndexError):
        return {"brand_safety_score": 75.0, "brand_safety_analysis": "Analysis pending"}


async def compute_rate_card(state: MediaKitState) -> dict[str, Any]:
    """Suggest CPM/flat-rate pricing based on metrics."""
    logger.info("media_kit.compute_rate_card")
    channel = state.get("channel_stats", {})
    sub_count = channel.get("subscriber_count", 0)
    avg_views = channel.get("avg_views_per_video", 0)

    # CPM tiers based on subscriber count and engagement
    if sub_count >= 1_000_000:
        base_cpm = 25.0
    elif sub_count >= 500_000:
        base_cpm = 20.0
    elif sub_count >= 100_000:
        base_cpm = 15.0
    elif sub_count >= 50_000:
        base_cpm = 12.0
    elif sub_count >= 10_000:
        base_cpm = 8.0
    else:
        base_cpm = 5.0

    estimated_flat_rate = avg_views * base_cpm / 1000 if avg_views > 0 else 0

    rate_card = {
        "suggested_cpm": base_cpm,
        "suggested_flat_rate": round(estimated_flat_rate),
        "formats": {
            "dedicated_video": round(estimated_flat_rate * 1.5),
            "integrated_mention": round(estimated_flat_rate * 0.6),
            "shorts_mention": round(estimated_flat_rate * 0.3),
            "community_post": round(estimated_flat_rate * 0.1),
        },
        "notes": "Rates are estimates based on channel metrics. Actual rates may vary.",
    }
    return {"rate_card": rate_card}


async def generate_media_kit(state: MediaKitState) -> dict[str, Any]:
    """Compile everything into a structured media kit."""
    logger.info("media_kit.generate")

    media_kit = {
        "channel_stats": state.get("channel_stats", {}),
        "demographics": state.get("demographics", {}),
        "growth_metrics": state.get("growth_metrics", {}),
        "top_videos": state.get("top_videos", [])[:10],
        "brand_safety": {
            "score": state.get("brand_safety_score", 0),
            "analysis": state.get("brand_safety_analysis", ""),
        },
        "rate_card": state.get("rate_card", {}),
        "collaboration_formats": [
            {"name": "Dedicated Video", "description": "Full video sponsored by brand"},
            {"name": "Integrated Mention", "description": "60-90 second brand integration"},
            {"name": "Product Review", "description": "In-depth product review/demo"},
            {"name": "Shorts Series", "description": "3-5 branded short-form videos"},
            {"name": "Community Post", "description": "Branded community post"},
        ],
    }
    return {"media_kit": media_kit}


async def render_outputs(state: MediaKitState) -> dict[str, Any]:
    """Generate final outputs (PDF + web page references)."""
    logger.info("media_kit.render")
    # In production, this would generate PDF and hosted page
    return {
        "pdf_url": None,  # Generated in production
        "public_slug": state.get("public_slug"),
        "render_complete": True,
    }


# --- Graph Construction ---


def create_media_kit_graph() -> StateGraph:
    """Create the Media Kit Generator LangGraph."""
    graph = StateGraph(MediaKitState)

    # Add nodes
    graph.add_node("pull_channel_data", pull_channel_data)
    graph.add_node("pull_audience_data", pull_audience_data)
    graph.add_node("calculate_growth", calculate_growth)
    graph.add_node("analyze_brand_safety", analyze_brand_safety)
    graph.add_node("compute_rate_card", compute_rate_card)
    graph.add_node("generate_media_kit", generate_media_kit)
    graph.add_node("render_outputs", render_outputs)

    # Edges: parallel(channel, audience) -> parallel(growth, brand) -> rate_card -> generate -> render
    graph.add_edge(START, "pull_channel_data")
    graph.add_edge(START, "pull_audience_data")
    graph.add_edge("pull_channel_data", "calculate_growth")
    graph.add_edge("pull_channel_data", "analyze_brand_safety")
    graph.add_edge("pull_audience_data", "calculate_growth")
    graph.add_edge("calculate_growth", "compute_rate_card")
    graph.add_edge("analyze_brand_safety", "compute_rate_card")
    graph.add_edge("compute_rate_card", "generate_media_kit")
    graph.add_edge("generate_media_kit", "render_outputs")
    graph.add_edge("render_outputs", END)

    return graph.compile()


async def run_media_kit_generator(
    channel_stats: dict,
    demographics: dict | None = None,
    top_videos: list[dict] | None = None,
    growth_30d: float = 0.0,
    growth_60d: float = 0.0,
    growth_90d: float = 0.0,
) -> dict[str, Any]:
    """Run the Media Kit Generator agent pipeline."""
    logger.info("media_kit.run")

    graph = create_media_kit_graph()
    initial_state: MediaKitState = {
        "channel_stats": channel_stats,
        "demographics": demographics or {},
        "top_videos": top_videos or [],
        "growth_30d": growth_30d,
        "growth_60d": growth_60d,
        "growth_90d": growth_90d,
    }

    result = await graph.ainvoke(initial_state)
    logger.info("media_kit.complete")
    return result
