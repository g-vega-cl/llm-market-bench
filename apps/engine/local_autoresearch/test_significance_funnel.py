"""Hermetic Unit & Integration Tests for Adaptive 3-Stage Significance Funnel.

Zero external network calls, zero unmocked sleep delays.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from local_autoresearch.manifest import JevCriteriaConfig
from local_autoresearch.significance_funnel import (
    SignificanceFunnelConfig,
    calculate_binomial_significance,
    evaluate_stage2_escalation,
    sample_contrasting_regime_weeks,
    should_escalate_to_stage2,
)


def test_calculate_binomial_significance_small_sample_insignificant():
    """Small samples (N=23, 14 wins = 60.9%) have high p-value (~0.20) and are not significant."""
    res = calculate_binomial_significance(wins=14, total=23, null_prob=0.5, alpha=0.05)
    assert res["total"] == 23
    assert res["wins"] == 14
    assert res["win_rate_pct"] == pytest.approx(60.87, rel=1e-2)
    assert res["p_value"] == pytest.approx(0.2024, rel=1e-2)
    assert res["is_significant"] is False
    assert res["null_prob"] == 0.5
    assert res["z_score"] > 0


def test_calculate_binomial_significance_expanded_sample_significant():
    """Expanded samples (N=70, 43 wins = 61.4%) achieve p < 0.05 and are statistically significant."""
    res = calculate_binomial_significance(wins=43, total=70, null_prob=0.5, alpha=0.05)
    assert res["total"] == 70
    assert res["wins"] == 43
    assert res["win_rate_pct"] == pytest.approx(61.43, rel=1e-2)
    assert res["p_value"] < 0.05
    assert res["is_significant"] is True


def test_calculate_binomial_significance_zero_or_invalid_sessions():
    """Handles edge case of zero sessions cleanly without ZeroDivisionError."""
    res = calculate_binomial_significance(wins=0, total=0)
    assert res["total"] == 0
    assert res["wins"] == 0
    assert res["win_rate_pct"] == 0.0
    assert res["p_value"] == 1.0
    assert res["is_significant"] is False
    assert res["z_score"] == 0.0


def test_should_escalate_to_stage2_promising():
    """Candidate with >= 58.0% win rate and not early-pruned escalates to Stage 2."""
    config = SignificanceFunnelConfig(promising_win_rate=0.58)
    metrics = {
        "traded_win_rate_pct": 60.0,
        "early_pruned": False,
        "traded_days": 25,
    }
    assert should_escalate_to_stage2(metrics, config) is True


def test_should_escalate_to_stage2_low_win_rate():
    """Candidate with < 58.0% win rate does not escalate to Stage 2."""
    config = SignificanceFunnelConfig(promising_win_rate=0.58)
    metrics = {
        "traded_win_rate_pct": 52.0,
        "early_pruned": False,
        "traded_days": 25,
    }
    assert should_escalate_to_stage2(metrics, config) is False


def test_should_escalate_to_stage2_early_pruned():
    """Early-pruned candidate never escalates even if partial win rate looks high."""
    config = SignificanceFunnelConfig(promising_win_rate=0.58)
    metrics = {
        "traded_win_rate_pct": 66.7,
        "early_pruned": True,
        "traded_days": 6,
    }
    assert should_escalate_to_stage2(metrics, config) is False


def test_sample_contrasting_regime_weeks():
    """Samples distinct unseen weeks across diverse curriculum batches."""
    all_weeks = {f"2025-W{i:02d}": [{"target_date": f"2025-01-{d:02d}"} for d in range(1, 6)] for i in range(1, 21)}
    stage1_keys = {"2025-W01", "2025-W02", "2025-W03", "2025-W04", "2025-W05"}
    sampled = sample_contrasting_regime_weeks(
        all_weeks=all_weeks,
        stage1_week_keys=stage1_keys,
        num_weeks=5,
        seed=42,
    )
    assert len(sampled) == 5
    sampled_keys = {w[0] for w in sampled}
    assert sampled_keys.isdisjoint(stage1_keys)
    for _, days in sampled:
        assert len(days) == 5


@pytest.mark.asyncio
async def test_evaluate_stage2_escalation_success():
    """Candidate maintaining strong win rate over expanded sample passes Stage 2 with p < 0.05."""
    stage1_results = [
        {"target_date": f"2025-01-{i:02d}", "is_traded": True, "is_correct": True, "gated_action": "UP"}
        for i in range(1, 16)
    ] + [
        {"target_date": f"2025-01-{i:02d}", "is_traded": True, "is_correct": False, "gated_action": "DOWN"}
        for i in range(16, 26)
    ]  # 15/25 = 60.0% in Stage 1

    stage2_mock_results = [
        {"target_date": f"2025-02-{i:02d}", "is_traded": True, "is_correct": True, "gated_action": "UP"}
        for i in range(1, 30)
    ] + [
        {"target_date": f"2025-02-{i:02d}", "is_traded": True, "is_correct": False, "gated_action": "DOWN"}
        for i in range(30, 46)
    ]  # 29/45 = 64.4% in Stage 2. Combined: 44/70 = 62.9% (p = 0.0204 < 0.05)

    stage2_mock_metrics = {
        "score": 62.5,
        "traded_win_rate_pct": 64.4,
        "traded_days": 45,
        "total_days": 45,
        "early_pruned": False,
    }

    expansion_weeks = [
        ("2025-W06", [{"target_date": "2025-02-01"}]),
        ("2025-W07", [{"target_date": "2025-02-08"}]),
    ]

    with patch(
        "local_autoresearch.significance_funnel.evaluate_curriculum_batch",
        new=AsyncMock(return_value=(stage2_mock_metrics, stage2_mock_results, ["Lesson 1"])),
    ):
        config = SignificanceFunnelConfig(promising_win_rate=0.58, significance_alpha=0.05)
        decision = await evaluate_stage2_escalation(
            expansion_weeks=expansion_weeks,
            stage1_results=stage1_results,
            ingestion_prompt="Test Prompt",
            criteria=JevCriteriaConfig(criteria_up="UP", criteria_down="DOWN"),
            config=config,
            strata_url="http://127.0.0.1:8080/v1",
        )

        assert decision["escalation_evaluated"] is True
        assert decision["passed"] is True
        assert decision["cumulative_metrics"]["traded_win_rate_pct"] == pytest.approx(62.86, rel=1e-2)
        assert decision["significance"]["p_value"] < 0.05
        assert decision["significance"]["is_significant"] is True
        assert len(decision["combined_results"]) == 70


@pytest.mark.asyncio
async def test_evaluate_stage2_escalation_faded_rejection():
    """Candidate that fades in Stage 2 drops win rate, fails p < 0.05, and is rejected."""
    stage1_results = [
        {"target_date": f"2025-01-{i:02d}", "is_traded": True, "is_correct": True, "gated_action": "UP"}
        for i in range(1, 16)
    ] + [
        {"target_date": f"2025-01-{i:02d}", "is_traded": True, "is_correct": False, "gated_action": "DOWN"}
        for i in range(16, 26)
    ]  # 15/25 = 60.0%

    stage2_faded_results = [
        {"target_date": f"2025-02-{i:02d}", "is_traded": True, "is_correct": True, "gated_action": "UP"}
        for i in range(1, 16)
    ] + [
        {"target_date": f"2025-02-{i:02d}", "is_traded": True, "is_correct": False, "gated_action": "DOWN"}
        for i in range(16, 46)
    ]  # 15/45 = 33.3% in Stage 2. Combined: 30/70 = 42.8%

    stage2_faded_metrics = {
        "score": 38.0,
        "traded_win_rate_pct": 33.3,
        "traded_days": 45,
        "total_days": 45,
        "early_pruned": False,
    }

    expansion_weeks = [("2025-W06", [{"target_date": "2025-02-01"}])]

    with patch(
        "local_autoresearch.significance_funnel.evaluate_curriculum_batch",
        new=AsyncMock(return_value=(stage2_faded_metrics, stage2_faded_results, [])),
    ):
        config = SignificanceFunnelConfig(promising_win_rate=0.58, significance_alpha=0.05)
        decision = await evaluate_stage2_escalation(
            expansion_weeks=expansion_weeks,
            stage1_results=stage1_results,
            ingestion_prompt="Test Prompt",
            criteria=JevCriteriaConfig(criteria_up="UP", criteria_down="DOWN"),
            config=config,
            strata_url="http://127.0.0.1:8080/v1",
        )

        assert decision["escalation_evaluated"] is True
        assert decision["passed"] is False
        assert decision["cumulative_metrics"]["traded_win_rate_pct"] < 50.0
        assert decision["significance"]["p_value"] > 0.05
        assert decision["significance"]["is_significant"] is False


@pytest.mark.asyncio
async def test_tournament_promising_candidate_escalates_and_ratified(tmp_path):
    """End-to-end integration test: a promising candidate (>58% in Stage 1) triggers Stage 2 and is accepted."""
    from local_autoresearch.double_ratchet import run_double_ratchet_curriculum_tournament
    from local_autoresearch.manifest import DoubleRatchetMutation

    all_weeks: dict[str, list[dict]] = {}
    for w in range(1, 26):
        w_key = f"2026-W{w:02d}"
        all_weeks[w_key] = [
            {"target_date": f"2026-08-{d:02d}", "ticker": "SPY", "open_price": 500.0, "close_price": 505.0}
            for d in range(1, 6)
        ]

    call_count = 0

    async def mock_eval_curriculum(curriculum_weeks, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        # Call 1: Batch 0 baseline (50% WR)
        if call_count == 1:
            metrics = {"score": 50.0, "traded_win_rate_pct": 50.0, "traded_days": 15, "total_days": 15}
            results = [{"target_date": "2026-08-01", "is_correct": True, "is_traded": True}]
        # Call 2: Batch 1 Stage 1 (60% WR -> triggers escalation)
        elif call_count == 2:
            metrics = {"score": 60.0, "traded_win_rate_pct": 60.0, "traded_days": 25, "total_days": 25}
            results = [
                {"target_date": f"2026-08-{i:02d}", "is_correct": i <= 15, "is_traded": True, "gated_action": "UP"}
                for i in range(1, 26)
            ]
        # Call 3: Batch 1 Stage 2 expansion (+45 sessions, 29 wins -> combined 44/70 = 62.9%, p < 0.05)
        else:
            metrics = {"score": 62.0, "traded_win_rate_pct": 64.4, "traded_days": 45, "total_days": 45}
            results = [
                {"target_date": f"2026-09-{i:02d}", "is_correct": i <= 29, "is_traded": True, "gated_action": "UP"}
                for i in range(1, 46)
            ]
        return metrics, results, ["Lesson"]

    mock_mutation = DoubleRatchetMutation(
        ingestion_prompt="Mutated Prompt 1",
        criteria=JevCriteriaConfig(criteria_up="Up", criteria_down="Down", min_confidence=55.0),
        hypothesis="Promising hypothesis",
    )

    with (
        patch("local_autoresearch.double_ratchet.evaluate_curriculum_batch", side_effect=mock_eval_curriculum),
        patch("local_autoresearch.significance_funnel.evaluate_curriculum_batch", side_effect=mock_eval_curriculum),
        patch(
            "local_autoresearch.double_ratchet.generate_double_ratchet_mutation_with_strata",
            AsyncMock(return_value=mock_mutation),
        ),
    ):
        summary = await run_double_ratchet_curriculum_tournament(
            all_weeks=all_weeks,
            num_curriculum_weeks=5,
            iterations=2,
            cache_db_path=str(tmp_path / "test.db"),
            state_path=str(tmp_path / "state.json"),
            escalate_promising=True,
            promising_win_rate=0.58,
            significance_alpha=0.05,
            stage2_expansion_weeks=5,
        )

        # Baseline (Call 1) + Stage 1 (Call 2) + Stage 2 (Call 3) = 3 calls
        assert call_count >= 3
        assert summary["champion_score"] > 50.0
        assert summary["history"][1]["accepted"] is True
