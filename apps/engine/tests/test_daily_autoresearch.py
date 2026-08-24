from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tasks.daily_autoresearch import (
    calculate_daily_ratchet_metrics,
    calculate_daily_ratchet_score,
    generate_new_daily_prompt,
    run_daily_autoresearch,
)


def test_calculate_daily_ratchet_score():
    predictions = [
        {
            "is_correct": True,
            "intraday_hit": True,
            "expected_return_pct": 0.20,
            "open_price": 500.0,
            "high_price": 505.0,
            "low_price": 499.0,
            "close_price": 504.0,
            "brier_score": 0.04,
        },
        {
            "is_correct": True,
            "intraday_hit": True,
            "expected_return_pct": 0.80,
            "open_price": 500.0,
            "high_price": 505.0,
            "low_price": 499.0,
            "close_price": 504.0,
            "brier_score": 0.09,
        },
        {
            "is_correct": False,
            "intraday_hit": False,
            "expected_return_pct": 0.50,
            "open_price": 500.0,
            "high_price": 501.0,
            "low_price": 497.0,
            "close_price": 498.0,
            "brier_score": 0.64,
        },
        {
            "is_correct": True,
            "intraday_hit": True,
            "expected_return_pct": 0.40,
            "open_price": 500.0,
            "high_price": 502.0,
            "low_price": 499.5,
            "close_price": 502.0,
            "brier_score": 0.04,
        },
    ]
    # EOD Accuracy = 3/4 = 75.0% -> 0.55 * 75.0 = 41.25
    # Intraday Hit = 3/4 = 75.0% -> 0.35 * 75.0 = 26.25
    # Magnitude Capture:
    # Pred 1: Peak return = +1.0%, exp = 0.2% -> capture = 20.0%
    # Pred 2: Peak return = +1.0%, exp = 0.8% -> capture = 80.0%
    # Pred 3: Missed -> capture = 0.0%
    # Pred 4: Peak return = +0.4%, exp = 0.4% -> capture = 100.0%
    # Mean capture = (20.0 + 80.0 + 0.0 + 100.0) / 4 = 50.0% -> 0.10 * 50.0 = 5.0
    # Mean Brier = 0.2025 -> 0.2025 * 50 = 10.125
    # Combined Score = 41.25 + 26.25 + 5.0 - 10.125 = 62.375
    score = calculate_daily_ratchet_score(predictions)
    assert pytest.approx(score, 0.01) == 62.375

    metrics = calculate_daily_ratchet_metrics(predictions)
    assert pytest.approx(metrics["score"], 0.01) == 62.375
    assert metrics["close_accuracy_pct"] == 75.0
    assert metrics["intraday_hit_pct"] == 75.0
    assert metrics["magnitude_capture_pct"] == 50.0
    assert pytest.approx(metrics["mean_brier"], 0.0001) == 0.2025
    assert metrics["predictions_evaluated"] == 4
    assert metrics["correct_count"] == 3
    assert metrics["intraday_hit_count"] == 3


def test_calculate_daily_ratchet_metrics_empty():
    metrics = calculate_daily_ratchet_metrics([])
    assert metrics["score"] == 0.0
    assert metrics["predictions_evaluated"] == 0


def test_compute_magnitude_postmortem_summary():
    from tasks.daily_autoresearch import compute_magnitude_postmortem_summary

    predictions = [
        {
            "target_date": "2026-08-10",
            "predicted_direction": "UP",
            "expected_return_pct": 0.20,
            "open_price": 500.0,
            "high_price": 506.0,
            "low_price": 499.0,
            "close_price": 505.0,
            "is_correct": True,
            "intraday_hit": True,
            "brier_score": 0.04,
        },
        {
            "target_date": "2026-08-11",
            "predicted_direction": "UP",
            "expected_return_pct": 1.20,
            "open_price": 500.0,
            "high_price": 502.0,
            "low_price": 499.0,
            "close_price": 501.0,
            "is_correct": True,
            "intraday_hit": False,
            "brier_score": 0.16,
        },
    ]

    summary = compute_magnitude_postmortem_summary(predictions)
    assert "Magnitude Calibration Diagnosis" in summary
    assert "Timid / Underestimated" in summary
    assert "Overshot / Missed Target" in summary
    assert "2026-08-10" in summary
    assert "2026-08-11" in summary


@pytest.mark.asyncio
async def test_generate_new_daily_prompt_success():
    mock_llm = MagicMock()
    mock_response = MagicMock(new_prompt="New strategy instructions for intraday SPY momentum.")
    mock_llm.chat.completions.create.return_value = mock_response

    old_prompt = "Header\nInstructions\nFooter"
    predictions = [
        {
            "target_date": "2026-08-10",
            "predicted_direction": "UP",
            "expected_return_pct": 0.20,
            "open_price": 500.0,
            "high_price": 506.0,
            "low_price": 499.0,
            "close_price": 505.0,
            "is_correct": True,
            "intraday_hit": True,
            "brier_score": 0.04,
        }
    ]
    new_prompt = await generate_new_daily_prompt(
        old_prompt=old_prompt,
        baseline_score=70.0,
        predictions=predictions,
        meta_researcher=mock_llm,
    )

    assert "New strategy instructions" in new_prompt
    assert mock_llm.chat.completions.create.called
    call_args = mock_llm.chat.completions.create.call_args
    meta_prompt_content = call_args.kwargs["messages"][0]["content"]
    assert "Magnitude Calibration Diagnosis" in meta_prompt_content


@pytest.mark.asyncio
async def test_run_daily_autoresearch_ratchet():
    mock_supabase = MagicMock()

    eval_predictions = [
        {"is_correct": True, "brier_score": 0.04},
        {"is_correct": True, "brier_score": 0.04},
        {"is_correct": True, "brier_score": 0.04},
    ]

    active_prompt = [
        {
            "variant_tag": "daily-active-1",
            "prompt_name": "DAILY_PREDICTOR_PROMPT",
            "prompt_content": "Active prompt content",
            "status": "active",
        }
    ]

    mock_table = MagicMock()

    def mock_table_select(table_name):
        mock_chain = MagicMock()
        # Allow arbitrary chaining of eq, gte, lte, select, in_, neq, order, limit
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.gte.return_value = mock_chain
        mock_chain.lte.return_value = mock_chain
        mock_chain.in_.return_value = mock_chain
        mock_chain.neq.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain

        if table_name == "daily_predictions":
            mock_chain.execute.return_value.data = eval_predictions
        elif table_name == "prompt_experiments":
            mock_chain.execute.return_value.data = active_prompt
            mock_chain.insert = mock_table.insert
            mock_chain.update = mock_table.update
        return mock_chain

    mock_supabase.table.side_effect = mock_table_select

    mock_llm = MagicMock()
    mock_llm.chat.completions.create.return_value = MagicMock(new_prompt="Mutated intraday strategy instructions")

    with (
        patch("tasks.daily_autoresearch.get_supabase_client", return_value=mock_supabase),
        patch("tasks.daily_autoresearch.get_deepseek_client", return_value=mock_llm),
        patch("tasks.daily_autoresearch.close_client", new_callable=AsyncMock),
    ):
        await run_daily_autoresearch()
        assert mock_table.insert.called
        # Should insert for both models
        assert mock_table.insert.call_count >= 2


def test_fetch_autoresearch_context():
    from tasks.daily_autoresearch import fetch_autoresearch_context

    mock_supabase = MagicMock()
    mock_news = [
        {
            "date": "2026-08-10T12:00:00Z",
            "sender": "Macro Daily",
            "subject": "Tech capex accelerates",
            "content": "Full content of tech acceleration...",
        }
    ]
    mock_events = [
        {
            "id": "evt-1",
            "content": "Fed signals rate pause at Jackson Hole",
            "created_at": "2026-08-10T14:00:00Z",
            "memory_type": "MARKET_EVENT",
            "metadata": {"tags": ["fed", "rates"]},
        }
    ]
    mock_concepts = [
        {
            "concept_name": "AI Infrastructure Surge",
            "velocity_score": 4.5,
            "mention_count": 12,
            "last_mention_at": "2026-08-10T10:00:00Z",
        }
    ]

    def mock_table_select(table_name):
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.gte.return_value = mock_chain
        mock_chain.lte.return_value = mock_chain
        mock_chain.in_.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain

        if table_name == "newsletter_snapshots":
            mock_chain.execute.return_value.data = mock_news
        elif table_name == "memories":
            mock_chain.execute.return_value.data = mock_events
        elif table_name == "concept_metrics":
            mock_chain.execute.return_value.data = mock_concepts
        else:
            mock_chain.execute.return_value.data = []
        return mock_chain

    mock_supabase.table.side_effect = mock_table_select

    context = fetch_autoresearch_context(mock_supabase, "2026-08-08", "2026-08-12")
    assert "2026-08-10" in context["daily_events"]
    assert "Tech capex accelerates" in context["daily_events"]["2026-08-10"]["newsletters"][0]
    assert "Fed signals rate pause" in context["daily_events"]["2026-08-10"]["events"][0]
    assert len(context["active_concepts"]) == 1
    assert "AI Infrastructure Surge" in context["active_concepts"][0]


def test_compute_magnitude_postmortem_summary_with_macro():
    from tasks.daily_autoresearch import compute_magnitude_postmortem_summary

    predictions = [
        {
            "target_date": "2026-08-10",
            "predicted_direction": "UP",
            "expected_return_pct": 0.20,
            "open_price": 500.0,
            "high_price": 506.0,
            "low_price": 499.0,
            "close_price": 505.0,
            "is_correct": True,
            "intraday_hit": True,
            "brier_score": 0.04,
        }
    ]
    macro_context = {
        "daily_events": {
            "2026-08-10": {
                "newsletters": ["Macro Daily: Tech capex surge"],
                "events": ["Fed dovish tone"],
            }
        },
        "active_concepts": ["AI Infrastructure Surge (Velocity: 4.5)"],
    }

    summary = compute_magnitude_postmortem_summary(predictions, macro_context=macro_context)
    assert "Key Catalysts" in summary
    assert "Tech capex surge" in summary
    assert "ACTIVE THEMATIC CONCEPTS & MARKET PLAYBOOKS" in summary
    assert "AI Infrastructure Surge" in summary
