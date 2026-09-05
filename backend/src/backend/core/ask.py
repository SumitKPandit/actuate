"""Deterministic, marts-only query planning for the Ask API."""

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select as SqlSelect

from backend.models.marts import OfficeKpi, ShiftKpi, VendorKpi

SUPPORTED_INTENTS = (
    "ota_by_vendor",
    "ota_by_office",
    "cost_outliers_by_vendor",
    "open_sev1_by_vendor",
    "open_sev1_by_office",
    "low_csat_by_vendor",
    "low_csat_by_office",
    "no_show_by_shift",
    "no_show_by_office",
)

ALLOWED_MARTS = {"daily_kpi", "vendor_kpi", "office_kpi", "shift_kpi"}
_RAW_TABLES = ("trips", "legs", "bills", "alerts", "feedback")
_CYCLE_RE = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])-H[12]$")
_SQL_TOKENS = re.compile(
    r"(?:\b(?:select|insert|update|delete|drop|alter|create|truncate|union)\b|--|/\*|\*/|;)"
)


class UnsupportedQuestion(ValueError):
    """The question does not select exactly one supported intent."""


class InvalidScope(ValueError):
    """The supplied scope does not match the selected intent."""


class EmptyMartsError(RuntimeError):
    """The target mart has no cycle from which to resolve a request."""


class UnknownCycleError(LookupError):
    def __init__(self, cycle: str, valid_cycles: list[str]):
        self.cycle = cycle
        self.valid_cycles = valid_cycles
        super().__init__("unknown cycle")


@dataclass(frozen=True)
class QueryPlan:
    intent: str
    statement: SqlSelect
    marts: tuple[str, ...]
    cycle: str
    scope: dict[str, str | None]


@dataclass(frozen=True)
class AskResult:
    plan: QueryPlan
    rows: list[dict[str, Any]]
    sql: str


def normalize_question(question: str) -> str:
    """Lowercase, punctuation-normalize, and collapse question whitespace."""
    text = str(question or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _has(text: str, *terms: str) -> bool:
    return any(re.search(rf"\b{re.escape(term)}\b", text) for term in terms)


def match_intent(question: str) -> str | None:
    """Return one frozen intent, or ``None`` for unsupported/ambiguous input."""
    raw = str(question or "")
    if _SQL_TOKENS.search(raw.lower()):
        return None
    text = normalize_question(raw)
    metrics = {
        "ota": _has(text, "ota", "on time", "late"),
        "cost": _has(text, "cost", "costs", "cost per trip", "expensive", "billing", "billings"),
        "sev1": _has(text, "sev 1", "sev one", "sev1", "severity 1", "severity one"),
        "csat": _has(text, "csat", "rating", "ratings", "feedback", "satisfaction"),
        "no_show": _has(text, "no show", "noshow", "missed ride", "missed rides"),
    }
    matched_metrics = [name for name, matched in metrics.items() if matched]
    if len(matched_metrics) != 1:
        return None

    dimensions = {
        "vendor": _has(text, "vendor", "vendors", "supplier", "suppliers", "operator", "operators"),
        "office": _has(text, "office", "offices", "hub", "hubs", "site", "sites"),
        "shift": _has(text, "shift", "shifts"),
    }
    matched_dimensions = [name for name, matched in dimensions.items() if matched]
    if len(matched_dimensions) != 1:
        return None

    metric_name = {
        "cost": "cost_outliers",
        "sev1": "open_sev1",
        "csat": "low_csat",
    }.get(matched_metrics[0], matched_metrics[0])
    intent = f"{metric_name}_by_{matched_dimensions[0]}"
    return intent if intent in SUPPORTED_INTENTS else None


def validate_scope(intent: str, scope: dict[str, str | None] | None) -> dict[str, str | None]:
    values = {"vendor": None, "office": None}
    for key in values:
        value = (scope or {}).get(key)
        if value is not None:
            value = value.strip()
            if not value:
                raise InvalidScope
        values[key] = value

    if intent.endswith("_by_vendor") and values["office"] is not None:
        raise InvalidScope
    if intent.endswith("_by_office") and values["vendor"] is not None:
        raise InvalidScope
    if intent == "no_show_by_shift" and any(values.values()):
        raise InvalidScope
    return values


def build_plan(intent: str, cycle: str, scope: dict[str, str | None] | None = None) -> QueryPlan:
    """Build a trusted bounded SELECT without accepting question text."""
    if intent not in SUPPORTED_INTENTS or not _CYCLE_RE.fullmatch(cycle):
        raise ValueError("invalid query plan inputs")
    scope = validate_scope(intent, scope)

    if intent == "no_show_by_shift":
        model = ShiftKpi
        columns = [model.shift_type, model.cycle_or_month.label("cycle"), model.legs, model.no_show_count, model.no_show_rate]
        order = (model.no_show_rate.desc().nulls_last(), model.shift_type.asc())
        statement = select(*columns).where(model.cycle_or_month == cycle).order_by(*order).limit(50)
        return QueryPlan(intent, statement, (model.__tablename__,), cycle, scope)

    model = VendorKpi if intent.endswith("_by_vendor") else OfficeKpi
    dimension = "vendor" if model is VendorKpi else "office"
    columns_by_intent = {
        "ota": (dimension, "trips", "ota_pct", "delayed_trips", "avg_delay_min"),
        "cost": (dimension, "trips", "cost_per_trip", "cost_per_km", "cost_outlier"),
        "sev1": (dimension, "trips", "open_sev1_count", "unclassified_severity_count"),
        "csat": (dimension, "trips", "csat_avg", "low_rating_share"),
        "no_show": (dimension, "trips", "no_show_rate"),
    }
    metric = {
        "cost_outliers": "cost",
        "open_sev1": "sev1",
        "low_csat": "csat",
    }.get(intent.split("_by_", 1)[0], intent.split("_by_", 1)[0])
    names = columns_by_intent[metric]
    columns = [getattr(model, name) for name in names if name != dimension]
    columns = [getattr(model, dimension), model.cycle_or_month.label("cycle"), *columns]
    predicates = [model.cycle_or_month == cycle]
    scope_value = scope[dimension]
    if scope_value is not None:
        predicates.append(getattr(model, dimension) == scope_value)

    if metric == "ota":
        ordering = (model.ota_pct.asc().nulls_last(), getattr(model, dimension).asc())
    elif metric == "cost":
        predicates.append(model.cost_outlier.is_(True))
        ordering = (model.cost_per_trip.desc().nulls_last(), getattr(model, dimension).asc())
    elif metric == "sev1":
        ordering = (model.open_sev1_count.desc().nulls_last(), getattr(model, dimension).asc())
    elif metric == "csat":
        ordering = (model.low_rating_share.desc().nulls_last(), model.csat_avg.asc().nulls_last(), getattr(model, dimension).asc())
    else:
        ordering = (model.no_show_rate.desc().nulls_last(), getattr(model, dimension).asc())
    statement = select(*columns).where(*predicates).order_by(*ordering).limit(50)
    return QueryPlan(intent, statement, (model.__tablename__,), cycle, scope)


def _table_names(from_clause) -> set[str]:
    name = getattr(from_clause, "name", None)
    if name:
        return {name}
    element = getattr(from_clause, "element", None)
    if element is not None:
        return _table_names(element)
    left = getattr(from_clause, "left", None)
    right = getattr(from_clause, "right", None)
    return (_table_names(left) if left is not None else set()) | (_table_names(right) if right is not None else set())


def _assert_safe_plan(plan: QueryPlan, sql: str) -> None:
    if not isinstance(plan.statement, Select):
        raise ValueError("ask plan must be a SELECT")  # noqa: TRY004 - stable planner error
    limit = plan.statement._limit_clause
    limit_value = getattr(limit, "value", None)
    if not isinstance(limit_value, int) or limit_value < 0 or limit_value > 50:
        raise ValueError("ask plan must have LIMIT <= 50")
    if not plan.marts or not set(plan.marts).issubset(ALLOWED_MARTS):
        raise ValueError("ask plan references a disallowed mart")
    froms = set().union(*(_table_names(item) for item in plan.statement.get_final_froms()))
    if not froms or not froms.issubset(set(plan.marts)):
        raise ValueError("ask plan references an unapproved table")
    if ";" in sql or re.search(r"\b(?:insert|update|delete|drop|alter|create|truncate)\b", sql, re.IGNORECASE):
        raise ValueError("ask plan is not read-only")
    if re.search(rf"\b(?:{'|'.join(_RAW_TABLES)})\b", sql, re.IGNORECASE) and any(
        re.search(rf"\b(?:from|join)\s+(?:\w+\.)?{raw}\b", sql, re.IGNORECASE) for raw in _RAW_TABLES
    ):
        raise ValueError("ask plan references a raw table")


async def resolve_cycle(db: AsyncSession, model, cycle: str | None) -> tuple[str, list[str]]:
    statement = (
        select(model.cycle_or_month)
        .where(model.cycle_or_month.is_not(None))
        .distinct()
        .order_by(model.cycle_or_month.asc())
        .limit(50)
    )
    result = await db.execute(statement)
    valid_cycles = sorted({value for (value,) in result.all() if isinstance(value, str) and _CYCLE_RE.fullmatch(value)})
    if not valid_cycles:
        raise EmptyMartsError("marts empty - run ingest")
    if cycle is not None and cycle in valid_cycles:
        return cycle, valid_cycles
    if cycle is not None:
        raise UnknownCycleError(cycle, valid_cycles)
    return valid_cycles[-1], valid_cycles


async def execute_plan(db: AsyncSession, plan: QueryPlan) -> tuple[list[dict[str, Any]], str]:
    """Validate and execute the exact statement whose SQL is returned."""
    dialect = db.bind.dialect if db.bind is not None else None
    compiled = plan.statement.compile(dialect=dialect, compile_kwargs={"literal_binds": True})
    sql = str(compiled)
    _assert_safe_plan(plan, sql)
    result = await db.execute(plan.statement)
    return [dict(row) for row in result.mappings().all()], sql


async def run_query(
    db: AsyncSession,
    question: str,
    cycle: str | None = None,
    scope: dict[str, str | None] | None = None,
) -> AskResult:
    intent = match_intent(question)
    if intent is None:
        raise UnsupportedQuestion
    normalized_scope = validate_scope(intent, scope)
    model = VendorKpi if intent.endswith("_by_vendor") else OfficeKpi if intent.endswith("_by_office") else ShiftKpi
    resolved_cycle, _ = await resolve_cycle(db, model, cycle)
    plan = build_plan(intent, resolved_cycle, normalized_scope)
    rows, sql = await execute_plan(db, plan)
    return AskResult(plan, rows, sql)
