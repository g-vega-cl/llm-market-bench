"""Hermetic unit tests for local_autoresearch.strata_client."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from apps.engine.local_autoresearch.manifest import DataManifest, JevCriteriaConfig
from apps.engine.local_autoresearch.strata_client import (
    _extract_json_payload,
    generate_mutation_with_strata,
    is_strata_available,
)


def test_extract_json_payload_clean():
    payload = {"criteria": {"criteria_up": "Up", "criteria_down": "Down", "min_confidence": 50.0}}
    res = _extract_json_payload(json.dumps(payload))
    assert res["criteria"]["criteria_up"] == "Up"


def test_extract_json_payload_markdown_fence():
    raw = """Here is the mutation:
```json
{
  "criteria": {
    "criteria_up": "Up rules",
    "criteria_down": "Down rules",
    "min_confidence": 60.0
  },
  "manifest": {
    "include_currency_uup": false
  },
  "hypothesis": "Test hypothesis"
}
```
Hope this helps!"""
    res = _extract_json_payload(raw)
    assert res["criteria"]["criteria_up"] == "Up rules"
    assert res["manifest"]["include_currency_uup"] is False
    assert res["hypothesis"] == "Test hypothesis"


@pytest.mark.asyncio
async def test_is_strata_available():
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_client.get.return_value = mock_resp

    assert (
        await is_strata_available("http://localhost:8081/v1") is False
    )  # default client without running server returns False


@pytest.mark.asyncio
async def test_generate_mutation_with_strata_hermetic():
    baseline_criteria = JevCriteriaConfig(criteria_up="Up", criteria_down="Down")
    baseline_manifest = DataManifest()

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_response_dict = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "criteria": {
                                "criteria_up": "Price above VWAP + tech breakout",
                                "criteria_down": "Price below VWAP + yield spike",
                                "min_confidence": 65.0,
                            },
                            "manifest": {
                                "selected_newsletters": ["The Kobeissi Letter"],
                                "include_synthetic_newsletter": True,
                                "include_macro_proxies": ["QQQ", "TLT"],
                                "include_currency_uup": False,
                                "include_options_derivatives": True,
                                "include_economic_calendar": True,
                                "include_market_health_barometer": False,
                                "include_recent_market_feeling": False,
                                "include_intraday_profile": True,
                            },
                            "hypothesis": "Narrowed newsletters and pruned currency noise.",
                        }
                    )
                }
            }
        ]
    }
    mock_resp.json.return_value = mock_response_dict
    mock_client.post.return_value = mock_resp

    mutation = await generate_mutation_with_strata(
        baseline_criteria=baseline_criteria,
        baseline_manifest=baseline_manifest,
        baseline_score=50.0,
        train_score=52.0,
        test_score=49.0,
        client=mock_client,
    )

    assert mutation.criteria.min_confidence == 65.0
    assert mutation.criteria.criteria_up == "Price above VWAP + tech breakout"
    assert mutation.manifest.selected_newsletters == ["The Kobeissi Letter"]
    assert mutation.manifest.include_currency_uup is False
    assert mutation.hypothesis == "Narrowed newsletters and pruned currency noise."


def test_strata_meta_researcher_system_has_strict_premarket_mandate():
    from apps.engine.local_autoresearch.strata_client import STRATA_META_RESEARCHER_SYSTEM

    assert "STRICT TEMPORAL PRE-MARKET CONSTRAINT" in STRATA_META_RESEARCHER_SYSTEM
    assert "before the 9:30 AM ET" in STRATA_META_RESEARCHER_SYSTEM
    assert "MUST NEVER reference post-open intraday data" in STRATA_META_RESEARCHER_SYSTEM
    assert "first 30-minute" in STRATA_META_RESEARCHER_SYSTEM.lower()
