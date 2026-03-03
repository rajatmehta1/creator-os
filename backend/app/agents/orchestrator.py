"""Orchestrator Agent — LangGraph supervisor coordinating all agents.

Routes requests to appropriate agents, manages full pipeline
(Trend -> Idea -> Script -> SEO), and handles human-in-the-loop gates.
"""

import time
from typing import Any

import structlog
from langgraph.graph import END, START, StateGraph

from app.agents.state import OrchestratorState

logger = structlog.get_logger()


# --- Node Functions ---


async def route_request(state: OrchestratorState) -> dict[str, Any]:
    """Determine which agents to run based on pipeline type."""
    logger.info("orchestrator.route", pipeline_type=state.get("pipeline_type"))
    pipeline_type = state.get("pipeline_type", "full_pipeline")

    if pipeline_type == "full_pipeline":
        agents = ["trend_scout", "idea_generator", "script_architect", "seo_optimizer"]
    elif pipeline_type == "single_agent":
        agents = state.get("requested_agents", [])[:1]
    elif pipeline_type == "custom":
        agents = state.get("requested_agents", [])
    else:
        agents = ["trend_scout"]

    return {
        "active_agents": agents,
        "pending_agents": agents.copy(),
        "completed_agents": [],
        "status": "running",
        "started_at": time.time(),
    }


async def run_trend_scout(state: OrchestratorState) -> dict[str, Any]:
    """Execute the Trend Scout agent."""
    logger.info("orchestrator.run_trend_scout")

    if "trend_scout" not in state.get("active_agents", []):
        return {}

    try:
        from app.agents.trend_scout import run_trend_scout as _run_trend_scout

        result = await _run_trend_scout(
            creator_id=state.get("creator_id", ""),
            niche=state.get("creator_niche", ""),
            topics=state.get("creator_topics", []),
        )
        pending = [a for a in state.get("pending_agents", []) if a != "trend_scout"]
        completed = state.get("completed_agents", []) + ["trend_scout"]

        return {
            "agent_outputs": {**state.get("agent_outputs", {}), "trend_scout": result},
            "pending_agents": pending,
            "completed_agents": completed,
            "current_agent": "trend_scout",
        }
    except Exception as e:
        logger.error("orchestrator.trend_scout_error", error=str(e))
        return {
            "errors": state.get("errors", []) + [f"trend_scout: {str(e)}"],
            "pending_agents": [a for a in state.get("pending_agents", []) if a != "trend_scout"],
        }


async def check_trend_gate(state: OrchestratorState) -> str:
    """Check if human approval is needed after Trend Scout."""
    gates = state.get("human_gates_config", {})
    if gates.get("trend_scout", False):
        return "wait_gate"
    return "continue"


async def run_idea_generator(state: OrchestratorState) -> dict[str, Any]:
    """Execute the Idea Generator agent."""
    logger.info("orchestrator.run_idea_generator")

    if "idea_generator" not in state.get("active_agents", []):
        return {}

    try:
        from app.agents.idea_generator import run_idea_generator as _run_idea_gen

        trend_output = state.get("agent_outputs", {}).get("trend_scout", {})
        trends = trend_output.get("recommendations", []) if isinstance(trend_output, dict) else []

        result = await _run_idea_gen(
            creator_id=state.get("creator_id", ""),
            trends=trends,
            creator_dna=state.get("creator_dna", {}),
            count=10,
        )
        pending = [a for a in state.get("pending_agents", []) if a != "idea_generator"]
        completed = state.get("completed_agents", []) + ["idea_generator"]

        return {
            "agent_outputs": {**state.get("agent_outputs", {}), "idea_generator": result},
            "pending_agents": pending,
            "completed_agents": completed,
            "current_agent": "idea_generator",
        }
    except Exception as e:
        logger.error("orchestrator.idea_generator_error", error=str(e))
        return {
            "errors": state.get("errors", []) + [f"idea_generator: {str(e)}"],
            "pending_agents": [a for a in state.get("pending_agents", []) if a != "idea_generator"],
        }


async def run_script_architect(state: OrchestratorState) -> dict[str, Any]:
    """Execute the Script Architect agent."""
    logger.info("orchestrator.run_script_architect")

    if "script_architect" not in state.get("active_agents", []):
        return {}

    try:
        from app.agents.script_architect import run_script_architect as _run_script

        idea_output = state.get("agent_outputs", {}).get("idea_generator", {})
        ideas = idea_output.get("final_ideas", []) if isinstance(idea_output, dict) else []
        top_idea = ideas[0] if ideas else {"title": "Untitled", "hook": "", "angle": ""}

        result = await _run_script(
            idea=top_idea,
            creator_dna=state.get("creator_dna", {}),
        )
        pending = [a for a in state.get("pending_agents", []) if a != "script_architect"]
        completed = state.get("completed_agents", []) + ["script_architect"]

        return {
            "agent_outputs": {**state.get("agent_outputs", {}), "script_architect": result},
            "pending_agents": pending,
            "completed_agents": completed,
            "current_agent": "script_architect",
        }
    except Exception as e:
        logger.error("orchestrator.script_architect_error", error=str(e))
        return {
            "errors": state.get("errors", []) + [f"script_architect: {str(e)}"],
            "pending_agents": [a for a in state.get("pending_agents", []) if a != "script_architect"],
        }


async def run_seo_optimizer(state: OrchestratorState) -> dict[str, Any]:
    """Execute the SEO Optimizer agent."""
    logger.info("orchestrator.run_seo_optimizer")

    if "seo_optimizer" not in state.get("active_agents", []):
        return {}

    try:
        from app.agents.seo_optimizer import run_seo_optimizer as _run_seo

        script_output = state.get("agent_outputs", {}).get("script_architect", {})
        script_text = script_output.get("final_script", "") if isinstance(script_output, dict) else ""

        result = await _run_seo(
            script=script_text,
            content_type="youtube_video",
            creator_niche=state.get("creator_niche", ""),
        )
        pending = [a for a in state.get("pending_agents", []) if a != "seo_optimizer"]
        completed = state.get("completed_agents", []) + ["seo_optimizer"]

        return {
            "agent_outputs": {**state.get("agent_outputs", {}), "seo_optimizer": result},
            "pending_agents": pending,
            "completed_agents": completed,
            "current_agent": "seo_optimizer",
        }
    except Exception as e:
        logger.error("orchestrator.seo_optimizer_error", error=str(e))
        return {
            "errors": state.get("errors", []) + [f"seo_optimizer: {str(e)}"],
            "pending_agents": [a for a in state.get("pending_agents", []) if a != "seo_optimizer"],
        }


async def wait_for_gate(state: OrchestratorState) -> dict[str, Any]:
    """Pause pipeline for human approval."""
    current_agent = state.get("current_agent", "unknown")
    logger.info("orchestrator.waiting_gate", agent=current_agent)
    return {
        "status": "waiting_gate",
        "waiting_gate": current_agent,
    }


async def finalize(state: OrchestratorState) -> dict[str, Any]:
    """Compile final output from all agent results."""
    logger.info("orchestrator.finalize")
    elapsed = time.time() - state.get("started_at", time.time())

    return {
        "status": "completed",
        "current_agent": None,
        "pending_agents": [],
        "duration_seconds": round(elapsed, 1),
        "final_output": {
            "completed_agents": state.get("completed_agents", []),
            "agent_outputs": state.get("agent_outputs", {}),
            "errors": state.get("errors", []),
        },
    }


# --- Routing ---


def should_run_ideas(state: OrchestratorState) -> str:
    """Decide whether to proceed to idea generation."""
    if "idea_generator" in state.get("active_agents", []):
        return "run_idea_generator"
    return "finalize"


def should_run_script(state: OrchestratorState) -> str:
    """Decide whether to proceed to script generation."""
    if "script_architect" in state.get("active_agents", []):
        return "run_script_architect"
    return "finalize"


def should_run_seo(state: OrchestratorState) -> str:
    """Decide whether to proceed to SEO optimization."""
    if "seo_optimizer" in state.get("active_agents", []):
        return "run_seo_optimizer"
    return "finalize"


# --- Graph Construction ---


def create_orchestrator_graph() -> StateGraph:
    """Create the Orchestrator LangGraph supervisor."""
    graph = StateGraph(OrchestratorState)

    # Add nodes
    graph.add_node("route_request", route_request)
    graph.add_node("run_trend_scout", run_trend_scout)
    graph.add_node("run_idea_generator", run_idea_generator)
    graph.add_node("run_script_architect", run_script_architect)
    graph.add_node("run_seo_optimizer", run_seo_optimizer)
    graph.add_node("wait_gate", wait_for_gate)
    graph.add_node("finalize", finalize)

    # Edges
    graph.add_edge(START, "route_request")
    graph.add_edge("route_request", "run_trend_scout")
    graph.add_conditional_edges("run_trend_scout", should_run_ideas, {
        "run_idea_generator": "run_idea_generator",
        "finalize": "finalize",
    })
    graph.add_conditional_edges("run_idea_generator", should_run_script, {
        "run_script_architect": "run_script_architect",
        "finalize": "finalize",
    })
    graph.add_conditional_edges("run_script_architect", should_run_seo, {
        "run_seo_optimizer": "run_seo_optimizer",
        "finalize": "finalize",
    })
    graph.add_edge("run_seo_optimizer", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


async def run_orchestrator(
    creator_id: str,
    creator_niche: str,
    creator_topics: list[str],
    creator_dna: dict | None = None,
    pipeline_type: str = "full_pipeline",
    agents: list[str] | None = None,
    human_gates: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Run the orchestrator pipeline."""
    logger.info(
        "orchestrator.run",
        creator_id=creator_id,
        pipeline_type=pipeline_type,
    )

    graph = create_orchestrator_graph()
    initial_state: OrchestratorState = {
        "creator_id": creator_id,
        "creator_niche": creator_niche,
        "creator_topics": creator_topics,
        "creator_dna": creator_dna or {},
        "pipeline_type": pipeline_type,
        "requested_agents": agents or [],
        "human_gates_config": human_gates or {},
        "agent_outputs": {},
        "errors": [],
        "status": "starting",
    }

    result = await graph.ainvoke(initial_state)
    logger.info(
        "orchestrator.complete",
        status=result.get("status"),
        completed=result.get("completed_agents", []),
        errors=result.get("errors", []),
    )
    return result
