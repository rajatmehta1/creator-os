"""Performance Analyst Agent — analyzes YouTube analytics and generates insights.

Ingests YouTube analytics data, identifies patterns, and generates actionable
insights that feed back into all other agents.
"""

from typing import Any

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.agents.state import PerformanceAnalystState
from app.core.llm import get_llm, invoke_with_retry

logger = structlog.get_logger()


# --- Node Functions ---


async def sync_youtube_data(state: PerformanceAnalystState) -> dict[str, Any]:
    """Pull latest analytics via YouTube Analytics API."""
    logger.info("performance_analyst.sync_youtube_data")
    # In production, this calls YouTubeAnalyticsClient
    # For now, pass through any pre-loaded data
    return {
        "channel_analytics": state.get("channel_analytics", {}),
        "video_analytics": state.get("video_analytics", []),
    }


async def compute_metrics(state: PerformanceAnalystState) -> dict[str, Any]:
    """Calculate derived metrics from raw analytics."""
    logger.info("performance_analyst.compute_metrics")
    videos = state.get("video_analytics", [])

    if not videos:
        return {"performance_summary": {"status": "no_data"}}

    total_views = sum(v.get("views", 0) for v in videos)
    total_watch_hours = sum(v.get("watch_time_hours", 0) for v in videos)
    avg_ctr = sum(v.get("ctr", 0) for v in videos) / len(videos) if videos else 0
    avg_retention = sum(v.get("average_percentage_viewed", 0) for v in videos) / len(videos) if videos else 0
    avg_views = total_views / len(videos) if videos else 0
    total_subs_gained = sum(v.get("subscribers_gained", 0) for v in videos)
    total_subs_lost = sum(v.get("subscribers_lost", 0) for v in videos)

    engagement_rates = []
    for v in videos:
        views = v.get("views", 1)
        engagement = (v.get("likes", 0) + v.get("comments", 0) + v.get("shares", 0)) / views
        engagement_rates.append(engagement)

    avg_engagement = sum(engagement_rates) / len(engagement_rates) if engagement_rates else 0

    return {
        "performance_summary": {
            "total_videos_analyzed": len(videos),
            "total_views": total_views,
            "total_watch_hours": round(total_watch_hours, 1),
            "avg_views_per_video": round(avg_views),
            "avg_ctr": round(avg_ctr, 2),
            "avg_retention": round(avg_retention, 1),
            "avg_engagement_rate": round(avg_engagement, 4),
            "net_subscribers": total_subs_gained - total_subs_lost,
        },
    }


async def detect_patterns(state: PerformanceAnalystState) -> dict[str, Any]:
    """Identify what's working and not working using LLM analysis."""
    logger.info("performance_analyst.detect_patterns")
    videos = state.get("video_analytics", [])
    summary = state.get("performance_summary", {})

    if not videos or summary.get("status") == "no_data":
        return {"patterns": []}

    # Sort videos by views to identify top and underperformers
    sorted_videos = sorted(videos, key=lambda v: v.get("views", 0), reverse=True)
    top_5 = sorted_videos[:5]
    bottom_5 = sorted_videos[-5:] if len(sorted_videos) >= 10 else sorted_videos[len(sorted_videos)//2:]

    llm = get_llm(temperature=0.3)
    prompt = f"""Analyze these YouTube video performance patterns.

Channel Summary:
{summary}

Top Performing Videos:
{_format_videos(top_5)}

Underperforming Videos:
{_format_videos(bottom_5)}

Identify specific, actionable patterns in these categories:
1. TOPICS: Which topics perform best/worst? Any emerging topics?
2. FORMATS: Optimal video length, style, format patterns
3. TIMING: Best publish times/days if detectable
4. ENGAGEMENT: What drives comments, likes, shares?
5. THUMBNAILS/TITLES: Patterns in high-CTR content
6. RETENTION: What keeps viewers watching or causes drop-offs?

Return your analysis as a JSON array of pattern objects:
[{{"category": "topics", "finding": "...", "confidence": 0.8, "impact": "high", "recommendation": "..."}}]"""

    response = await invoke_with_retry(
        llm,
        [SystemMessage(content="You are a YouTube analytics expert. Return valid JSON only."),
         HumanMessage(content=prompt)],
    )

    import json
    try:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        patterns = json.loads(content)
    except (json.JSONDecodeError, IndexError):
        patterns = [{"category": "general", "finding": content, "confidence": 0.5, "impact": "medium", "recommendation": "Review manually"}]

    return {"patterns": patterns}


async def benchmark_performance(state: PerformanceAnalystState) -> dict[str, Any]:
    """Compare against niche averages."""
    logger.info("performance_analyst.benchmark")
    summary = state.get("performance_summary", {})

    # Niche benchmarks (these would come from aggregated data in production)
    benchmarks = {
        "avg_ctr_benchmark": 4.5,
        "avg_retention_benchmark": 50.0,
        "avg_engagement_benchmark": 0.04,
    }

    comparisons = {}
    if summary.get("avg_ctr"):
        ctr_diff = summary["avg_ctr"] - benchmarks["avg_ctr_benchmark"]
        comparisons["ctr"] = {
            "yours": summary["avg_ctr"],
            "benchmark": benchmarks["avg_ctr_benchmark"],
            "diff_pct": round(ctr_diff / benchmarks["avg_ctr_benchmark"] * 100, 1),
            "status": "above" if ctr_diff > 0 else "below",
        }
    if summary.get("avg_retention"):
        ret_diff = summary["avg_retention"] - benchmarks["avg_retention_benchmark"]
        comparisons["retention"] = {
            "yours": summary["avg_retention"],
            "benchmark": benchmarks["avg_retention_benchmark"],
            "diff_pct": round(ret_diff / benchmarks["avg_retention_benchmark"] * 100, 1),
            "status": "above" if ret_diff > 0 else "below",
        }

    return {"benchmarks": comparisons}


async def generate_insights(state: PerformanceAnalystState) -> dict[str, Any]:
    """Synthesize patterns into plain-language insights."""
    logger.info("performance_analyst.generate_insights")
    patterns = state.get("patterns", [])
    benchmarks = state.get("benchmarks", {})
    summary = state.get("performance_summary", {})

    if not patterns and not benchmarks:
        return {"insights": []}

    llm = get_llm(temperature=0.4)
    prompt = f"""Based on these YouTube channel analytics, generate clear, actionable insights.

Performance Summary: {summary}
Patterns Found: {patterns}
Benchmark Comparisons: {benchmarks}

Generate 5-10 insights in this JSON format:
[{{
    "insight": "Plain language insight",
    "category": "content|growth|engagement|seo|monetization",
    "priority": "high|medium|low",
    "action": "Specific action to take",
    "expected_impact": "What improvement to expect"
}}]"""

    response = await invoke_with_retry(
        llm,
        [SystemMessage(content="You are a YouTube growth strategist. Return valid JSON only."),
         HumanMessage(content=prompt)],
    )

    import json
    try:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        insights = json.loads(content)
    except (json.JSONDecodeError, IndexError):
        insights = []

    return {"insights": insights}


async def generate_agent_feedback(state: PerformanceAnalystState) -> dict[str, Any]:
    """Create specific recommendations for each agent based on insights."""
    logger.info("performance_analyst.generate_agent_feedback")
    insights = state.get("insights", [])
    patterns = state.get("patterns", [])

    if not insights and not patterns:
        return {"agent_feedback": {}}

    llm = get_llm(temperature=0.3)
    prompt = f"""Based on these performance insights, generate specific feedback for each AI agent.

Insights: {insights}
Patterns: {patterns}

Generate feedback as JSON:
{{
    "trend_scout": ["Weight topics X, Y higher because...", ...],
    "idea_generator": ["Suggest shorter formats because...", ...],
    "script_architect": ["Prefer hook style A because...", ...],
    "seo_optimizer": ["Include numbers in titles because...", ...]
}}"""

    response = await invoke_with_retry(
        llm,
        [SystemMessage(content="You are an AI agent coordinator. Return valid JSON only."),
         HumanMessage(content=prompt)],
    )

    import json
    try:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        feedback = json.loads(content)
    except (json.JSONDecodeError, IndexError):
        feedback = {}

    return {"agent_feedback": feedback}


async def update_knowledge_graph(state: PerformanceAnalystState) -> dict[str, Any]:
    """Store insights as nodes in knowledge graph linked to content."""
    logger.info("performance_analyst.update_knowledge_graph")
    # In production, this would create Insight nodes in Neo4j
    # linked to the relevant Content nodes
    insights = state.get("insights", [])
    return {"graph_updated": True, "insights_stored": len(insights)}


# --- Graph Construction ---


def create_performance_analyst_graph() -> StateGraph:
    """Create the Performance Analyst LangGraph."""
    graph = StateGraph(PerformanceAnalystState)

    # Add nodes
    graph.add_node("sync_youtube_data", sync_youtube_data)
    graph.add_node("compute_metrics", compute_metrics)
    graph.add_node("detect_patterns", detect_patterns)
    graph.add_node("benchmark_performance", benchmark_performance)
    graph.add_node("generate_insights", generate_insights)
    graph.add_node("generate_agent_feedback", generate_agent_feedback)
    graph.add_node("update_knowledge_graph", update_knowledge_graph)

    # Edges: sync -> compute -> parallel(patterns, benchmark) -> insights -> feedback -> graph
    graph.add_edge(START, "sync_youtube_data")
    graph.add_edge("sync_youtube_data", "compute_metrics")
    graph.add_edge("compute_metrics", "detect_patterns")
    graph.add_edge("compute_metrics", "benchmark_performance")
    graph.add_edge("detect_patterns", "generate_insights")
    graph.add_edge("benchmark_performance", "generate_insights")
    graph.add_edge("generate_insights", "generate_agent_feedback")
    graph.add_edge("generate_agent_feedback", "update_knowledge_graph")
    graph.add_edge("update_knowledge_graph", END)

    return graph.compile()


async def run_performance_analyst(
    channel_analytics: dict,
    video_analytics: list[dict],
) -> dict[str, Any]:
    """Run the Performance Analyst agent pipeline."""
    logger.info("performance_analyst.run", video_count=len(video_analytics))

    graph = create_performance_analyst_graph()
    initial_state: PerformanceAnalystState = {
        "channel_analytics": channel_analytics,
        "video_analytics": video_analytics,
    }

    result = await graph.ainvoke(initial_state)

    logger.info(
        "performance_analyst.complete",
        insights_count=len(result.get("insights", [])),
        feedback_agents=list(result.get("agent_feedback", {}).keys()),
    )
    return result


# --- Helpers ---


def _format_videos(videos: list[dict]) -> str:
    """Format videos for LLM prompt."""
    lines = []
    for v in videos:
        lines.append(
            f"- \"{v.get('title', 'Unknown')}\" | "
            f"Views: {v.get('views', 0):,} | "
            f"CTR: {v.get('ctr', 0):.1f}% | "
            f"Retention: {v.get('average_percentage_viewed', 0):.0f}% | "
            f"Likes: {v.get('likes', 0):,} | "
            f"Comments: {v.get('comments', 0):,}"
        )
    return "\n".join(lines)
