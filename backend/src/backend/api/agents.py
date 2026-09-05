"""Agentic API backed by deterministic analytics and human-approved demo actions."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.orchestrator import AGENTS, WORKFLOW, MobilityOrchestrator
from backend.core.database import get_db
from backend.services import moveinsync_data as dset
from backend.services.anomaly_detection import detect_daily_anomalies

router = APIRouter(prefix="/api", tags=["mobility agents"])
orchestrator = MobilityOrchestrator()
# CSV-backed actors that analyze the real MoveInSync trip-feedback dataset.
# They run beside the mart-backed agents without changing AGENTS or `/api/agents`.
DATASET_AGENTS = {
    "operations_agent": "Operations Agent",
    "analytics_agent": "Analytics/Insight Agent",
}
TRACE_STEPS = ["LOAD_DATA", "CLEAN_DATA", "ANALYZE", "BENCHMARK", "REASON", "RECOMMEND"]
_MAX_TRACES = 50
_EXECUTION_TRACES: list[dict] = []


def _record_execution(agent_key: str) -> dict:
    """Analyze the real CSV and persist an execution trace for the agent."""
    df = dset.get_dataframe()
    if agent_key == "operations_agent":
        columns_used = [str(col) for col in df.columns]
    else:
        columns_used = [col for col in df.columns if "rating" in col.lower()] + [
            col for col in ("business_unit", "trip_type", "trip_date") if col in df.columns
        ]
    trace = {
        "agent": DATASET_AGENTS[agent_key],
        "dataset": dset.DSET_NAME,
        "rows_analyzed": int(len(df)),
        "columns_used": columns_used,
        "steps": list(TRACE_STEPS),
        "completed_at": datetime.now(UTC).isoformat(),
        "analysis": {
            "dataset_info": dset.get_dataset_info(),
            "trip_feedback_summary": dset.get_trip_feedback_summary(),
            "route_metrics": dset.get_route_metrics(),
            "vendor_metrics": dset.get_vendor_metrics(),
        },
    }
    _EXECUTION_TRACES.append(trace)
    del _EXECUTION_TRACES[:-_MAX_TRACES]
    return trace


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    cycle: str | None = None


class ActionRequest(BaseModel):
    action: str = Field(min_length=1, max_length=120)
    target: str = Field(min_length=1, max_length=255)
    approved: bool = False


@router.get("/agents")
async def list_agents():
    return {"agents": [{"name": name, "status": "active", "role": role} for name, role in AGENTS.items()]}


@router.get("/agents/{agent_name}")
async def get_agent(agent_name: str):
    if agent_name not in AGENTS:
        raise HTTPException(status_code=404, detail="unknown agent")
    return {"name": agent_name, "status": "active", "role": AGENTS[agent_name]}


@router.post("/agents/{agent_name}/run")
async def run_agent(agent_name: str, cycle: str | None = None, db: AsyncSession = Depends(get_db)):  # noqa: B008
    if agent_name == "analytics_agent":
        trace = _record_execution("analytics_agent")
        return {"agent": agent_name, "analysis": trace["analysis"], "trace": trace}
    try:
        result = await orchestrator.run(agent_name, db, cycle)
    except KeyError:
        raise HTTPException(status_code=404, detail="unknown agent") from None
    if agent_name in DATASET_AGENTS:
        trace = _record_execution(agent_name)
        result["dataset_analysis"] = trace["analysis"]
        result["trace"] = trace
    return result


@router.get("/agent/execution-trace")
def execution_trace() -> dict:
    """Return recorded agent executions; analyze the CSV on demand if none yet."""
    if _EXECUTION_TRACES:
        traces = [dict(saved) for saved in _EXECUTION_TRACES]
    else:
        traces = [_record_execution(name) for name in DATASET_AGENTS]
    latest = dict(traces[-1])
    latest["traces"] = traces
    return latest


@router.get("/agent/workflow")
async def workflow():
    return {"workflow": [stage["stage"] for stage in WORKFLOW], "stages": WORKFLOW}


@router.post("/agent/ask")
async def ask(payload: AskRequest, db: AsyncSession = Depends(get_db)):  # noqa: B008
    return await orchestrator.ask(payload.question, db, payload.cycle)


@router.post("/agent/action")
async def action(payload: ActionRequest):
    if not payload.approved:
        return {"status": "approval_required", "action": payload.action, "target": payload.target}
    return {"status": "executed_demo", "action": payload.action, "target": payload.target, "note": "Demo action recorded only; no external communication was sent."}


@router.get("/dashboard")
async def dashboard(cycle: str | None = None, db: AsyncSession = Depends(get_db)):  # noqa: B008
    state = await orchestrator.snapshot(db, cycle)
    return {"cycle": state["cycle"], "overview": state["overview"], "insights": orchestrator._insights(state["insights"]), "anomalies": [] if state["overview"] is None else detect_daily_anomalies(state["daily"])}


@router.get("/overview")
async def overview(cycle: str | None = None, db: AsyncSession = Depends(get_db)):  # noqa: B008
    state = await orchestrator.snapshot(db, cycle)
    return {"cycle": state["cycle"], "data": state["overview"], "warning": "marts empty — run ingest" if state["overview"] is None else None}


@router.get("/insights")
async def insights(cycle: str | None = None, db: AsyncSession = Depends(get_db)):  # noqa: B008
    state = await orchestrator.snapshot(db, cycle)
    return {"cycle": state["cycle"], "insights": orchestrator._insights(state["insights"]), "warning": "marts empty — run ingest" if state["overview"] is None else None}


@router.get("/vendors")
async def vendors(cycle: str | None = None, db: AsyncSession = Depends(get_db)):  # noqa: B008
    state = await orchestrator.snapshot(db, cycle)
    return {"cycle": state["cycle"], "vendors": [orchestrator.vendor_metrics(v) for v in state["vendors"]], "warning": "marts empty — run ingest" if state["overview"] is None else None}


@router.get("/briefing")
async def briefing(cycle: str | None = None, db: AsyncSession = Depends(get_db)):  # noqa: B008
    return await orchestrator.leadership_report(db, cycle)


@router.get("/actions")
async def actions(cycle: str | None = None, db: AsyncSession = Depends(get_db)):  # noqa: B008
    state = await orchestrator.snapshot(db, cycle)
    return {"cycle": state["cycle"], "actions": [{"action": item["recommended_action"], "approval_required": True} for item in orchestrator._insights(state["insights"])]}


@router.get("/report/leadership")
async def leadership_report(cycle: str | None = None, db: AsyncSession = Depends(get_db)):  # noqa: B008
    return await orchestrator.leadership_report(db, cycle)
