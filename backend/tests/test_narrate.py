"""Story 07 deterministic and provider narration tests."""

import asyncio

from backend.core import narrate

FACTS = {
    "intent": "ota_by_vendor",
    "cycle": "2026-06-H1",
    "scope": {"vendor": None, "office": None},
    "result_count": 1,
    "rows": [{"vendor": "Vendor A", "ota_pct": 91.2, "trips": 100, "delayed_trips": 9, "avg_delay_min": 20.0}],
    "quality": {"unclassified_severity_count": 0},
}


def test_template_handles_data_and_no_data() -> None:
    narrative = narrate.render_template(FACTS)
    assert "Vendor A" in narrative
    assert "91.2" in narrative
    assert "2026-06-H1" in narrative

    empty = {**FACTS, "result_count": 0, "rows": []}
    assert "No data" in narrate.render_template(empty)


def test_provider_receives_bounded_facts_and_content() -> None:
    class FakeProvider:
        def __init__(self):
            self.facts = None

        async def complete(self, facts):
            self.facts = facts
            return {"choices": [{"message": {"content": "Grounded provider narrative."}}]}

    provider = FakeProvider()
    result = asyncio.run(narrate.narrate_with_sarvam(FACTS, provider=provider, api_key="test-key"))
    assert result == "Grounded provider narrative."
    assert provider.facts["rows"] == FACTS["rows"]
    assert "question" not in provider.facts


def test_missing_key_and_null_content_fall_back() -> None:
    assert asyncio.run(narrate.narrate_with_sarvam(FACTS, api_key=None)) == narrate.render_template(FACTS)

    class NullProvider:
        async def complete(self, facts):
            return {"choices": [{"message": {"content": None}}]}

    assert asyncio.run(narrate.narrate_with_sarvam(FACTS, provider=NullProvider(), api_key="test-key")) == narrate.render_template(FACTS)
