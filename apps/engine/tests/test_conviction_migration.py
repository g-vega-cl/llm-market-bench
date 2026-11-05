"""Guard tests for the conviction scoring migration.

These assert the structural contract that the Python scoring code depends on:
the three prediction tables persist a ``conviction_score``, the sector arena
persists a separate ``worst_confidence``, and the leaderboard RPC no longer
pays a model for stating high confidence regardless of accuracy.
"""

import os
import re


def _get_migration_dir() -> str:
    for candidate in ["../../supabase/migrations", "supabase/migrations"]:
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError("Could not find supabase/migrations directory")


def _migration_files() -> list[tuple[str, str]]:
    directory = _get_migration_dir()
    result = []
    for filename in sorted(f for f in os.listdir(directory) if f.endswith(".sql")):
        with open(os.path.join(directory, filename), encoding="utf-8") as handle:
            result.append((filename, handle.read()))
    return result


def _normalise(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).lower()


def _latest_leaderboard_definition() -> tuple[str, str]:
    candidates = [(name, content) for name, content in _migration_files() if "get_llm_leaderboard_metrics" in content]
    assert candidates, "No migration defines get_llm_leaderboard_metrics"
    return candidates[-1]


def test_conviction_score_column_on_every_prediction_table():
    sql = _normalise("\n".join(content for _, content in _migration_files()))

    for table in ("daily_predictions", "sector_predictions", "earnings_predictions"):
        assert re.search(
            rf"alter table (public\.)?{table} .*?add column if not exists conviction_score",
            sql,
        ), f"{table} is missing a conviction_score column"


def test_sector_predictions_store_worst_confidence_separately():
    sql = _normalise("\n".join(content for _, content in _migration_files()))

    assert re.search(
        r"alter table (public\.)?sector_predictions .*?add column if not exists worst_confidence",
        sql,
    ), "sector_predictions is missing worst_confidence"


def test_latest_leaderboard_rpc_scores_conviction():
    filename, content = _latest_leaderboard_definition()
    sql = _normalise(content)

    assert "conviction_score numeric" in sql, f"{filename} must expose conviction_score"
    assert "from public.daily_predictions" in sql, f"{filename} must source conviction from daily_predictions"
    # Conviction points are 100 * ln(2p) / 100 * ln(2 - 2p).
    assert "ln(" in sql, f"{filename} must compute the log score"
    assert "tanh(" in sql, f"{filename} must squash conviction onto the 0-100 scale"


def test_leaderboard_no_longer_rewards_raw_confidence():
    """The old RPC paid 0.3 * avg_confidence regardless of correctness."""
    filename, content = _latest_leaderboard_definition()
    sql = _normalise(content)

    forbidden = [
        "0.3 * coalesce(mdec.avg_conf, 0.0)",
        "coalesce(mdec.avg_conf, 0.0), 2) as reasoning_quality_score",
    ]
    for pattern in forbidden:
        assert pattern not in sql, f"{filename} still scores raw average confidence via '{pattern}'"


def test_leaderboard_keeps_confidence_as_informational_column():
    """Average confidence stays visible; it just stops earning points."""
    _, content = _latest_leaderboard_definition()
    assert "average_confidence" in _normalise(content)
