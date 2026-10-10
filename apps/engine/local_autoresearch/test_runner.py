"""Hermetic unit tests for local_autoresearch.runner."""

import os
import tempfile
from unittest.mock import AsyncMock, patch

import pytest
from apps.engine.local_autoresearch.cache_builder import init_cache_db, save_cached_day
from apps.engine.local_autoresearch.local_store import init_local_store
from apps.engine.local_autoresearch.manifest import (
    AutoresearchMutation,
    DataManifest,
    JevCriteriaConfig,
)
from apps.engine.local_autoresearch.runner import run_local_autoresearch_loop


@pytest.fixture
def temp_dbs():
    fd1, cache_path = tempfile.mkstemp(suffix=".db")
    fd2, local_path = tempfile.mkstemp(suffix=".db")
    os.close(fd1)
    os.close(fd2)

    init_cache_db(cache_path)
    init_local_store(local_path)

    # Seed 2 weeks of sample data
    for w_date in ["2026-10-05", "2026-10-06", "2026-10-12", "2026-10-13"]:
        save_cached_day(
            {
                "target_date": w_date,
                "ticker": "SPY",
                "open_price": 570.0,
                "close_price": 572.0,
                "actual_direction": "UP",
            },
            db_path=cache_path,
        )

    yield cache_path, local_path

    for p in [cache_path, local_path]:
        if os.path.exists(p):
            os.remove(p)


@pytest.mark.asyncio
async def test_run_local_autoresearch_loop_hermetic(temp_dbs):
    cache_path, local_path = temp_dbs

    mock_mutation = AutoresearchMutation(
        criteria=JevCriteriaConfig(
            criteria_up="Mutated UP",
            criteria_down="Mutated DOWN",
            min_confidence=60.0,
        ),
        manifest=DataManifest(include_currency_uup=False),
        hypothesis="Remove currency to prevent false breakouts.",
    )

    mock_seed_eval = {
        "train_metrics": {"score": 50.0, "traded_win_rate_pct": 55.0},
        "test_metrics": {"score": 48.0, "traded_win_rate_pct": 52.0},
        "overfit_penalty": 2.0,
        "effective_score": 47.0,
        "train_weeks": ["2026-W41"],
        "test_weeks": ["2026-W42"],
    }

    mock_iter_eval = {
        "train_metrics": {"score": 62.0, "traded_win_rate_pct": 65.0},
        "test_metrics": {"score": 60.0, "traded_win_rate_pct": 63.0},
        "overfit_penalty": 2.0,
        "effective_score": 59.0,  # 59.0 > 47.0 -> BEATS BASELINE!
        "train_weeks": ["2026-W41"],
        "test_weeks": ["2026-W42"],
    }

    with (
        patch(
            "apps.engine.local_autoresearch.runner.evaluate_weekly_kfold",
            AsyncMock(side_effect=[mock_seed_eval, mock_iter_eval]),
        ),
        patch(
            "apps.engine.local_autoresearch.runner.evaluate_vault",
            AsyncMock(return_value={"score": 58.0, "traded_win_rate_pct": 60.0}),
        ),
        patch(
            "apps.engine.local_autoresearch.runner.generate_mutation_with_strata", AsyncMock(return_value=mock_mutation)
        ),
    ):
        best = await run_local_autoresearch_loop(
            iterations=1,
            cache_db=cache_path,
            local_db=local_path,
            promote_best=False,
        )

        assert best is not None
        assert best["effective_score"] == 59.0
        assert best["criteria_up"] == "Mutated UP"
        assert best["status"] == "baseline"


@pytest.mark.asyncio
async def test_run_local_autoresearch_loop_vault_overfit_rejected(temp_dbs):
    cache_path, local_path = temp_dbs

    # Seed additional weeks so split_weekly_vault creates a Locked Vault (>= 4 weeks)
    for extra_date in ["2026-10-19", "2026-10-26", "2026-11-02"]:
        save_cached_day(
            {
                "target_date": extra_date,
                "ticker": "SPY",
                "open_price": 570.0,
                "close_price": 572.0,
                "actual_direction": "UP",
            },
            db_path=cache_path,
        )

    mock_mutation = AutoresearchMutation(
        criteria=JevCriteriaConfig(
            criteria_up="Overfit UP",
            criteria_down="Overfit DOWN",
            min_confidence=60.0,
        ),
        manifest=DataManifest(),
        hypothesis="Overfit rule that collapses on vault.",
    )

    mock_seed_eval = {
        "train_metrics": {"score": 50.0, "traded_win_rate_pct": 55.0},
        "test_metrics": {"score": 48.0, "traded_win_rate_pct": 52.0},
        "overfit_penalty": 2.0,
        "effective_score": 47.0,
        "train_weeks": ["2026-W41"],
        "test_weeks": ["2026-W42"],
    }

    mock_iter_eval = {
        "train_metrics": {"score": 75.0, "traded_win_rate_pct": 75.0},
        "test_metrics": {"score": 70.0, "traded_win_rate_pct": 70.0},
        "overfit_penalty": 5.0,
        "effective_score": 67.5,  # Beats 47.0 on active pool!
        "train_weeks": ["2026-W41"],
        "test_weeks": ["2026-W42"],
    }

    # Vault evaluation collapses to 20.0
    mock_vault_eval = {"score": 20.0, "traded_win_rate_pct": 30.0}

    with (
        patch(
            "apps.engine.local_autoresearch.runner.evaluate_weekly_kfold",
            AsyncMock(side_effect=[mock_seed_eval, mock_iter_eval]),
        ),
        patch(
            "apps.engine.local_autoresearch.runner.evaluate_vault",
            AsyncMock(side_effect=[{"score": 50.0, "traded_win_rate_pct": 50.0}, mock_vault_eval]),
        ),
        patch(
            "apps.engine.local_autoresearch.runner.generate_mutation_with_strata", AsyncMock(return_value=mock_mutation)
        ),
    ):
        best = await run_local_autoresearch_loop(
            iterations=1,
            cache_db=cache_path,
            local_db=local_path,
            promote_best=False,
        )

        assert best is not None
        # Retains the original baseline of 47.0 because the candidate was rejected by the vault!
        assert best["effective_score"] == 47.0
        assert best["criteria_up"] != "Overfit UP"
