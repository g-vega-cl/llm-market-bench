"""Hermetic unit tests for local_autoresearch.reporting."""

import os
import tempfile

from apps.engine.local_autoresearch.reporting import (
    render_terminal_dashboard,
    update_dashboard_artifact,
)


def test_render_terminal_dashboard_basic():
    history = [
        {
            "iteration": 0,
            "variant_tag": "clean-start-1234",
            "train_score": 45.0,
            "test_score": 46.0,
            "overfit_penalty": 0.0,
            "effective_score": 46.0,
            "is_baseline_beat": True,
        },
        {
            "iteration": 1,
            "variant_tag": "qwen-jev-5678",
            "train_score": 40.0,
            "test_score": 30.0,
            "overfit_penalty": 10.0,
            "effective_score": 25.0,
            "is_baseline_beat": False,
        },
    ]
    baseline = {"variant_tag": "clean-start-1234", "effective_score": 46.0}

    dashboard = render_terminal_dashboard(history, baseline)
    assert "LOCAL AUTORESEARCH EXPERIMENT SCOREBOARD" in dashboard
    assert "clean-start-123" in dashboard
    assert "qwen-jev-5678" in dashboard
    assert "Current Best Baseline: clean-start-1234" in dashboard
    assert "Ratchet Score Trajectory" in dashboard


def test_render_terminal_dashboard_with_weekly_breakdown():
    history = [
        {
            "iteration": 0,
            "variant_tag": "clean-start-1234",
            "train_score": 45.0,
            "test_score": 46.0,
            "overfit_penalty": 0.0,
            "effective_score": 46.0,
            "is_baseline_beat": True,
        }
    ]
    baseline = {"variant_tag": "clean-start-1234", "effective_score": 46.0}
    weekly_breakdown = {
        "2026-W05": {
            "split": "TRAIN",
            "days_count": 5,
            "accuracy_pct": 60.0,
            "traded_win_rate_pct": 60.0,
            "score": 52.4,
        },
        "2026-W06": {
            "split": "TEST",
            "days_count": 5,
            "accuracy_pct": 80.0,
            "traded_win_rate_pct": 80.0,
            "score": 71.2,
        },
    }

    dashboard = render_terminal_dashboard(history, baseline, latest_weekly_breakdown=weekly_breakdown)
    assert "Latest Weekly Iterations Breakdown" in dashboard
    assert "2026-W05" in dashboard
    assert "2026-W06" in dashboard
    assert "TRAIN" in dashboard
    assert "TEST" in dashboard


def test_update_dashboard_artifact():
    history = [
        {
            "iteration": 0,
            "variant_tag": "clean-start-1234",
            "train_score": 45.0,
            "test_score": 46.0,
            "effective_score": 46.0,
            "is_baseline_beat": True,
            "hypothesis": "Clean sheet start",
        }
    ]
    baseline = {
        "variant_tag": "clean-start-1234",
        "effective_score": 46.0,
        "criteria_up": "SPY >= Open",
        "criteria_down": "SPY < Open",
        "min_confidence": 55.0,
        "manifest": {"selected_newsletters": ["The Kobeissi Letter"], "include_currency_uup": False},
    }
    weekly_breakdown = {
        "2026-W05": {
            "split": "TRAIN",
            "days_count": 5,
            "accuracy_pct": 60.0,
            "traded_win_rate_pct": 60.0,
            "score": 52.4,
        }
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        art_path = os.path.join(tmpdir, "report.md")
        update_dashboard_artifact(history, baseline, art_path, latest_weekly_breakdown=weekly_breakdown)
        assert os.path.exists(art_path)
        with open(art_path, encoding="utf-8") as f:
            content = f.read()
        assert "# Local Autoresearch Session Report" in content
        assert "clean-start-1234" in content
        assert "The Kobeissi Letter" in content
        assert "Latest Weekly Iteration Breakdown" in content
        assert "2026-W05" in content
        assert "```mermaid" in content
