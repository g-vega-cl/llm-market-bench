"""TDD tests for weekly ingestion and consensus log audit, sampling, and summarization."""

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.audit.runner import (
    analyze_recent_logs,
    extract_log_summary,
    select_sampled_runs,
)


def test_select_sampled_runs_prioritizes_errors():
    """Verify that select_sampled_runs keeps the latest anchor and prioritizes runs with errors."""
    mock_runs = [
        {"run_id": "run_0_latest", "log_blob": "INFO: All systems nominal. 0 errors."},
        {"run_id": "run_1_clean", "log_blob": "INFO: Clean run here."},
        {"run_id": "run_2_error", "log_blob": "ERROR: Gmail IMAP socket timeout\nWARNING: retry failed"},
        {"run_id": "run_3_clean", "log_blob": "INFO: Another normal run."},
        {
            "run_id": "run_4_critical",
            "log_blob": "CRITICAL: Database disconnect\nTraceback (most recent call last):\n  File 'a.py': error",
        },
        {"run_id": "run_5_clean", "log_blob": "INFO: Clean routine check."},
    ]

    selected = select_sampled_runs(mock_runs, sample_size=3)

    assert len(selected) == 3
    # Anchor must be the latest run
    assert selected[0]["run_id"] == "run_0_latest"

    # The other 2 selected runs must be the error/critical ones
    selected_ids = {r["run_id"] for r in selected}
    assert "run_4_critical" in selected_ids
    assert "run_2_error" in selected_ids


def test_select_sampled_runs_clean_fallback():
    """Verify that select_sampled_runs samples distinct runs when all candidates are clean."""
    mock_runs = [{"run_id": f"run_{i}", "log_blob": f"INFO: Everything normal in run {i}"} for i in range(8)]

    selected = select_sampled_runs(mock_runs, sample_size=3)

    assert len(selected) == 3
    assert selected[0]["run_id"] == "run_0"

    selected_ids = [r["run_id"] for r in selected]
    assert len(set(selected_ids)) == 3  # All distinct
    for sid in selected_ids[1:]:
        assert sid in [f"run_{i}" for i in range(1, 8)]


def test_select_sampled_runs_fewer_than_sample_size():
    """Verify that select_sampled_runs gracefully handles lists smaller than sample_size."""
    mock_runs = [
        {"run_id": "run_0", "log_blob": "INFO: Only run 0"},
        {"run_id": "run_1", "log_blob": "INFO: Only run 1"},
    ]

    selected = select_sampled_runs(mock_runs, sample_size=3)
    assert len(selected) == 2
    assert [r["run_id"] for r in selected] == ["run_0", "run_1"]


def test_extract_log_summary_preserves_errors_and_metrics():
    """Verify that extract_log_summary truncates noise while strictly preserving errors, tracebacks, and summaries."""
    noise_line = "[2026-09-09 12:00:00] DEBUG: checking quote AAPL 250.00\n"
    repetitive_noise = noise_line * 1000  # ~56,000 characters

    full_log = (
        repetitive_noise
        + "[2026-09-09 12:01:00] INFO: Successfully ingested 5 newsletters: 2 from Morning Brew, 3 from Bloomberg\n"
        + "[2026-09-09 12:02:00] WARNING: SEMANTIC FRAGILITY ALERT: Found message(s) from 'bad_sender' but yielded 0 valid snapshots.\n"
        + repetitive_noise
        + "[2026-09-09 12:03:00] INFO: Consensus reached on semantic event group: 'Fed Rate Cut Expectations'\n"
        + "[2026-09-09 12:04:00] ERROR: Background consensus/momentum failed: rate limit exceeded\n"
        + "Traceback (most recent call last):\n  File 'main.py', line 50\nValueError: test error\n"
        + repetitive_noise
        + "[2026-09-09 12:05:00] INFO: Processing complete: 3 saved, 1 rejected.\n"
    )

    summary = extract_log_summary(full_log, max_chars=8000)

    assert len(summary) <= 8000
    assert "Successfully ingested 5 newsletters" in summary
    assert "SEMANTIC FRAGILITY ALERT" in summary
    assert "Consensus reached on semantic event group" in summary
    assert "Background consensus/momentum failed" in summary
    assert "Traceback (most recent call last)" in summary
    assert "ValueError: test error" in summary
    assert "Processing complete: 3 saved, 1 rejected" in summary


@pytest.mark.asyncio
async def test_analyze_recent_logs_queries_7_days_and_writes_summary(tmp_path):
    """Verify that analyze_recent_logs queries the 7-day lookback window and writes to GITHUB_STEP_SUMMARY."""
    mock_supabase = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_gte = MagicMock()
    mock_order = MagicMock()

    mock_supabase.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.gte.return_value = mock_gte
    mock_gte.order.return_value = mock_order

    mock_order.execute.return_value = MagicMock(
        data=[
            {
                "run_id": "run_2026-09-09_15-30-00",
                "run_date": "2026-09-09",
                "log_blob": "INFO: Successfully ingested 4 newsletters.\nERROR: MiniMax provider timeout.",
            },
            {
                "run_id": "run_2026-09-08_11-35-00",
                "run_date": "2026-09-08",
                "log_blob": "INFO: Clean run.",
            },
        ]
    )

    mock_analysis_result = (
        "[\n"
        "  {\n"
        '    "title": "MiniMax Provider Timeout",\n'
        '    "severity": "HIGH",\n'
        '    "suggestion": "Check MiniMax API status and increase timeout",\n'
        '    "run_id": "run_2026-09-09_15-30-00"\n'
        "  }\n"
        "]"
    )

    summary_file = tmp_path / "step_summary.md"

    with (
        patch("core.audit.runner.analyze_log_blob", new=AsyncMock(return_value=mock_analysis_result)),
        patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}),
    ):
        finding_count = await analyze_recent_logs(mock_supabase, "audit-20260909-120000")

    assert finding_count == 1

    # Verify query used 7-day cutoff (approximately 7 days ago in ISO format)
    cutoff_arg = mock_select.gte.call_args[0][1]
    cutoff_dt = datetime.fromisoformat(cutoff_arg)
    now = datetime.now(UTC)
    time_diff = now - cutoff_dt
    assert 6.9 <= time_diff.total_seconds() / 86400 <= 7.1

    # Verify GITHUB_STEP_SUMMARY was written
    assert summary_file.exists()
    content = summary_file.read_text()
    assert "Weekly Ingestion & Consensus Audit" in content
    assert "MiniMax Provider Timeout" in content
