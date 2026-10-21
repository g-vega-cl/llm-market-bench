"""Tests for Single-Prompt Ground-Truth Ratchet (Hermetic & TDD)."""

from __future__ import annotations

import pytest

from core.llm.daily_predictor_prompts import (
    DAILY_PREDICTOR_CONSTRAINTS_FOOTER,
    DAILY_PREDICTOR_CONSTRAINTS_HEADER,
    DAILY_PREDICTOR_PROMPT,
    split_daily_predictor_prompt,
)
from local_autoresearch.live_session_store import is_premarket_timestamp_clean
from local_autoresearch.single_prompt_ratchet import (
    calculate_balanced_accuracy,
    create_balanced_stratified_split,
    evaluate_prediction_record,
    extract_daily_prediction,
    extract_mutant_strategy_payload,
    is_statistically_significant_improvement,
    lint_mutant_prompt,
    passes_two_sided_gate,
    should_prune_stage1,
)


def test_split_and_assemble_prompt_preserves_frozen_structure():
    """Verify that mutating the middle strategy leaves frozen header and footer intact."""
    header, mutable, footer = split_daily_predictor_prompt(DAILY_PREDICTOR_PROMPT)

    assert header.strip() == DAILY_PREDICTOR_CONSTRAINTS_HEADER.strip()
    assert footer.strip() == DAILY_PREDICTOR_CONSTRAINTS_FOOTER.strip()
    assert "ZERO-MEAN BASE RATE" in mutable or "ANALYTICAL STRATEGY" in mutable

    new_strategy = "=== NOVEL STRATEGY ===\nAlways evaluate bond yields (TLT) against QQQ breadth."
    reconstructed = f"{header}\n\n{new_strategy}\n\n{footer}"

    h2, m2, f2 = split_daily_predictor_prompt(reconstructed)
    assert h2.strip() == DAILY_PREDICTOR_CONSTRAINTS_HEADER.strip()
    assert f2.strip() == DAILY_PREDICTOR_CONSTRAINTS_FOOTER.strip()
    assert "Always evaluate bond yields" in m2


def test_extract_daily_prediction_valid_json():
    """Verify extracting prediction from standard JSON response."""
    raw = (
        '{"predicted_direction": "UP", "confidence": 72.5, "expected_return_pct": 0.45, '
        '"rationale": "Overnight gap continuation with QQQ confirming.", "catalysts": ["Tech earnings"]}'
    )
    pred = extract_daily_prediction(raw)
    assert pred["predicted_direction"] == "UP"
    assert pred["confidence"] == 72.5
    assert pred["expected_return_pct"] == 0.45
    assert "Overnight gap" in pred["rationale"]


def test_extract_daily_prediction_with_think_tags_and_fenced_markdown():
    """Verify extraction strips native reasoning <think> and markdown code fences."""
    raw = """<think>
Evaluating overnight gaps...
SPY gap is +0.3%, but TLT is dumping and 10Y yield is up 6 bps.
This suggests rates headwind and possible profit taking.
I will predict DOWN.
</think>
```json
{
  "predicted_direction": "DOWN",
  "confidence": 68.0,
  "expected_return_pct": -0.35,
  "rationale": "Rising 10Y yield caps equity upside leading to morning reversal.",
  "catalysts": ["Yield spike"]
}
```"""
    pred = extract_daily_prediction(raw)
    assert pred["predicted_direction"] == "DOWN"
    assert pred["confidence"] == 68.0
    assert pred["expected_return_pct"] == -0.35
    assert "Yield spike" in pred["catalysts"]


def test_extract_daily_prediction_fallback_on_corrupt():
    """Verify fallback defaults gracefully when LLM emits corrupt text."""
    raw = "I think the market will go up, but I am not outputting valid json at all."
    pred = extract_daily_prediction(raw)
    assert pred["predicted_direction"] in ("UP", "DOWN")
    assert pred["confidence"] == 50.0
    assert pred["expected_return_pct"] == 0.0


def test_evaluate_prediction_record_scoring():
    """Verify evaluation record calculation of correctness, Brier score, and intraday hit."""
    session = {
        "target_date": "2026-08-15",
        "ticker": "SPY",
        "open_price": 500.0,
        "high_price": 503.0,
        "low_price": 499.0,
        "close_price": 502.5,
        "actual_direction": "UP",
    }
    prediction = {
        "predicted_direction": "UP",
        "confidence": 80.0,
        "expected_return_pct": 0.5,
    }

    eval_row = evaluate_prediction_record(session, prediction)
    assert eval_row["is_correct"] is True
    # Brier: (0.80 - 1.0)^2 = 0.04
    assert pytest.approx(eval_row["brier_score"], abs=1e-4) == 0.04
    assert eval_row["intraday_hit"] is True

    # Test incorrect prediction
    wrong_prediction = {
        "predicted_direction": "DOWN",
        "confidence": 80.0,
        "expected_return_pct": -0.5,
    }
    wrong_row = evaluate_prediction_record(session, wrong_prediction)
    assert wrong_row["is_correct"] is False
    # Brier: (0.80 - 0.0)^2 = 0.64
    assert pytest.approx(wrong_row["brier_score"], abs=1e-4) == 0.64


def test_should_prune_stage1():
    """Verify Stage 1 screening filter prunes weak candidates early."""
    # 25 evaluated, only 10 correct = 40.0% win rate -> Prune!
    assert should_prune_stage1(evaluated=25, correct=10, min_win_rate=0.52) is True

    # 25 evaluated, 14 correct = 56.0% win rate -> Pass Stage 1!
    assert should_prune_stage1(evaluated=25, correct=14, min_win_rate=0.52) is False

    # Fewer than required screening sessions (e.g. 15 < 25) -> Do not prune yet
    assert should_prune_stage1(evaluated=15, correct=5, min_win_rate=0.52, sieve_size=25) is False


def test_binomial_significance_filter():
    """Verify binomial significance requires p < alpha against 50% coin flip."""
    # 33 wins out of 51 sessions = 64.7% win rate -> p = 0.0244 < 0.05 (Significant)
    is_sig, p_val = is_statistically_significant_improvement(wins=33, total=51, alpha=0.05)
    assert is_sig is True
    assert p_val < 0.05

    # 27 wins out of 51 sessions = 52.9% win rate -> p = 0.389 > 0.05 (Not significant)
    is_sig_weak, p_val_weak = is_statistically_significant_improvement(wins=27, total=51, alpha=0.05)
    assert is_sig_weak is False
    assert p_val_weak > 0.05


def test_calculate_balanced_accuracy_exposes_always_short_bot():
    """Verify that balanced accuracy penalizes an always-short predictor in a down-biased regime."""
    # 10 sessions: 3 UP, 7 DOWN
    # Always DOWN predictor gets 7/10 = 70% raw win rate, but 0% on UP!
    dummy_records = [
        {"predicted_direction": "DOWN", "actual_direction": "UP", "is_correct": False},
        {"predicted_direction": "DOWN", "actual_direction": "UP", "is_correct": False},
        {"predicted_direction": "DOWN", "actual_direction": "UP", "is_correct": False},
        {"predicted_direction": "DOWN", "actual_direction": "DOWN", "is_correct": True},
        {"predicted_direction": "DOWN", "actual_direction": "DOWN", "is_correct": True},
        {"predicted_direction": "DOWN", "actual_direction": "DOWN", "is_correct": True},
        {"predicted_direction": "DOWN", "actual_direction": "DOWN", "is_correct": True},
        {"predicted_direction": "DOWN", "actual_direction": "DOWN", "is_correct": True},
        {"predicted_direction": "DOWN", "actual_direction": "DOWN", "is_correct": True},
        {"predicted_direction": "DOWN", "actual_direction": "DOWN", "is_correct": True},
    ]

    metrics = calculate_balanced_accuracy(dummy_records)
    assert metrics["win_rate_pct"] == 70.0
    assert metrics["recall_up_pct"] == 0.0
    assert metrics["recall_down_pct"] == 100.0
    # Balanced Accuracy: (0% + 100%) / 2 = 50.0% (Failed!)
    assert metrics["balanced_accuracy_pct"] == 50.0
    assert metrics["mcc"] == 0.0


def test_lint_mutant_prompt_blocks_dates_and_years():
    """Verify regex linter catches temporal leakage and date-anchored rules."""
    bad_prompt_year = "Always look at 2026 inflation rates before deciding."
    is_valid, reason = lint_mutant_prompt(bad_prompt_year)
    assert is_valid is False
    assert "year" in reason.lower()

    bad_prompt_date = "On August 26, expect strong tech dip-buying."
    is_valid2, reason2 = lint_mutant_prompt(bad_prompt_date)
    assert is_valid2 is False
    assert "date" in reason2.lower()

    good_prompt = (
        "=== ANALYTICAL STRATEGY ===\n"
        "1. Evaluate pre-market bond yields (TLT) against tech futures gap.\n"
        "2. If gap is > 0.3% and 10Y yield is rising, fade the gap with DOWN prediction."
    )
    is_valid3, reason3 = lint_mutant_prompt(good_prompt)
    assert is_valid3 is True
    assert reason3 is None


def test_is_premarket_timestamp_clean():
    """Verify premarket cleaner rejects any sessions timestamped post-open."""
    # Pre-market clean: 09:16 AM ET (13:16 UTC)
    assert is_premarket_timestamp_clean("2026-08-12T13:16:00Z", "Exact Current Time: 09:16:00 AM EDT") is True

    # Leaked post-open: 09:38 AM ET (13:38 UTC)
    assert is_premarket_timestamp_clean("2026-08-07T13:38:05Z", "Market Session: Pre-Market") is False

    # Leaked afternoon: 03:18 PM ET
    assert is_premarket_timestamp_clean("2026-09-23T19:18:55Z", "Exact Current Time: 03:18:55 PM EDT") is False

    # Leaked evening: 07:48 PM ET
    assert is_premarket_timestamp_clean("2026-10-01T23:48:36Z", "Exact Current Time: 07:48:36 PM EDT") is False


def test_stratified_train_test_split():
    """Verify stratified split preserves UP/DOWN class ratios in both splits."""
    from local_autoresearch.single_prompt_ratchet import create_stratified_split

    sessions = [{"target_date": f"2026-08-{i:02d}", "actual_direction": "UP"} for i in range(1, 11)] + [
        {"target_date": f"2026-09-{i:02d}", "actual_direction": "DOWN"} for i in range(1, 21)
    ]
    # Total 30 sessions: 10 UP, 20 DOWN

    train, test = create_stratified_split(sessions, train_ratio=0.7, seed=42)
    assert len(train) == 21  # 7 UP, 14 DOWN
    assert len(test) == 9  # 3 UP, 6 DOWN

    train_up = sum(1 for s in train if s["actual_direction"] == "UP")
    test_up = sum(1 for s in test if s["actual_direction"] == "UP")
    assert train_up == 7
    assert test_up == 3


@pytest.mark.asyncio
async def test_evaluate_prompt_on_live_sessions_mocked():
    """Hermetic test verifying batch evaluation loop against mocked HTTP client."""
    import httpx

    from local_autoresearch.single_prompt_ratchet import evaluate_prompt_on_live_sessions

    sessions = [
        {
            "target_date": "2026-08-01",
            "ticker": "SPY",
            "open_price": 500.0,
            "high_price": 505.0,
            "low_price": 498.0,
            "close_price": 503.0,
            "actual_direction": "UP",
            "evaluation_payload": "Context 1",
        },
        {
            "target_date": "2026-08-02",
            "ticker": "SPY",
            "open_price": 503.0,
            "high_price": 504.0,
            "low_price": 499.0,
            "close_price": 500.0,
            "actual_direction": "DOWN",
            "evaluation_payload": "Context 2",
        },
    ]

    mock_json_reply = {
        "choices": [
            {
                "message": {
                    "content": '{"predicted_direction": "UP", "confidence": 75.0, "expected_return_pct": 0.4, "rationale": "Bullish momentum"}'
                }
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_json_reply)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        res = await evaluate_prompt_on_live_sessions(
            prompt_content="test prompt",
            sessions=sessions,
            client=mock_client,
            stage1_sieve=10,
        )

        assert res["pruned"] is False
        assert res["evaluated_count"] == 2
        assert res["correct_count"] == 1  # 1st UP correct, 2nd DOWN incorrect
        assert res["win_rate"] == 0.5
        assert "score" in res["metrics"]


@pytest.mark.asyncio
async def test_mutate_daily_strategy_mocked():
    """Hermetic test verifying strategy mutation extraction with mocked client."""
    import httpx

    from local_autoresearch.single_prompt_ratchet import mutate_daily_strategy

    mock_meta_reply = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"hypothesis": "Account for 10Y yields", '
                        '"new_strategy": "=== UPDATED STRATEGY ===\\nEvaluate bond yield inversions against tech gap."}'
                    )
                }
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_meta_reply)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        new_prompt, hypothesis = await mutate_daily_strategy(
            current_prompt=DAILY_PREDICTOR_PROMPT,
            evaluated_records=[],
            client=mock_client,
        )

        assert "Account for 10Y yields" in hypothesis
        assert "=== UPDATED STRATEGY ===" in new_prompt
        assert DAILY_PREDICTOR_CONSTRAINTS_HEADER.strip() in new_prompt
        assert DAILY_PREDICTOR_CONSTRAINTS_FOOTER.strip() in new_prompt


def test_passes_two_sided_gate_rejects_perma_bear():
    """Verify that a model with high raw win rate but low UP recall is strictly rejected."""
    # Perma-bear baseline metrics: 71.0% win rate, but only 45.5% UP recall
    perma_bear_metrics = {
        "balanced_accuracy_pct": 65.25,
        "win_rate_pct": 71.0,
        "recall_up_pct": 45.45,
        "recall_down_pct": 85.0,
        "mcc": 0.333,
    }
    passed, reason = passes_two_sided_gate(
        perma_bear_metrics,
        min_recall_up=55.0,
        min_recall_down=55.0,
        min_bal_acc=58.0,
        min_mcc=0.20,
    )
    assert not passed
    assert "Recall UP" in reason
    assert "Bear-biased" in reason


def test_passes_two_sided_gate_accepts_balanced_predictor():
    """Verify that a candidate with balanced two-sided predictive skill passes."""
    balanced_metrics = {
        "balanced_accuracy_pct": 64.5,
        "win_rate_pct": 64.5,
        "recall_up_pct": 64.0,
        "recall_down_pct": 65.0,
        "mcc": 0.290,
    }
    passed, reason = passes_two_sided_gate(
        balanced_metrics,
        min_recall_up=55.0,
        min_recall_down=55.0,
        min_bal_acc=58.0,
        min_mcc=0.20,
    )
    assert passed
    assert "Passed two-sided gate" in reason


def test_create_balanced_stratified_split():
    """Verify 1:1 balanced subsampling produces exact equal UP and DOWN counts."""
    # Create synthetic imbalanced dataset: 10 UP, 25 DOWN
    sessions = [{"target_date": f"2026-08-{i:02d}", "actual_direction": "UP"} for i in range(1, 11)] + [
        {"target_date": f"2026-09-{i:02d}", "actual_direction": "DOWN"} for i in range(1, 26)
    ]

    train, test = create_balanced_stratified_split(sessions, train_ratio=0.7, seed=42)

    # Total balanced pool should be 10 UP and 10 DOWN = 20 sessions
    assert len(train) + len(test) == 20

    train_ups = sum(1 for s in train if s["actual_direction"] == "UP")
    train_downs = sum(1 for s in train if s["actual_direction"] == "DOWN")
    assert train_ups == train_downs == 7  # 70% of 10

    test_ups = sum(1 for s in test if s["actual_direction"] == "UP")
    test_downs = sum(1 for s in test if s["actual_direction"] == "DOWN")
    assert test_ups == test_downs == 3  # 30% of 10


def test_header_contains_no_trading_heuristics():
    """Verify header strictly contains identity and available context, leaving trading strategy mutable."""
    header, mutable, footer = split_daily_predictor_prompt(DAILY_PREDICTOR_PROMPT)

    # Header must NOT contain trading heuristic keywords
    forbidden_heuristics = ["RSI", "MACD", "moving average", "VWAP", "profit-taking", "gap-fill", "exhaustion", "fade"]
    for word in forbidden_heuristics:
        assert word.lower() not in header.lower(), f"Header should not contain trading heuristic '{word}'"

    # Context items must state 'where available'
    assert "where available" in header.lower()


def test_compute_quant_diagnostics():
    """Verify statistical and classification diagnostic metrics calculation."""
    from local_autoresearch.single_prompt_ratchet import compute_quant_diagnostics

    records = [
        {"predicted_direction": "UP", "actual_direction": "UP", "brier_score": 0.04},
        {"predicted_direction": "UP", "actual_direction": "UP", "brier_score": 0.09},
        {"predicted_direction": "DOWN", "actual_direction": "DOWN", "brier_score": 0.04},
        {"predicted_direction": "DOWN", "actual_direction": "UP", "brier_score": 0.64},
    ]

    diag = compute_quant_diagnostics(records)
    assert diag["total_evaluated"] == 4
    assert diag["correct_predictions"] == 3
    assert diag["win_rate_pct"] == 75.0
    assert diag["tp"] == 2
    assert diag["tn"] == 1
    assert diag["fp"] == 0
    assert diag["fn"] == 1
    assert diag["recall_up_pct"] == round(2 / 3 * 100.0, 2)
    assert diag["recall_down_pct"] == 100.0
    assert diag["balanced_accuracy_pct"] == round(0.5 * (2 / 3 + 1.0) * 100.0, 2)
    assert diag["mcc"] > 0.0
    assert diag["kelly_fraction"] == 0.5  # 2 * 0.75 - 1


def test_append_quant_journal_entry(tmp_path):
    """Verify appending formatted markdown journal entries."""
    from local_autoresearch.single_prompt_ratchet import append_quant_journal_entry

    journal_file = str(tmp_path / "test_journal.md")
    append_quant_journal_entry(
        journal_path=journal_file,
        iteration=1,
        mode="INCREMENTAL REFINEMENT",
        hypothesis="Test symmetric macro hypothesis",
        status="promoted",
        champ_score=55.0,
        mutant_score=58.5,
        in_sample_diag={
            "total_evaluated": 20,
            "correct_predictions": 13,
            "win_rate_pct": 65.0,
            "tp": 6,
            "tn": 7,
            "fp": 3,
            "fn": 4,
            "recall_up_pct": 60.0,
            "recall_down_pct": 70.0,
            "precision_up_pct": 66.7,
            "precision_down_pct": 63.6,
            "balanced_accuracy_pct": 65.0,
            "mcc": 0.301,
            "mean_brier": 0.21,
            "kelly_fraction": 0.3,
            "p_value": 0.04,
        },
        reason="Passed tests.",
    )

    with open(journal_file) as f:
        content = f.read()

    assert "## Iteration 1: INCREMENTAL REFINEMENT — Status: PROMOTED" in content
    assert "Test symmetric macro hypothesis" in content
    assert "Balanced Accuracy" in content
    assert "Kelly Fraction" in content


def test_extract_mutant_strategy_payload_unescaped_newlines():
    """Verify extracting JSON payload containing raw multiline string literals."""
    raw = """```json
{
  "hypothesis": "Weight bond yield momentum against equity futures.",
  "new_strategy": "=== SECTION 1 ===\\nParse overnight catalysts.\\n\\n=== SECTION 2 ===\\nEvaluate VWAP hold."
}
```"""
    payload = extract_mutant_strategy_payload(raw)
    assert payload is not None
    assert "bond yield momentum" in payload["hypothesis"]
    assert "SECTION 1" in payload["new_strategy"]


def test_extract_mutant_strategy_payload_regex_fallback():
    """Verify fallback regex extraction when LLM emits slightly corrupted JSON formatting."""
    raw = """Here is the updated strategy:
{
  "hypothesis": "Fade extreme gap moves when breadth diverges",
  "new_strategy": "1. Check overnight gap.\\n2. If gap > 0.4% fade toward VWAP."
}
Hope this helps!"""
    payload = extract_mutant_strategy_payload(raw)
    assert payload is not None
    assert "breadth diverges" in payload["hypothesis"]
    assert "fade toward VWAP" in payload["new_strategy"]
