"""LangGraph-based AI agents for the Creator OS pipeline.

Agents:
    - **TrendScout**: Monitors external sources and scores trends for relevance.
    - **IdeaGenerator**: Transforms scored trends into actionable content ideas.
    - **ScriptArchitect**: Produces full scripts / outlines from approved ideas.
    - **SEOOptimizer**: Generates SEO metadata packages for every content type.
    - **PerformanceAnalyst**: Analyses published content and recommends improvements.
    - **MediaKit**: Builds auto-updating media kits for brand partnerships.
    - **Orchestrator**: Coordinates the full pipeline with human-in-the-loop gates.

State definitions live in ``app.agents.state`` and LangChain tool wrappers
live under ``app.agents.tools``.
"""

from app.agents.state import (
    IdeaGeneratorState,
    MediaKitState,
    OrchestratorState,
    PerformanceAnalystState,
    ScriptArchitectState,
    SEOOptimizerState,
    TrendScoutState,
)
from app.agents.script_architect import (
    create_script_architect_graph,
    run_script_architect,
)
from app.agents.seo_optimizer import (
    create_seo_optimizer_graph,
    run_seo_optimizer,
)

__all__ = [
    # State classes
    "TrendScoutState",
    "IdeaGeneratorState",
    "ScriptArchitectState",
    "SEOOptimizerState",
    "PerformanceAnalystState",
    "MediaKitState",
    "OrchestratorState",
    # Script Architect agent
    "create_script_architect_graph",
    "run_script_architect",
    # SEO Optimizer agent
    "create_seo_optimizer_graph",
    "run_seo_optimizer",
]
