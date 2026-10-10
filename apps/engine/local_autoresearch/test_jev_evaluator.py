"""Hermetic unit tests for local_autoresearch.jev_evaluator."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from apps.engine.local_autoresearch.jev_evaluator import (
    calculate_metrics,
    evaluate_single_day,
    evaluate_vault,
    evaluate_weekly_kfold,
    split_weekly_vault,
)
from apps.engine.local_autoresearch.manifest import DataManifest, JevCriteriaConfig


@pytest.mark.asyncio
async def test_evaluate_single_day_hermetic():
    day_record = {
        "target_date": "2026-10-09",
        "ticker": "SPY",
        "actual_direction": "UP",
        "economic_calendar": "CPI at expectations",
    }
    criteria = JevCriteriaConfig(
        criteria_up="Hold above VWAP",
        criteria_down="Break below VWAP",
        min_confidence=60.0,
    )
    manifest = DataManifest()

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "answers": {
            "direction": {
                "choice": "UP",
                "confidence": 0.75,
                "probabilities": {"UP": 0.75, "DOWN": 0.25},
            }
        }
    }
    mock_client.post.return_value = mock_resp

    res = await evaluate_single_day(
        day_record=day_record,
        criteria=criteria,
        manifest=manifest,
        client=mock_client,
        api_key="mock-key",
    )

    assert res["predicted_direction"] == "UP"
    assert res["gated_action"] == "UP"
    assert res["is_correct"] is True
    assert res["is_traded"] is True
    assert res["confidence"] == 75.0
    assert res["brier_score"] == pytest.approx(0.0625, abs=0.001)


@pytest.mark.asyncio
async def test_evaluate_single_day_confidence_gated():
    day_record = {
        "target_date": "2026-10-09",
        "ticker": "SPY",
        "actual_direction": "UP",
    }
    # min_confidence is 70.0, but Jev only gives 55.0%
    criteria = JevCriteriaConfig(
        criteria_up="Hold above VWAP",
        criteria_down="Break below VWAP",
        min_confidence=70.0,
    )
    manifest = DataManifest()

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "answers": {
            "direction": {
                "choice": "UP",
                "confidence": 0.55,
                "probabilities": {"UP": 0.55, "DOWN": 0.45},
            }
        }
    }
    mock_client.post.return_value = mock_resp

    res = await evaluate_single_day(
        day_record=day_record,
        criteria=criteria,
        manifest=manifest,
        client=mock_client,
        api_key="mock-key",
    )

    assert res["predicted_direction"] == "UP"
    assert res["gated_action"] == "NO_TRADE"
    assert res["is_traded"] is False


def test_calculate_metrics():
    results = [
        {"is_correct": True, "is_traded": True, "brier_score": 0.05},
        {"is_correct": True, "is_traded": True, "brier_score": 0.10},
        {"is_correct": False, "is_traded": False, "brier_score": 0.30},
        {"is_correct": False, "is_traded": True, "brier_score": 0.40},
    ]

    m = calculate_metrics(results)
    assert m["total_days"] == 4
    assert m["traded_days"] == 3
    # Traded correct: 2 out of 3 = 66.67%
    assert m["traded_win_rate_pct"] == pytest.approx(66.67, abs=0.1)
    assert m["selectivity_pct"] == 75.0


@pytest.mark.asyncio
async def test_evaluate_weekly_kfold_hermetic():
    weekly_data = {
        "2026-W01": [
            {"target_date": "2026-01-05", "actual_direction": "UP"},
            {"target_date": "2026-01-06", "actual_direction": "DOWN"},
        ],
        "2026-W02": [
            {"target_date": "2026-01-12", "actual_direction": "UP"},
            {"target_date": "2026-01-13", "actual_direction": "UP"},
        ],
        "2026-W03": [
            {"target_date": "2026-01-19", "actual_direction": "DOWN"},
            {"target_date": "2026-01-20", "actual_direction": "DOWN"},
        ],
        "2026-W04": [
            {"target_date": "2026-01-26", "actual_direction": "UP"},
            {"target_date": "2026-01-27", "actual_direction": "DOWN"},
        ],
    }

    criteria = JevCriteriaConfig(criteria_up="Up rules", criteria_down="Down rules")
    manifest = DataManifest()

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "answers": {
            "direction": {
                "choice": "UP",
                "confidence": 0.70,
                "probabilities": {"UP": 0.70, "DOWN": 0.30},
            }
        }
    }
    mock_client.post.return_value = mock_resp

    kfold_res = await evaluate_weekly_kfold(
        weekly_data=weekly_data,
        criteria=criteria,
        manifest=manifest,
        train_ratio=0.75,
        seed=42,
        client=mock_client,
        api_key="mock-key",
    )

    assert len(kfold_res["train_weeks"]) == 3
    assert len(kfold_res["test_weeks"]) == 1
    # Check that weeks are mutually exclusive
    assert set(kfold_res["train_weeks"]).isdisjoint(set(kfold_res["test_weeks"]))
    assert "effective_score" in kfold_res
    assert "overfit_penalty" in kfold_res


def test_split_weekly_vault():
    weekly_data = {f"2026-W{i:02d}": [{"target_date": f"2026-01-{i:02d}"}] for i in range(1, 11)}
    active_pool, vault_pool = split_weekly_vault(weekly_data, vault_ratio=0.20, seed=42)

    assert len(vault_pool) == 2
    assert len(active_pool) == 8
    # Ensure sets are disjoint and partition the full set
    assert set(active_pool.keys()).isdisjoint(set(vault_pool.keys()))
    assert set(active_pool.keys()) | set(vault_pool.keys()) == set(weekly_data.keys())


@pytest.mark.asyncio
async def test_evaluate_vault_hermetic():
    vault_data = {
        "2026-W09": [
            {"target_date": "2026-03-02", "actual_direction": "UP"},
            {"target_date": "2026-03-03", "actual_direction": "DOWN"},
        ]
    }
    criteria = JevCriteriaConfig(criteria_up="Up rules", criteria_down="Down rules")
    manifest = DataManifest()

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "answers": {
            "direction": {
                "choice": "UP",
                "confidence": 0.80,
                "probabilities": {"UP": 0.80, "DOWN": 0.20},
            }
        }
    }
    mock_client.post.return_value = mock_resp

    metrics = await evaluate_vault(
        vault_data=vault_data,
        criteria=criteria,
        manifest=manifest,
        client=mock_client,
        api_key="mock-key",
    )

    assert metrics["total_days"] == 2
    assert metrics["traded_days"] == 2
    assert "score" in metrics
