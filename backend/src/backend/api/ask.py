"""HTTP boundary for deterministic marts-backed operational questions."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.ask import (
    SUPPORTED_INTENTS,
    EmptyMartsError,
    InvalidScope,
    UnknownCycleError,
    match_intent,
    run_query,
)
from backend.core.database import get_db
from backend.core.narrate import narrate_with_sarvam

router = APIRouter(tags=["ask"])


class AskScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vendor: str | None = Field(default=None, min_length=1, max_length=100)
    office: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("vendor", "office", mode="before")
    @classmethod
    def strip_scope(cls, value):
        return value.strip() if isinstance(value, str) else value


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=500)
    cycle: str | None = Field(default=None, min_length=8, max_length=10)
    scope: AskScope | None = None


class GroundedFrom(BaseModel):
    marts: list[str]
    cycle: str


class AskResponse(BaseModel):
    sql: str
    rows: list[dict[str, object]]
    narrative: str
    grounded_from: GroundedFrom


def _facts(result) -> dict:
    quality_count = sum(
        int(row.get("unclassified_severity_count") or 0)
        for row in result.rows
        if isinstance(row.get("unclassified_severity_count"), (int, float))
    )
    return {
        "intent": result.plan.intent,
        "cycle": result.plan.cycle,
        "scope": result.plan.scope,
        "result_count": len(result.rows),
        "rows": result.rows,
        "quality": {"unclassified_severity_count": quality_count},
    }


@router.post("/ask", response_model=AskResponse)
async def ask(payload: AskRequest, db: AsyncSession = Depends(get_db)):  # noqa: B008
    intent = match_intent(payload.question)
    if intent is None:
        return JSONResponse(
            status_code=422,
            content={"detail": "unsupported question", "supported_intents": list(SUPPORTED_INTENTS)},
        )
    scope = payload.scope.model_dump() if payload.scope is not None else None
    try:
        result = await run_query(db, payload.question, payload.cycle, scope)
    except InvalidScope:
        allowed = "vendor" if intent.endswith("_by_vendor") else "office" if intent.endswith("_by_office") else None
        return JSONResponse(status_code=422, content={"detail": "invalid scope", "intent": intent, "allowed_scope": allowed})
    except EmptyMartsError:
        return JSONResponse(status_code=503, content={"detail": "marts empty - run ingest"})
    except UnknownCycleError as exc:
        return JSONResponse(
            status_code=404,
            content={"detail": "unknown cycle", "cycle": exc.cycle, "valid_cycles": exc.valid_cycles},
        )

    facts = _facts(result)
    narrative = await narrate_with_sarvam(facts)
    return AskResponse(
        sql=result.sql,
        rows=result.rows,
        narrative=narrative,
        grounded_from=GroundedFrom(marts=list(result.plan.marts), cycle=result.plan.cycle),
    )
