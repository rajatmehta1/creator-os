"""Multi-agent orchestrator endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.dependencies import DbSession
from app.schemas.agent import AgentRun, GateApproval, OrchestratorStatus

router = APIRouter()


@router.post("/run")
async def run_pipeline(
    request: AgentRun,
    db: DbSession,
) -> dict[str, str]:
    """Run a full or custom agent pipeline."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 6")


@router.get("/status/{run_id}", response_model=OrchestratorStatus)
async def get_pipeline_status(
    run_id: str,
    db: DbSession,
) -> OrchestratorStatus:
    """Get the status of a pipeline run."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 6")


@router.post("/gate/{run_id}/{agent}/approve")
async def approve_gate(
    run_id: str,
    agent: str,
    approval: GateApproval,
    db: DbSession,
) -> dict[str, str]:
    """Approve an agent's human-in-the-loop gate."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 6")


@router.post("/gate/{run_id}/{agent}/reject")
async def reject_gate(
    run_id: str,
    agent: str,
    approval: GateApproval,
    db: DbSession,
) -> dict[str, str]:
    """Reject an agent's output at a gate."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 6")
