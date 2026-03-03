"""Agent-related Pydantic schemas."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class AgentStatus(BaseModel):
    """Real-time agent status update sent via WebSocket."""

    agent_name: str
    status: str  # "idle" | "running" | "waiting_human" | "completed" | "error"
    current_node: Optional[str] = None
    progress: float = 0.0  # 0.0 to 1.0
    message: Optional[str] = None
    timestamp: datetime


class AgentOutput(BaseModel):
    """Output from a completed agent run."""

    agent_name: str
    run_id: str
    status: str
    output: Any = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    nodes_executed: list[str] = []


class AgentRun(BaseModel):
    """Request to run an agent or pipeline."""

    agent_name: Optional[str] = None  # None = full pipeline
    pipeline_type: str = "full_pipeline"  # "full_pipeline" | "single_agent" | "custom"
    agents: list[str] = []  # for custom pipeline
    human_gates: dict[str, bool] = {}  # agent_name → require_approval
    input_data: dict = {}


class OrchestratorStatus(BaseModel):
    """Status of a multi-agent orchestrator run."""

    run_id: str
    pipeline_type: str
    status: str  # "running" | "waiting_gate" | "completed" | "error"
    current_agent: Optional[str] = None
    completed_agents: list[str] = []
    pending_agents: list[str] = []
    agent_outputs: dict[str, Any] = {}
    waiting_gate: Optional[str] = None  # agent waiting for human approval
    started_at: datetime
    updated_at: datetime


class GateApproval(BaseModel):
    """Human approval/rejection for an agent gate."""

    approved: bool
    feedback: Optional[str] = None
    edits: Optional[dict] = None
