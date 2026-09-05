"""Explicit, deterministic SENSE → REASON → BENCHMARK → RECOMMEND → ACT flow."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.ops import _compute_insights, _overview_from_rows
from backend.core.reason import BENCHMARKS
from backend.models.marts import DailyKpi, VendorKpi
from backend.services.anomaly_detection import detect_daily_anomalies

AGENTS = {
    "operations_agent": "Mobility operational analysis",
    "vendor_agent": "Vendor performance analysis",
    "anomaly_agent": "Operational anomaly detection",
    "benchmark_agent": "SLA and historical benchmarking",
    "action_agent": "Recommendations and approved actions",
}

WORKFLOW = [
    {"stage": "SENSE", "agents": ["operations_agent"]},
    {"stage": "REASON", "agents": ["operations_agent", "anomaly_agent"]},
    {"stage": "BENCHMARK", "agents": ["benchmark_agent", "vendor_agent"]},
    {"stage": "RECOMMEND", "agents": ["action_agent"]},
    {"stage": "ACT", "agents": ["action_agent"], "approval_required": True},
]


def _round(value: object, digits: int = 1) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return round(float(value), digits)


class MobilityOrchestrator:
    """Coordinates real mart queries; it has no LLM or external side effects."""

    async def cycles(self, db: AsyncSession) -> list[str]:
        result = await db.execute(select(VendorKpi.cycle_or_month).distinct())
        return sorted({cycle for (cycle,) in result.all() if cycle})

    async def snapshot(self, db: AsyncSession, cycle: str | None = None) -> dict:
        cycles = await self.cycles(db)
        selected = cycle or (cycles[-1] if cycles else None)
        if selected is None:
            return {"cycle": None, "overview": None, "vendors": [], "daily": [], "insights": []}
        vendors = list((await db.scalars(select(VendorKpi).where(VendorKpi.cycle_or_month == selected))).all())
        daily = list((await db.scalars(select(DailyKpi).order_by(DailyKpi.date))).all())
        return {
            "cycle": selected,
            "overview": _overview_from_rows(vendors) if vendors else None,
            "vendors": vendors,
            "daily": daily,
            "insights": await _compute_insights(db, selected) if vendors else [],
        }

    @staticmethod
    def _insights(items: Iterable[dict]) -> list[dict]:
        out = []
        for item in items:
            severity = str(item.get("severity", "low")).upper()
            reason = str(item.get("reason", "")).upper()
            out.append(
                {
                    "severity": severity,
                    "type": "SLA_BREACH" if reason == "VS_SLA" else "PERFORMANCE_EXCEPTION",
                    "title": f"{item.get('kpi', 'Mobility metric').replace('_', ' ').upper()} {reason.replace('_', ' ').lower()}",
                    "metric": item.get("current"),
                    "benchmark": item.get("baseline"),
                    "impact": f"{item.get('reach_trips', 0)} trips in scope",
                    "recommended_action": item.get("recommended_action"),
                    "source": item,
                }
            )
        return out

    async def run(self, name: str, db: AsyncSession, cycle: str | None = None) -> dict:
        if name not in AGENTS:
            raise KeyError(name)
        state = await self.snapshot(db, cycle)
        if state["overview"] is None:
            return {"agent": name, "cycle": state["cycle"], "data": None, "warning": "marts empty — run ingest"}
        overview = state["overview"]
        if name == "operations_agent":
            return {"agent": name, "cycle": state["cycle"], "metrics": overview, "shift_readiness": {"no_show_rate": overview.get("no_show_rate"), "sev1_count": overview.get("sev1_count")}}
        if name == "vendor_agent":
            return {"agent": name, "cycle": state["cycle"], "vendors": [self.vendor_metrics(v) for v in state["vendors"]]}
        if name == "anomaly_agent":
            return {"agent": name, "cycle": state["cycle"], "anomalies": detect_daily_anomalies(state["daily"])}
        if name == "benchmark_agent":
            return {"agent": name, "cycle": state["cycle"], "benchmarks": self.benchmarks(overview), "insights": self._insights(state["insights"])}
        return {"agent": name, "cycle": state["cycle"], "actions": [item["recommended_action"] for item in self._insights(state["insights"])]}

    @staticmethod
    def vendor_metrics(vendor: VendorKpi) -> dict:
        return {
            "vendor": vendor.vendor,
            "trips": vendor.trips,
            "ota_pct": _round(vendor.ota_pct),
            "average_delay_min": _round(vendor.avg_delay_min),
            "cancellation_rate_pct": _round(vendor.no_show_rate),
            "cost_per_trip": _round(vendor.cost_per_trip, 2),
            "feedback_score": _round(vendor.csat_avg),
            "safety_alert_rate_per_1k": _round(vendor.alert_rate_per_1k),
            "sla_compliant": vendor.ota_pct is not None and vendor.ota_pct >= BENCHMARKS["ota_sla_pct"],
        }

    @staticmethod
    def benchmarks(overview: dict) -> dict:
        ota = overview.get("ota_pct")
        return {
            "ota_sla_pct": BENCHMARKS["ota_sla_pct"],
            "ota_gap_pp": _round(ota - BENCHMARKS["ota_sla_pct"]) if ota is not None else None,
            "severity": "HIGH" if ota is not None and ota < BENCHMARKS["ota_sla_pct"] else "LOW",
            "business_impact": "Delayed employee journeys and vendor SLA exposure" if ota is not None and ota < BENCHMARKS["ota_sla_pct"] else "Within OTA SLA",
        }

    async def ask(self, question: str, db: AsyncSession, cycle: str | None = None) -> dict:
        state = await self.snapshot(db, cycle)
        text = question.lower()
        agent = "vendor_agent" if any(word in text for word in ("vendor", "supplier", "abc")) else "operations_agent"
        if any(word in text for word in ("anomaly", "outlier", "unusual")):
            agent = "anomaly_agent"
        if state["overview"] is None:
            return {"question": question, "agent": agent, "answer": "No ingested mobility marts are available yet.", "metrics": {}, "benchmark": {}, "recommendation": "Run the ingest command, then retry.", "confidence": {"label": "data_coverage", "value": 0.0}}
        overview = state["overview"]
        if agent == "vendor_agent":
            chosen = next((v for v in state["vendors"] if v.vendor.lower() in text), state["vendors"][0])
            metrics = self.vendor_metrics(chosen)
            peers = [v.ota_pct for v in state["vendors"] if v.vendor != chosen.vendor and v.ota_pct is not None]
            peer_ota = sum(peers) / len(peers) if peers else None
            benchmark = {**self.benchmarks({"ota_pct": chosen.ota_pct}), "peer_ota_pct": _round(peer_ota), "peer_gap_pp": _round(chosen.ota_pct - peer_ota) if peer_ota is not None else None}
            answer = f"{chosen.vendor} OTA is {metrics['ota_pct']}% against the {BENCHMARKS['ota_sla_pct']}% SLA"
            if peer_ota is not None:
                answer += f" and peer OTA of {_round(peer_ota)}%."
            else:
                answer += "."
            return {"question": question, "agent": agent, "answer": answer, "metrics": metrics, "benchmark": benchmark, "recommendation": "Escalate to the vendor for a delay root-cause review and recovery plan.", "confidence": {"label": "data_coverage", "value": 1.0 if len(state["vendors"]) > 1 else 0.7}}
        anomalies = detect_daily_anomalies(state["daily"]) if agent == "anomaly_agent" else []
        return {"question": question, "agent": agent, "answer": f"OTA is {overview['ota_pct']}% across {overview['trips']} trips.", "metrics": overview, "benchmark": self.benchmarks(overview), "recommendation": "Review the highest-ranked operational insight and approve the proposed action if appropriate.", "anomalies": anomalies, "confidence": {"label": "data_coverage", "value": 1.0}}

    async def leadership_report(self, db: AsyncSession, cycle: str | None = None) -> dict:
        state = await self.snapshot(db, cycle)
        if state["overview"] is None:
            return {"cycle": state["cycle"], "report": "No ingested mobility data is available. Run ingest before generating a leadership report."}
        overview = state["overview"]
        top_vendors = sorted((self.vendor_metrics(v) for v in state["vendors"]), key=lambda v: (v["ota_pct"] is None, v["ota_pct"] or 0))
        risks = self._insights(state["insights"])[:3]
        report = (
            f"Mobility health for {state['cycle']}: OTA is {overview['ota_pct']}% against the {BENCHMARKS['ota_sla_pct']}% SLA across {overview['trips']} trips. "
            f"Average delay is {overview['avg_delay_min']} minutes and cost per trip is {overview['cost_per_trip']}. "
            f"There are {overview['sev1_count']} Sev-1 alerts and CSAT is {overview['csat_avg']}. "
            f"Priority action: {risks[0]['recommended_action'] if risks else 'continue monitoring current performance.'}"
        )
        return {"cycle": state["cycle"], "overall_mobility_health": self.benchmarks(overview), "metrics": overview, "vendor_performance": top_vendors, "top_risks": risks, "recommended_actions": [risk["recommended_action"] for risk in risks], "report": report}
