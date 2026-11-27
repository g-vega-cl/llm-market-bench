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


def test_latest_leaderboard_removes_verifier_and_fixes_win_rate_consistency_and_unified_competitors():
    """Latest leaderboard RPC must drop verifier scoring, fix win_rate/consistency, and unify LLMs + sys + user bots."""
    filename, content = _latest_leaderboard_definition()
    sql = _normalise(content)

    # 1. No verifier approval rate weighting or output column
    assert "verifier_approval_rate" not in sql, f"{filename} must remove verifier_approval_rate"
    assert "verifier_app_rate" not in sql, f"{filename} must not weight verifier_app_rate"

    # 2. Win rate counts closed exit trades (SELL/COVER) rather than dividing by all BUY rows, with open-position fallback
    assert "in ('sell', 'cover')" in sql, f"{filename} must restrict realized win rate to SELL/COVER exit trades"
    assert "from public.position_pnl" in sql, f"{filename} must fall back to open positions when closed trades = 0"

    # 3. Consistency measures daily equity return positivity, not API uptime
    assert "0.7 * coalesce(mdec.api_succ_rate" not in sql, f"{filename} must not use API uptime as consistency_score"
    assert "lag(" in sql and "from public.portfolio_performance" in sql, (
        f"{filename} must compute consistency_score from portfolio_performance daily returns"
    )

    # 4. Unified competitors: active portfolios (LLMs + sys-*) + all non-archived user bots
    assert "from public.strategy_recipes" in sql, f"{filename} must include user bots from strategy_recipes"
    assert "entity_type" in sql, f"{filename} must return entity_type"
    assert "sys-daily-spy-minimax-m3" in sql, f"{filename} must exclude archived portfolios"

    # 5. Materialized user bot stats + indexes + server-side pagination + non-LLM neutrality
    assert "public.user_bot_leaderboard_stats" in sql, (
        f"{filename} must read pre-materialized user_bot_leaderboard_stats instead of unpacking JSONB"
    )
    assert "jsonb_array_elements" not in sql, f"{filename} must not unpack JSONB arrays on request path"
    assert "upper(t.signal) = 'short'" in sql, f"{filename} must include open SHORT lots in open-position win rate"
    assert "get_leaderboard_page" in sql, f"{filename} must expose STABLE server-side get_leaderboard_page RPC"
    assert "create index if not exists idx_decisions_created_at" in sql, f"{filename} must index decisions(created_at)"


def test_leaderboard_exposes_up_day_counts_behind_consistency():
    """Consistency is a smoothed up-day rate; the raw counts must be exposed for the UI."""
    filename, content = _latest_leaderboard_definition()
    sql = _normalise(content)

    assert "up_days bigint" in sql, f"{filename} must return up_days"
    assert "active_days bigint" in sql, f"{filename} must return active_days"
    assert "pos_days" in sql, f"{filename} must count positive equity sessions for up_days"
    assert "get_leaderboard_page" in sql, f"{filename} must redefine get_leaderboard_page"
    assert re.search(r"o\.up_days", sql), f"{filename} must pass up_days through the page RPC"
    assert re.search(r"o\.active_days", sql), f"{filename} must pass active_days through the page RPC"

    stats_sql = _normalise(
        "\n".join(content for _, content in _migration_files() if "user_bot_leaderboard_stats" in content)
    )
    assert "add column if not exists up_days" in stats_sql, "user_bot_leaderboard_stats must store up_days"
    assert "add column if not exists active_days" in stats_sql, (
        "user_bot_leaderboard_stats must store active_days"
    )


def test_strategy_recipes_default_public_migration_exists():
    """All non-archived user bots must be public by default and backfilled."""
    sql = _normalise("\n".join(content for _, content in _migration_files()))
    assert "alter table public.strategy_recipes alter column is_public set default true" in sql
    assert "update public.strategy_recipes set is_public = true" in sql
