"""Hermetic unit tests for local_autoresearch.double_ratchet."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from local_autoresearch.double_ratchet import (
    evaluate_double_ratchet_batch,
    evaluate_single_day_double_ratchet,
    partition_dataset,
    run_double_ratchet_tournament,
)
from local_autoresearch.manifest import DoubleRatchetMutation, JevCriteriaConfig


@pytest.fixture
def sample_days() -> list[dict]:
    days = []
    for i in range(20):
        days.append(
            {
                "target_date": f"2026-09-{i + 1:02d}",
                "ticker": "SPY",
                "open_price": 570.0 + i,
                "close_price": 572.0 + i if i % 2 == 0 else 568.0 + i,
                "actual_direction": "UP" if i % 2 == 0 else "DOWN",
                "proxies": {"SPY": {"price": 570.0 + i, "change_pct": 0.2}},
                "newsletters": [{"sender": "Test", "subject": "Daily", "content": "Sample"}],
            }
        )
    return days


def test_partition_dataset(sample_days: list[dict]):
    active, held_out = partition_dataset(sample_days, held_out_ratio=0.15, seed=42)

    # 15% of 20 = 3 days
    assert len(held_out) == 3
    assert len(active) == 17
    # Zero overlap
    active_dates = {d["target_date"] for d in active}
    held_out_dates = {d["target_date"] for d in held_out}
    assert active_dates.isdisjoint(held_out_dates)


@pytest.mark.asyncio
async def test_evaluate_single_day_double_ratchet(sample_days: list[dict]):
    day = sample_days[0]
    criteria = JevCriteriaConfig(criteria_up="Up", criteria_down="Down", min_confidence=50.0)

    with (
        patch(
            "local_autoresearch.double_ratchet.generate_daily_document",
            AsyncMock(return_value="Synthesized Market Document"),
        ) as mock_doc,
        patch(
            "local_autoresearch.double_ratchet.evaluate_with_qwen_predictor",
            AsyncMock(
                return_value={
                    "predicted_direction": "UP",
                    "gated_action": "UP",
                    "confidence": 68.0,
                    "probabilities": {"UP": 0.68, "DOWN": 0.32},
                    "is_correct": True,
                    "is_traded": True,
                    "brier_score": 0.1024,
                    "model_backend": "qwen-predictor-local",
                }
            ),
        ) as mock_pred,
    ):
        res = await evaluate_single_day_double_ratchet(
            day_record=day,
            ingestion_prompt="Test ingestion prompt",
            criteria=criteria,
        )

        assert res["target_date"] == day["target_date"]
        assert res["predicted_direction"] == "UP"
        assert res["is_correct"] is True
        mock_doc.assert_called_once()
        mock_pred.assert_called_once()


@pytest.mark.asyncio
async def test_evaluate_double_ratchet_batch(sample_days: list[dict]):
    criteria = JevCriteriaConfig(criteria_up="Up", criteria_down="Down", min_confidence=50.0)

    mock_day_res = {
        "target_date": "2026-09-01",
        "predicted_direction": "UP",
        "gated_action": "UP",
        "confidence": 65.0,
        "is_correct": True,
        "is_traded": True,
        "brier_score": 0.12,
    }

    with patch(
        "local_autoresearch.double_ratchet.evaluate_single_day_double_ratchet",
        AsyncMock(return_value=mock_day_res),
    ):
        metrics, results = await evaluate_double_ratchet_batch(
            days=sample_days[:5],
            ingestion_prompt="Test prompt",
            criteria=criteria,
            max_concurrency=2,
        )

        assert metrics["total_days"] == 5
        assert metrics["traded_win_rate_pct"] == 100.0
        assert metrics["score"] > 50.0
        assert len(results) == 5


@pytest.mark.asyncio
async def test_run_double_ratchet_tournament(sample_days: list[dict], tmp_path):
    criteria = JevCriteriaConfig(criteria_up="Up", criteria_down="Down", min_confidence=50.0)
    mutation = DoubleRatchetMutation(
        ingestion_prompt="Evolved Ingestion Prompt",
        criteria=JevCriteriaConfig(criteria_up="Evolved Up", criteria_down="Evolved Down", min_confidence=55.0),
        hypothesis="Evolved synergy",
    )

    baseline_metrics = {
        "total_days": 17,
        "traded_days": 17,
        "traded_win_rate_pct": 50.0,
        "close_accuracy_pct": 50.0,
        "selectivity_pct": 100.0,
        "mean_brier": 0.25,
        "score": 50.0,
    }
    improved_metrics = dict(baseline_metrics, score=60.0, traded_win_rate_pct=65.0)

    eval_calls = 0

    async def mock_eval_batch(days, *args, **kwargs):
        nonlocal eval_calls
        eval_calls += 1
        if eval_calls == 1:
            return baseline_metrics, []
        return improved_metrics, []

    with (
        patch(
            "local_autoresearch.double_ratchet.evaluate_double_ratchet_batch",
            side_effect=mock_eval_batch,
        ),
        patch(
            "local_autoresearch.double_ratchet.generate_double_ratchet_mutation_with_strata",
            AsyncMock(return_value=mutation),
        ),
    ):
        summary = await run_double_ratchet_tournament(
            all_days=sample_days,
            iterations=1,
            held_out_ratio=0.15,
            seed=42,
            initial_criteria=criteria,
            state_path=str(tmp_path / "test_state.json"),
        )

        assert summary["iterations_run"] == 1
        assert summary["baseline_score"] == 50.0
        assert summary["champion_score"] == 60.0
        assert summary["held_out_metrics"] is not None


def test_partition_dataset_508_days():
    pseudo_508 = [{"target_date": f"d_{i}", "ticker": "SPY"} for i in range(508)]
    active, held_out = partition_dataset(pseudo_508, held_out_ratio=0.15, seed=42)

    assert len(held_out) == 76  # 508 * 0.15 = 76.2 -> 76
    assert len(active) == 432  # 508 - 76 = 432
    assert len(active) + len(held_out) == 508


def test_sqlite_document_cache(tmp_path):
    from local_autoresearch.double_ratchet import SqliteDocumentCache

    db_file = str(tmp_path / "test_cache.db")
    cache = SqliteDocumentCache(db_file)

    # Cache miss
    assert cache.get("2026-10-12", "prompt_hash_1") is None

    # Put into cache
    cache.put("2026-10-12", "prompt_hash_1", "## Distilled Briefing")

    # Cache hit
    assert cache.get("2026-10-12", "prompt_hash_1") == "## Distilled Briefing"
    # Different prompt hash -> miss
    assert cache.get("2026-10-12", "prompt_hash_2") is None


@pytest.mark.asyncio
async def test_run_double_ratchet_early_rejection_prunes_decaying_candidate(
    sample_days: list[dict], tmp_path, monkeypatch
):
    monkeypatch.setenv("DOUBLE_RATCHET_FILTER_SIZE", "5")
    monkeypatch.setenv("DOUBLE_RATCHET_EARLY_REJECT_MARGIN", "1.50")

    criteria = JevCriteriaConfig(criteria_up="Up", criteria_down="Down", min_confidence=50.0)
    mutation = DoubleRatchetMutation(
        ingestion_prompt="Mutated Ingestion",
        criteria=criteria,
        hypothesis="Bad hypothesis that regresses",
    )

    baseline_metrics = {
        "total_days": 17,
        "traded_days": 17,
        "no_trade_days": 0,
        "traded_win_rate_pct": 55.0,
        "close_accuracy_pct": 55.0,
        "selectivity_pct": 100.0,
        "mean_brier": 0.20,
        "score": 52.0,
    }
    # Decaying score on Stage 1 (delta = 45.0 - 52.0 = -7.0 < -1.50)
    regressive_stage1_metrics = dict(baseline_metrics, score=45.0)

    evaluated_batch_sizes = []

    async def mock_eval_batch(days, *args, **kwargs):
        evaluated_batch_sizes.append(len(days))
        if len(evaluated_batch_sizes) == 1:
            # Baseline (all 17 active days)
            dummy_results = [{"is_correct": True, "is_traded": True, "brier_score": 0.2}] * 17
            return baseline_metrics, dummy_results
        elif len(evaluated_batch_sizes) == 2:
            # Candidate Stage 1 (only 5 filter days)
            return regressive_stage1_metrics, []
        else:
            # Post-ratchet held out
            return baseline_metrics, []

    with (
        patch(
            "local_autoresearch.double_ratchet.evaluate_double_ratchet_batch",
            side_effect=mock_eval_batch,
        ),
        patch(
            "local_autoresearch.double_ratchet.generate_double_ratchet_mutation_with_strata",
            AsyncMock(return_value=mutation),
        ),
    ):
        summary = await run_double_ratchet_tournament(
            all_days=sample_days,
            iterations=1,
            held_out_ratio=0.15,
            seed=42,
            initial_criteria=criteria,
            state_path=str(tmp_path / "test_state.json"),
        )

        # Baseline evaluated 17 days, Candidate evaluated ONLY 5 filter days and was pruned early!
        assert evaluated_batch_sizes[0] == 17
        assert evaluated_batch_sizes[1] == 5
        # Remaining 12 days were NEVER called for the decaying candidate
        assert 12 not in evaluated_batch_sizes

        # Pruned candidate recorded in history
        cand_hist = summary["history"][1]
        assert cand_hist["accepted"] is False
        assert cand_hist["pruned_early"] is True
        assert summary["champion_score"] == 52.0


def test_partition_curriculum_weeks():
    from local_autoresearch.double_ratchet import partition_curriculum_weeks

    # Generate 50 weeks with 5 days each
    all_weeks: dict[str, list[dict]] = {}
    for w in range(1, 51):
        w_key = f"2026-W{w:02d}"
        all_weeks[w_key] = [
            {"target_date": f"2026-08-{d:02d}", "ticker": "SPY", "open_price": 500.0, "close_price": 505.0}
            for d in range(1, 6)
        ]

    active, stashed = partition_curriculum_weeks(all_weeks, test_ratio=0.10, seed=42)

    # 10% of 50 weeks = 5 weeks
    assert len(stashed) == 5
    assert len(active) == 45
    # Strict zero overlap
    assert set(active.keys()).isdisjoint(set(stashed.keys()))
    assert set(active.keys()) | set(stashed.keys()) == set(all_weeks.keys())


def test_sample_curriculum_weeks():
    from local_autoresearch.double_ratchet import sample_curriculum_weeks

    # Generate 35 weeks with 5 days each
    all_weeks: dict[str, list[dict]] = {}
    for w in range(1, 36):
        w_key = f"2026-W{w:02d}"
        all_weeks[w_key] = [
            {"target_date": f"2026-08-{d:02d}", "ticker": "SPY", "open_price": 500.0, "close_price": 505.0}
            for d in range(1, 6)
        ]

    # Sample default 10 weeks
    sampled_default = sample_curriculum_weeks(all_weeks)
    assert len(sampled_default) == 10
    assert sum(len(days) for _, days in sampled_default) == 50

    # Sample 10 weeks explicitly
    sampled = sample_curriculum_weeks(all_weeks, num_weeks=10, seed=42)

    assert len(sampled) == 10
    # Total days = 10 * 5 = 50 days
    total_days = sum(len(days) for _, days in sampled)
    assert total_days == 50

    # Verify chronological ordering
    sampled_keys = [w_key for w_key, _ in sampled]
    assert sampled_keys == sorted(sampled_keys)

    # Different seeds produce different samples
    sampled_other = sample_curriculum_weeks(all_weeks, num_weeks=10, seed=999)
    sampled_other_keys = [w_key for w_key, _ in sampled_other]
    assert sampled_keys != sampled_other_keys


def test_partition_into_curriculum_batches():
    from local_autoresearch.double_ratchet import partition_into_curriculum_batches

    # 100 weeks with 5 days each
    all_weeks: dict[str, list[dict]] = {}
    for w in range(1, 101):
        w_key = f"2026-W{w:03d}"
        all_weeks[w_key] = [
            {"target_date": f"2026-08-{d:02d}", "ticker": "SPY", "open_price": 500.0, "close_price": 505.0}
            for d in range(1, 6)
        ]

    batches, stashed = partition_into_curriculum_batches(all_weeks, num_batches=10, stashed_ratio=0.10, seed=42)

    # 10% of 100 weeks = 10 stashed weeks
    assert len(stashed) == 10
    # 90 active weeks divided into 10 batches = 9 weeks per batch
    assert len(batches) == 10
    for b in batches:
        assert len(b) == 9

    # Disjointness check
    all_batch_keys = [k for b in batches for k, _ in b]
    assert len(all_batch_keys) == 90
    assert len(set(all_batch_keys)) == 90
    assert set(all_batch_keys).isdisjoint(set(stashed.keys()))

    # Chronological ordering within batches
    for b in batches:
        keys = [k for k, _ in b]
        assert keys == sorted(keys)

    # weeks_per_batch explicit slicing
    batches_5w, _ = partition_into_curriculum_batches(
        all_weeks, num_batches=2, weeks_per_batch=5, stashed_ratio=0.10, seed=42
    )
    assert len(batches_5w) == 2
    assert len(batches_5w[0]) == 5
    assert len(batches_5w[1]) == 5


def test_partition_into_curriculum_batches_randomized_multi_regime():
    from local_autoresearch.double_ratchet import partition_into_curriculum_batches

    # 100 weeks named chronologically
    all_weeks: dict[str, list[dict]] = {}
    for w in range(1, 101):
        w_key = f"2025-W{w:03d}"
        all_weeks[w_key] = [
            {"target_date": f"2025-01-{d:02d}", "ticker": "SPY", "open_price": 500.0, "close_price": 505.0}
            for d in range(1, 6)
        ]

    # Default shuffle_weeks=True: multi-regime cross-sectional batches
    batches_shuffled, stashed_shuffled = partition_into_curriculum_batches(
        all_weeks, num_batches=10, weeks_per_batch=5, stashed_ratio=0.10, seed=42, shuffle_weeks=True
    )
    assert len(batches_shuffled) == 10
    assert len(stashed_shuffled) == 10

    # Ensure each batch contains 5 weeks
    for b in batches_shuffled:
        assert len(b) == 5
        keys = [k for k, _ in b]
        # Must be chronologically sorted internally for forward lesson compounding
        assert keys == sorted(keys)

    # First batch must NOT be consecutive weeks (e.g. W001, W002, W003...)
    batch_0_keys = [k for k, _ in batches_shuffled[0]]
    # In randomized multi-regime, the span from min week to max week is wide across the timeline
    min_w = int(batch_0_keys[0].split("-W")[1])
    max_w = int(batch_0_keys[-1].split("-W")[1])
    assert max_w - min_w > 10, f"Expected multi-regime wide span, got {min_w} to {max_w}"

    # Sequential mode (shuffle_weeks=False) produces contiguous blocks
    batches_seq, _ = partition_into_curriculum_batches(
        all_weeks, num_batches=10, weeks_per_batch=5, stashed_ratio=0.10, seed=42, shuffle_weeks=False
    )
    seq_0_keys = [k for k, _ in batches_seq[0]]
    seq_min = int(seq_0_keys[0].split("-W")[1])
    seq_max = int(seq_0_keys[-1].split("-W")[1])
    # In contiguous mode, 5 weeks span exactly 4 or 5 intervals (depending on stashed removal)
    assert seq_max - seq_min <= 6


@pytest.mark.asyncio
async def test_run_double_ratchet_curriculum_tournament_walk_forward(tmp_path):
    from local_autoresearch.double_ratchet import run_double_ratchet_curriculum_tournament

    all_weeks: dict[str, list[dict]] = {}
    for w in range(1, 31):
        w_key = f"2026-W{w:02d}"
        all_weeks[w_key] = [
            {"target_date": f"2026-08-{d:02d}", "ticker": "SPY", "open_price": 500.0, "close_price": 505.0}
            for d in range(1, 6)
        ]

    evaluated_batches = []

    async def mock_eval_curriculum(curriculum_weeks, ingestion_prompt, criteria, *args, **kwargs):
        evaluated_batches.append([k for k, _ in curriculum_weeks])
        score = 50.0 + len(evaluated_batches) * 2.0
        metrics = {
            "total_days": 15,
            "traded_days": 15,
            "no_trade_days": 0,
            "traded_win_rate_pct": 55.0,
            "score": score,
        }
        results = [{"target_date": "2026-08-01", "is_correct": True, "is_traded": True}]
        lessons = ["Test lesson"]
        return metrics, results, lessons

    mock_mutation = DoubleRatchetMutation(
        ingestion_prompt="Mutated Prompt 1",
        criteria=JevCriteriaConfig(criteria_up="Up", criteria_down="Down", min_confidence=55.0),
        hypothesis="Test hypothesis",
    )

    with (
        patch("local_autoresearch.double_ratchet.evaluate_curriculum_batch", side_effect=mock_eval_curriculum),
        patch(
            "local_autoresearch.double_ratchet.generate_double_ratchet_mutation_with_strata",
            AsyncMock(return_value=mock_mutation),
        ),
    ):
        summary = await run_double_ratchet_curriculum_tournament(
            all_weeks=all_weeks,
            num_curriculum_weeks=10,
            iterations=3,
            cache_db_path=str(tmp_path / "test.db"),
            no_cache=True,
            state_path=str(tmp_path / "state.json"),
        )

        assert summary["iterations_run"] == 3
        # 3 iterations = Batch 0 (baseline) + Batch 1 (cand 1) + Batch 2 (cand 2) + post-test on stashed weeks
        # Total evaluated calls = 4 (3 batches + 1 stashed test)
        assert len(evaluated_batches) == 4
        # Batches 0, 1, 2 must be different slices of weeks (walk-forward)!
        assert evaluated_batches[0] != evaluated_batches[1]
        assert evaluated_batches[1] != evaluated_batches[2]
        # Champion score increased
        assert summary["champion_score"] > summary["baseline_score"]


@pytest.mark.asyncio
async def test_run_weekly_mini_autoresearch(tmp_path):
    import sqlite3
    from contextlib import closing

    from local_autoresearch.document_builder import get_point_in_time_memories
    from local_autoresearch.double_ratchet import run_weekly_mini_autoresearch

    db_path = str(tmp_path / "test_mini_cycle.db")
    with closing(sqlite3.connect(db_path)) as conn:
        with conn:
            conn.execute(
                """
            CREATE TABLE cached_memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                importance_score INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
            )
        conn.commit()

    week_results = [
        {
            "target_date": "2026-09-01",
            "predicted_direction": "UP",
            "actual_direction": "UP",
            "confidence": 65.0,
            "is_correct": True,
            "is_traded": True,
        },
        {
            "target_date": "2026-09-02",
            "predicted_direction": "UP",
            "actual_direction": "DOWN",
            "confidence": 70.0,
            "is_correct": False,
            "is_traded": True,
        },
        {
            "target_date": "2026-09-03",
            "predicted_direction": "UP",
            "actual_direction": "UP",
            "confidence": 60.0,
            "is_correct": True,
            "is_traded": True,
        },
        {
            "target_date": "2026-09-04",
            "predicted_direction": "NO_TRADE",
            "actual_direction": "UP",
            "confidence": 50.0,
            "is_correct": False,
            "is_traded": False,
        },
        {
            "target_date": "2026-09-05",
            "predicted_direction": "UP",
            "actual_direction": "DOWN",
            "confidence": 68.0,
            "is_correct": False,
            "is_traded": True,
        },
    ]

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": (
                        "- Lesson: Avoid buying into overnight gap-ups when Treasury yields rise > 4 bps.\n"
                        "- Lesson: Unconfirmed tech divergence on QQQ leads to afternoon SPY roll-over."
                    )
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        lessons = await run_weekly_mini_autoresearch(
            week_key="2026-W36",
            week_results=week_results,
            strata_url="http://localhost:8080/v1",
            db_path=db_path,
            run_id="test_run_1",
        )

    assert len(lessons) == 2
    assert "Treasury yields rise" in lessons[0]
    assert "tech divergence" in lessons[1]

    # Verify lessons exist in SQLite cached_memories
    with closing(sqlite3.connect(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT content, created_at FROM cached_memories")
        rows = cursor.fetchall()
        assert len(rows) == 2
        # Timestamped as Friday close
        assert "2026-09-05T20:00:00Z" in rows[0][1]

    # Check Point-in-Time retrieval:
    # 1. Friday morning (2026-09-05) cannot see this lesson (zero lookahead)
    memories_friday_morning = get_point_in_time_memories("2026-09-05", db_path=db_path)
    assert len(memories_friday_morning) == 0

    # 2. Next Monday (2026-09-08) CAN see the lesson
    memories_next_monday = get_point_in_time_memories("2026-09-08", db_path=db_path)
    assert len(memories_next_monday) == 2


def test_query_memories_for_autoresearch(tmp_path):
    import sqlite3
    from contextlib import closing

    from local_autoresearch.double_ratchet import query_memories_for_autoresearch

    db_path = str(tmp_path / "test_mem_query.db")
    with closing(sqlite3.connect(db_path)) as conn:
        with conn:
            conn.execute(
                """
            CREATE TABLE cached_memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                importance_score INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
            )
        conn.execute(
            """
            INSERT INTO cached_memories VALUES
            ('1', 'Post-mortem: Fading unconfirmed gap-up caused 1.5% loss', 'POST_MORTEM', 90, '2026-09-01T12:00:00Z'),
            ('2', 'Lesson: Enforce >=60% confidence floor', 'LESSON_LEARNED', 85, '2026-09-02T12:00:00Z')
            """
        )
        conn.commit()

    res = query_memories_for_autoresearch(db_path=db_path, limit=5)
    assert "HISTORICAL MEMORIES & LESSONS" in res
    assert "Fading unconfirmed gap-up" in res
    assert "Enforce >=60% confidence floor" in res


def test_summarize_recent_errors():
    from local_autoresearch.double_ratchet import summarize_recent_errors

    results = [
        {
            "target_date": "2026-09-01",
            "predicted_direction": "UP",
            "actual_direction": "UP",
            "confidence": 65.0,
            "is_correct": True,
            "is_traded": True,
        },
        {
            "target_date": "2026-09-02",
            "predicted_direction": "UP",
            "actual_direction": "DOWN",
            "confidence": 56.0,
            "is_correct": False,
            "is_traded": True,
        },
        {
            "target_date": "2026-09-03",
            "predicted_direction": "NO_TRADE",
            "actual_direction": "UP",
            "confidence": 52.0,
            "is_correct": False,
            "is_traded": False,
        },
    ]

    summary = summarize_recent_errors(results, limit=5)
    assert "RECENT PREDICTIVE FAILURES" in summary
    assert "2026-09-02: Predicted UP (56.0%) | Actual was DOWN" in summary
    assert "2026-09-03: NO_TRADE (52.0%) | Actual was UP (Missed trend move)" in summary
