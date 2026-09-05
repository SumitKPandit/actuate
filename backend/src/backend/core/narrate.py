"""Facts-only deterministic and optional Sarvam narration."""

import asyncio
import json
import logging
from typing import Any, Protocol

from backend.core.config import settings

logger = logging.getLogger(__name__)
SYSTEM_INSTRUCTION = (
    "You are a transport operations narrator. Write two or three concise sentences for a "
    "transport manager. Use only the supplied facts. Do not invent, alter, or extrapolate "
    "numeric values."
)
_DEFAULT = object()


class NarrationProvider(Protocol):
    async def complete(self, facts: dict) -> object: ...


def _value(value: Any, suffix: str = "") -> str:
    if value is None:
        return "—"
    return f"{value}{suffix}"


def _quality_note(facts: dict) -> str:
    quality = facts.get("quality") or {}
    count = quality.get("unclassified_severity_count", 0)
    if isinstance(count, (int, float)) and not isinstance(count, bool) and count > 0:
        return f" Data quality note: {int(count)} alert(s) have unclassified severity."
    return ""


def render_template(facts: dict) -> str:
    """Render every supported intent without a network call."""
    intent = facts.get("intent", "briefing")
    cycle = facts.get("cycle", "the selected cycle")
    rows = facts.get("rows") or []
    if intent == "briefing":
        headlines = facts.get("headline_facts") or []
        if not headlines:
            return f"No data is available for the operational briefing in {cycle}."
        return f"Operational briefing for {cycle}: {headlines[0]} " + " ".join(headlines[1:2])
    if not rows:
        return f"No data is available for {intent.replace('_', ' ')} in {cycle}."

    first = rows[0]
    dimension = next((first.get(key) for key in ("vendor", "office", "shift_type") if first.get(key) is not None), "the selected group")
    if intent.startswith("ota_"):
        text = f"{dimension} has {_value(first.get('ota_pct'), '%')} OTA in {cycle}, with {_value(first.get('delayed_trips'))} delayed trips across {_value(first.get('trips'))} trips."
    elif intent.startswith("cost_"):
        text = f"{dimension} is a persisted cost outlier in {cycle} at {_value(first.get('cost_per_trip'))} per trip and {_value(first.get('cost_per_km'))} per kilometre."
    elif intent.startswith("open_sev1_"):
        text = f"{dimension} has {_value(first.get('open_sev1_count'))} open Sev-1 alerts in {cycle}; {_value(first.get('unclassified_severity_count'))} alerts have unclassified severity."
    elif intent.startswith("low_csat_"):
        text = f"{dimension} has {_value(first.get('csat_avg'))} average CSAT and {_value(first.get('low_rating_share'), '%')} low ratings in {cycle}."
    else:
        text = f"{dimension} has {_value(first.get('no_show_rate'), '%')} no-show rate in {cycle}, from {_value(first.get('no_show_count'))} no-shows across {_value(first.get('legs', first.get('trips')))} legs."
    return text + _quality_note(facts)


def _provider_facts(facts: dict) -> dict:
    bounded = dict(facts)
    rows = list(facts.get("rows") or [])[:5]
    while rows:
        bounded["rows"] = rows
        if len(json.dumps(bounded, sort_keys=True, separators=(",", ":"))) < 20_000:
            break
        rows.pop()
    bounded["rows"] = rows
    return bounded


class _SarvamProvider:
    def __init__(self, api_key: str):
        from sarvamai import AsyncSarvamAI

        self.client = AsyncSarvamAI(api_subscription_key=api_key, timeout=settings.sarvam_timeout_seconds)

    async def complete(self, facts: dict) -> object:
        return await self.client.chat.completions(
            model=settings.sarvam_model,
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": json.dumps(facts, sort_keys=True)},
            ],
            reasoning_effort=None,
            max_tokens=500,
            request_options={"max_retries": settings.sarvam_max_retries},
        )


def _response_content(response: object) -> tuple[str | None, str]:
    choices = response.get("choices") if isinstance(response, dict) else getattr(response, "choices", None)
    if not choices:
        return None, "empty_choices"
    first = choices[0]
    message = first.get("message") if isinstance(first, dict) else getattr(first, "message", None)
    content = message.get("content") if isinstance(message, dict) else getattr(message, "content", None)
    if not isinstance(content, str) or not content.strip():
        return None, "empty_content"
    return content.strip(), ""


def _fallback(facts: dict, reason: str) -> str:
    logger.info("narrate_fallback=true reason=%s", reason, extra={"narrate_fallback": True, "reason": reason})
    return render_template(facts)


async def narrate_with_sarvam(
    facts: dict,
    provider: NarrationProvider | None = None,
    api_key: str | None | object = _DEFAULT,
) -> str:
    """Return provider text when valid, otherwise the deterministic template."""
    key = settings.sarvam_api_key if api_key is _DEFAULT else api_key
    if not key:
        return _fallback(facts, "missing_key")
    bounded = _provider_facts(facts)
    active_provider = provider
    if active_provider is None:
        try:
            active_provider = _SarvamProvider(str(key))
        except Exception:  # noqa: BLE001 - provider construction is an optional edge
            return _fallback(facts, "provider_error")
    try:
        async with asyncio.timeout(settings.sarvam_timeout_seconds):
            response = await active_provider.complete(bounded)
        content, reason = _response_content(response)
        return content if content is not None else _fallback(facts, reason)
    except TimeoutError:
        return _fallback(facts, "timeout")
    except Exception:  # noqa: BLE001 - provider failures must not break /ask
        return _fallback(facts, "provider_error")
