"""Hermetic tests for the weekly TLT bond-predictor autoresearch loop."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm.bond_predictor_prompts import (
    BOND_PREDICTOR_CONSTRAINTS_FOOTER,
    BOND_PREDICTOR_CONSTRAINTS_HEADER,
    BOND_PREDICTOR_MUTABLE_STRATEGIES,
    BOND_PREDICTOR_PROMPT,
    split_bond_prompt,
)
from tasks.bond_autoresearch import (
    PROMPT_NAME,
    BondMetaPromptResponse,
    resolve_ratchet,
    run_bond_autoresearch,
)


def _prediction(i: int, correct: bool = True) -> dict:
    return {
        "target_date": f"2026-11-{17 + i:02d}",
        "ticker": "TLT",
        "predicted_direction": "UP" if correct else "DOWN",
        "expected_return_pct": 0.2,
        "open_price": 90.0,
        "close_price": 90.2 if correct else 89.8,
        "high_price": 90.3,
        "low_price": 89.9,
        "is_correct": correct,
        "intraday_hit": correct,
        "brier_score": 0.1,
        "conviction_score": 60.0,
    }


def test_split_bond_prompt_roundtrip():
    header, mutable, footer = split_bond_prompt(BOND_PREDICTOR_PROMPT)
    assert header == BOND_PREDICTOR_CONSTRAINTS_HEADER
    assert mutable.strip() == BOND_PREDICTOR_MUTABLE_STRATEGIES.strip()
    assert footer == BOND_PREDICTOR_CONSTRAINTS_FOOTER


def test_split_bond_prompt_falls_back_to_frozen_sections():
    header, mutable, footer = split_bond_prompt("free-form mutation text")
    assert header == BOND_PREDICTOR_CONSTRAINTS_HEADER
    assert footer == BOND_PREDICTOR_CONSTRAINTS_FOOTER
    assert "free-form mutation text" in mutable


def test_ratchet_promotes_when_score_beats_baseline():
    decision = resolve_ratchet(
        all_variants=[
            {
                "variant_tag": "base-1",
                "status": "baseline",
                "prompt_content": "BASE",
                "metrics": {"score": 20.0, "predictions_evaluated": 20, "traded_count": 20},
            },
            {"variant_tag": "active-1", "status": "active", "prompt_content": "ACTIVE", "metrics": {}},
        ],
        parent_tag="active-1",
        weekly_score=70.0,
        current_prompt="ACTIVE",
    )
    assert decision["parent_tag"] == "active-1"
    assert decision["is_baseline_beat"] is True
    assert decision["baseline_score"] < 70.0


def test_ratchet_reverts_when_score_loses_to_baseline():
    decision = resolve_ratchet(
        all_variants=[
            {
                "variant_tag": "base-1",
                "status": "baseline",
                "prompt_content": "BASE",
                "metrics": {"score": 95.0, "predictions_evaluated": 20, "traded_count": 20},
            },
            {"variant_tag": "active-1", "status": "active", "prompt_content": "ACTIVE", "metrics": {}},
        ],
        parent_tag="active-1",
        weekly_score=10.0,
        current_prompt="ACTIVE",
    )
    assert decision["parent_tag"] == "base-1"
    assert decision["current_prompt"] == "BASE"
    assert decision["is_baseline_beat"] is False


@pytest.mark.asyncio
async def test_run_bond_autoresearch_deploys_active_variant():
    mock_supabase = MagicMock()
    mutation = BondMetaPromptResponse(
        new_strategy="=== BOND MUTATION ===\nLead with the 10Y auction tail.",
        research_insight="Auction tails dominate direction on supply days.",
        confidence=70,
    )

    with (
        patch("tasks.bond_autoresearch.get_supabase_client", return_value=mock_supabase),
        patch("tasks.bond_autoresearch.TARGET_BOND_MODELS", ["gpt-6-luna"]),
        patch(
            "tasks.bond_autoresearch._fetch_week_predictions",
            return_value=[_prediction(i) for i in range(5)],
        ),
        patch(
            "tasks.bond_autoresearch._resolve_active_bond_prompt",
            return_value=("bond-baseline-gpt-6-luna", BOND_PREDICTOR_PROMPT),
        ),
        patch(
            "tasks.bond_autoresearch._fetch_all_variants",
            return_value=[
                {
                    "variant_tag": "bond-baseline-gpt-6-luna",
                    "status": "baseline",
                    "prompt_content": BOND_PREDICTOR_PROMPT,
                    "metrics": {"score": 40.0},
                }
            ],
        ),
        patch("tasks.bond_autoresearch._generate_mutation", new_callable=AsyncMock, return_value=mutation),
        patch("tasks.bond_autoresearch.add_memory", create=True),
    ):
        await run_bond_autoresearch(dry_run=False, cold_start=False)

    insert_calls = mock_supabase.table().insert.call_args_list
    assert insert_calls, "bond autoresearch must insert a new active variant"
    payload = insert_calls[0][0][0]
    assert payload["prompt_name"] == PROMPT_NAME
    assert payload["track_id"] == "gpt-6-luna"
    assert payload["status"] == "active"
    assert payload["parent_tag"] == "bond-baseline-gpt-6-luna"
    assert payload["experiment_type"] == "incremental"
    assert payload["prompt_content"].startswith(BOND_PREDICTOR_CONSTRAINTS_HEADER)
    assert payload["prompt_content"].rstrip().endswith(BOND_PREDICTOR_CONSTRAINTS_FOOTER.rstrip())
    assert "Lead with the 10Y auction tail." in payload["prompt_content"]
    assert payload["research_output"]["research_insight"].startswith("Auction tails")


@pytest.mark.asyncio
async def test_run_bond_autoresearch_skips_model_without_evaluated_predictions():
    mock_supabase = MagicMock()

    with (
        patch("tasks.bond_autoresearch.get_supabase_client", return_value=mock_supabase),
        patch("tasks.bond_autoresearch.TARGET_BOND_MODELS", ["gpt-6-luna"]),
        patch("tasks.bond_autoresearch._fetch_week_predictions", return_value=[]),
    ):
        result = await run_bond_autoresearch(dry_run=False, cold_start=False)

    assert result == [{"model": "gpt-6-luna", "status": "skipped"}]
    mock_supabase.table().insert.assert_not_called()


@pytest.mark.asyncio
async def test_run_bond_autoresearch_dry_run_writes_nothing():
    """A dry run must not seed a baseline, demote actives, or insert a variant."""
    mock_supabase = MagicMock()
    mock_supabase.table().select().eq().eq().order().limit().execute.return_value = MagicMock(data=[])
    mock_supabase.table().select().eq().eq().execute.return_value = MagicMock(data=[])

    with (
        patch("tasks.bond_autoresearch.get_supabase_client", return_value=mock_supabase),
        patch("tasks.bond_autoresearch.TARGET_BOND_MODELS", ["gpt-6-luna"]),
        patch(
            "tasks.bond_autoresearch._fetch_week_predictions",
            return_value=[_prediction(i) for i in range(5)],
        ),
    ):
        result = await run_bond_autoresearch(dry_run=True, cold_start=False)

    assert result[0]["status"] == "dry_run"
    mock_supabase.table().upsert.assert_not_called()
    mock_supabase.table().insert.assert_not_called()
