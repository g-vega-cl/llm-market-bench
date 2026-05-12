"""Weekly evaluation orchestrator.

Gathers trading data, computes metrics, and formats the structured report
that is fed to the auto-research LLM. Returns both the markdown report and
the composite-score dict so the runner does not have to parse markdown.
"""

import json
import logging
from datetime import date, timedelta

from core.config import AUTORESEARCH_EXPERIMENT_OWNER_IDS, OPENAI_MODEL, ANTHROPIC_MODEL
from core.db import get_async_supabase_client

from .metrics import compute_wall_street_metrics, compute_composite_score, _spy_returns
from .decision_quality import compute_decision_quality
from .prompt_store import get_active_prompt, get_previous_variants, get_baseline_metrics
from .window import get_week_window

logger = logging.getLogger("engine")

CONTROL_OWNER_IDS = frozenset([OPENAI_MODEL, ANTHROPIC_MODEL])


async def _get_market_regime_summary(week_start: date, week_end: date) -> str:
    """Brief market-regime summary from available data.

    VIXY is the volatility ETF tracked in `price_history` (see
    `core.macro_tracker`). The legacy index ticker "VIX" is never stored.
    """
    summary_parts = []
    sb_client = await get_async_supabase_client()

    try:
        vix_res = await (
            sb_client.table("price_history")
            .select("price")
            .eq("ticker", "VIXY")
            .gte("fetched_at", (week_start - timedelta(days=30)).isoformat())
            .lte("fetched_at", week_end.isoformat())
            .order("fetched_at")
            .execute()
        )
        if vix_res.data and len(vix_res.data) >= 2:
            prev_vix = float(vix_res.data[-2].get("price") or 0)
            curr_vix = float(vix_res.data[-1].get("price") or 0)
            if prev_vix > 0:
                vix_change = (curr_vix - prev_vix) / prev_vix * 100
                summary_parts.append(f"VIXY: {curr_vix:.1f} (change: {vix_change:+.1f}% WoW)")
    except Exception as e:
        logger.debug("VIXY regime lookup failed: %s", e)

    try:
        spy_res = await (
            sb_client.table("price_history")
            .select("price")
            .eq("ticker", "SPY")
            .gte("fetched_at", week_start.isoformat())
            .lte("fetched_at", week_end.isoformat())
            .order("fetched_at")
            .execute()
        )
        if spy_res.data and len(spy_res.data) >= 2:
            spy_start = float(spy_res.data[0].get("price") or 0)
            spy_end = float(spy_res.data[-1].get("price") or 0)
            if spy_start > 0:
                spy_change = (spy_end - spy_start) / spy_start * 100
                summary_parts.append(f"SPY weekly return: {spy_change:+.2f}%")
    except Exception as e:
        logger.debug("SPY regime lookup failed: %s", e)

    if not summary_parts:
        summary_parts.append("No regime data available for this week.")

    return " | ".join(summary_parts)


def _check_stagnation(previous_variants: list[dict]) -> tuple[bool, str]:
    """Check if composite score has stagnated for 2+ weeks."""
    recent = [v for v in previous_variants if v.get("metrics") and isinstance(v["metrics"], dict)]
    if len(recent) < 2:
        return False, ""

    metrics_list = []
    for v in recent[:3]:
        m = v["metrics"]
        if isinstance(m, str):
            try:
                m = json.loads(m)
            except (json.JSONDecodeError, TypeError):
                continue
        comp = m.get("composite")
        if comp is not None:
            metrics_list.append(float(comp))

    if len(metrics_list) >= 2:
        avg = sum(metrics_list) / len(metrics_list)
        # Floor check: if average composite is below 0.05, we're stuck at the floor
        if avg < 0.05:
            return True, (
                f"STAGNATION: average composite score ({avg:.3f}) is at floor (< 0.05). "
                "A RADICAL variant is strongly recommended."
            )
        if avg > 0:
            pct_range = (max(metrics_list) - min(metrics_list)) / avg
            if pct_range < 0.05:
                return True, f"STAGNATION: composite score has been within {pct_range:.1%} for {len(metrics_list)} weeks. A RADICAL variant is strongly recommended."

    return False, ""


def _format_metrics_table(label: str, metrics: dict) -> str:
    return (
        f"**{label}**\n"
        f"  Sharpe: {metrics.get('sharpe', 0):.3f} | "
        f"Sortino: {metrics.get('sortino', 0):.3f} | "
        f"Max DD: {metrics.get('max_drawdown', 0):.1%} | "
        f"Profit Factor: {metrics.get('profit_factor', 0):.2f} | "
        f"Info Ratio: {metrics.get('info_ratio', 0):.3f}\n"
        f"  Trading Days: {metrics.get('num_trading_days', 0)} | "
        f"Total Return: {metrics.get('total_return_pct', 0):.2f}%"
    )


def _format_decision_quality(dq: dict) -> str:
    lines = [
        "**Decision Quality**",
        f"  Concordance: {dq.get('concordance', 0):.2f} | "
        f"Conviction Calibration: {dq.get('conviction_calibration', 0):.2f} | "
        f"Rejection Rate: {dq.get('rejection_rate', 0):.1%}",
        f"  Total Decisions: {dq.get('total_decisions', 0)} | "
        f"Total Trades: {dq.get('total_trades', 0)}",
    ]
    mistakes = dq.get("mistake_patterns", [])
    if mistakes:
        lines.append("  Top Mistake Patterns:")
        for reason, count in mistakes[:5]:
            lines.append(f"    - {reason}: {count}x")
    return "\n".join(lines)


def _format_samples(dq: dict) -> str:
    lines = []
    wins = dq.get("sample_wins", [])
    losses = dq.get("sample_losses", [])
    rejects = dq.get("sample_rejections", [])

    if wins:
        lines.append("**Best Wins:**")
        for w in wins:
            lines.append(f"  - {w['ticker']}: P&L ${w['pnl']:.2f} | Reasoning: {w['reasoning'][:200]}")

    if losses:
        lines.append("**Worst Losses:**")
        for loss in losses:
            lines.append(f"  - {loss['ticker']}: P&L ${loss['pnl']:.2f} | Reasoning: {loss['reasoning'][:200]}")

    if rejects:
        lines.append("**Typical Rejections:**")
        for r in rejects:
            lines.append(f"  - {r['ticker']} ({r['signal']}): {r['status']} | Reasoning: {r['reasoning'][:200]}")

    return "\n".join(lines)


def _format_previous_variants(variants: list[dict]) -> str:
    if not variants:
        return "No previous variants."

    lines = ["**Previous Prompt Variants:**"]
    for v in variants[:5]:
        tag = v.get("variant_tag", "?")
        exp_type = v.get("experiment_type", "?")
        desc = v.get("change_description", "?")
        m = v.get("metrics", {})
        if isinstance(m, str):
            try:
                m = json.loads(m)
            except (json.JSONDecodeError, TypeError):
                m = {}
        comp = m.get("composite", "?")
        lines.append(f"  - {tag} ({exp_type}): {desc} | Score: {comp}")
    return "\n".join(lines)


async def evaluate_week(
    week_start: date | None = None,
    week_end: date | None = None,
) -> tuple[str, dict]:
    """Gather all data for the past week and format the evaluation report.

    If week_start/week_end are not provided, they are computed from the
    most recent complete Mon-Sun window (via get_week_window).

    Returns:
        (report_markdown, composite_metrics) — the markdown report ready for
        the auto-research LLM, plus the structured composite dict the runner
        persists alongside the new variant.
    """
    if week_start is None or week_end is None:
        week_start, week_end = get_week_window()

    logger.info("Evaluating week %s to %s", week_start, week_end)

    current_prompt = await get_active_prompt()
    from core.llm import prompts
    if not current_prompt:
        current_prompt = prompts.CORE_ANALYSIS_SYSTEM_PROMPT

    # Fetch SPY returns once — same benchmark for both agent groups.
    sb_client = await get_async_supabase_client()
    spy_returns = await _spy_returns(sb_client, week_start, week_end)

    exp_metrics = await compute_wall_street_metrics(
        AUTORESEARCH_EXPERIMENT_OWNER_IDS, week_start, week_end, spy_returns=spy_returns,
    )
    ctrl_metrics = await compute_wall_street_metrics(
        CONTROL_OWNER_IDS, week_start, week_end, spy_returns=spy_returns,
    )

    # Concordance: did experiment agents outperform control on equity change?
    exp_return = exp_metrics.get("total_return_pct", 0)
    ctrl_return = ctrl_metrics.get("total_return_pct", 0)
    if exp_return > ctrl_return:
        concordance = 1.0
    elif abs(exp_return - ctrl_return) < 0.01:
        concordance = 0.5  # Within 1 bp — effectively tied.
    else:
        concordance = 0.0

    dq = await compute_decision_quality(AUTORESEARCH_EXPERIMENT_OWNER_IDS, week_start, week_end)
    composite = compute_composite_score(
        exp_metrics,
        concordance=concordance,
        conviction=dq["conviction_calibration"],
        regime_awareness=dq["regime_awareness"],
    )
    previous = await get_previous_variants(limit=5)
    _, stagnation_msg = _check_stagnation(previous)

    regime = await _get_market_regime_summary(week_start, week_end)

    baseline_metrics = await get_baseline_metrics()
    baseline_text = ""
    baseline_composite = 0.0
    if baseline_metrics:
        if isinstance(baseline_metrics, str):
            try:
                baseline_metrics = json.loads(baseline_metrics)
            except (json.JSONDecodeError, TypeError):
                baseline_metrics = {}
        baseline_composite = float(baseline_metrics.get("composite", 0))
        baseline_text = f"**Baseline Composite Score:** {baseline_composite}"
    # Expose baseline for the runner's activation gate.
    composite["baseline_composite"] = baseline_composite

    report_parts = [
        "# Weekly Trading Performance Report",
        f"**Period:** {week_start.isoformat()} to {week_end.isoformat()}",
        "",
        "## Composite Score",
        f"**This Week:** {composite['composite']}",
        f"  Sharpe: {composite['sharpe_normalized']} | Sortino: {composite['sortino_normalized']} | "
        f"Drawdown: {composite['drawdown_normalized']} | Profit Factor: {composite['profit_factor_normalized']}",
        f"  Concordance: {composite['concordance']} | Conviction: {composite['conviction_calibration']}",
        baseline_text,
        "",
        "## Wall Street Metrics",
        _format_metrics_table("Experiment Agents (Gemini + DeepSeek)", exp_metrics),
        _format_metrics_table("Control Agents (OpenAI + Claude - baseline prompt)", ctrl_metrics),
        "",
        "## Decision Quality (Experiment Agents)",
        _format_decision_quality(dq),
        "",
        "## Sample Trades",
        _format_samples(dq),
        "",
        "## Market Regime",
        regime,
        "",
        _format_previous_variants(previous),
        "",
        "## Current Prompt (to be improved)",
        "```",
        current_prompt,
        "```",
        "",
    ]

    if stagnation_msg:
        report_parts.append(f"## STAGNATION ALERT\n{stagnation_msg}\n")

    report_parts.append(
        "## Instructions\n"
        "Analyze the performance data above and propose a new CORE_ANALYSIS_SYSTEM_PROMPT. "
        "Return ONLY valid JSON with new_prompt_text, change_description, experiment_type, "
        "research_reasoning, and confidence."
    )

    return "\n".join(report_parts), composite
