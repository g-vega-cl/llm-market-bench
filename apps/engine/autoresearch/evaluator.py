"""Weekly evaluation orchestrator.

Gathers trading data, computes the single score (risk-adjusted return vs SPY),
and formats a minimal report for the auto-research LLM. Returns both the
markdown report and the score dict so the runner does not parse markdown.
"""

import logging
from datetime import date

from core.config import AUTORESEARCH_EXPERIMENT_OWNER_IDS, OPENAI_MODEL, ANTHROPIC_MODEL
from core.db import get_async_supabase_client

from .metrics import compute_wall_street_metrics, _spy_returns, compute_score
from .prompt_store import get_active_prompt, get_previous_variants, get_all_time_baseline
from .window import get_week_window

logger = logging.getLogger("engine")

CONTROL_OWNER_IDS = frozenset([OPENAI_MODEL, ANTHROPIC_MODEL])


def _format_variants(variants: list[dict], baseline_score: float | None = None) -> str:
    if not variants:
        return "No previous variants."

    lines = ["**Recent Prompt Experiments:**"]
    for v in variants[:5]:
        tag = v.get("variant_tag", "?")
        exp_type = v.get("experiment_type", "?")
        desc = v.get("change_description", "?")
        m = v.get("metrics", {})
        if isinstance(m, str):
            import json
            try:
                m = json.loads(m)
            except (json.JSONDecodeError, TypeError):
                m = {}
        score = m.get("score")
        score_str = f"{score}" if score is not None else "?"

        status = ""
        if score is not None and baseline_score is not None:
            if score >= baseline_score:
                status = " [NEW BEST]" if score > baseline_score else " [TIED BEST]"
            else:
                status = " [FAILED TO BEAT BASELINE]"

        lines.append(f"  - {tag} ({exp_type}): {desc} | Score: {score_str}{status}")
    return "\n".join(lines)


async def evaluate_week(
    week_start: date | None = None,
    week_end: date | None = None,
) -> tuple[str, dict, str | None]:
    """Gather all data for the past week and format the evaluation report.

    If week_start/week_end are not provided, they are computed from the
    most recent complete Mon-Sun window.

    Returns:
        (report_markdown, metrics) — minimal report for the meta-researcher LLM,
        plus the score dict the runner persists alongside the new variant.
    """
    if week_start is None or week_end is None:
        week_start, week_end = get_week_window()

    logger.info("Evaluating week %s to %s", week_start, week_end)

    current_prompt = await get_active_prompt()
    if not current_prompt:
        from core.llm import prompts
        current_prompt = prompts.CORE_ANALYSIS_SYSTEM_PROMPT

    # Fetch SPY returns once — benchmark for the score.
    sb_client = await get_async_supabase_client()
    spy_returns = await _spy_returns(sb_client, week_start, week_end)

    # Compute SPY return from daily returns.
    spy_return_pct = 0.0
    if spy_returns:
        cumulative = 1.0
        for r in spy_returns:
            cumulative *= (1 + r)
        spy_return_pct = (cumulative - 1) * 100

    # Experiment group metrics.
    exp_metrics = await compute_wall_street_metrics(
        AUTORESEARCH_EXPERIMENT_OWNER_IDS, week_start, week_end, spy_returns=spy_returns,
    )

    # Control group metrics (reference only).
    ctrl_metrics = await compute_wall_street_metrics(
        CONTROL_OWNER_IDS, week_start, week_end, spy_returns=spy_returns,
    )

    # Compute the single score.
    score_result = compute_score(
        portfolio_return_pct=exp_metrics.get("total_return_pct", 0),
        spy_return_pct=spy_return_pct,
        max_drawdown_pct=exp_metrics.get("max_drawdown", 0) * 100,
    )

    previous = await get_previous_variants(limit=5)
    baseline_variant = await get_all_time_baseline()

    baseline_score = None
    baseline_prompt = None
    if baseline_variant:
        baseline_prompt = baseline_variant.get("prompt_content")
        m = baseline_variant.get("metrics", {})
        if isinstance(m, str):
            import json
            try:
                m = json.loads(m)
            except (json.JSONDecodeError, TypeError):
                m = {}
        baseline_score = m.get("score")

    # Build minimal report.
    baseline_line = ""
    if baseline_score is not None:
        delta = score_result["score"] - baseline_score
        baseline_line = (
            f"Baseline: {baseline_score} (best so far)  "
            f"(Δ: {delta:+.4f} vs baseline)"
        )
    else:
        baseline_line = "Baseline: N/A (first week, no baseline yet)"

    report_parts = [
        "# Weekly Performance",
        f"Score: {score_result['score']}  "
        f"(portfolio: {exp_metrics.get('total_return_pct', 0):+.1f}% | "
        f"SPY: {spy_return_pct:+.1f}% | "
        f"drawdown: -{score_result['max_drawdown']:.1f}%)",
        baseline_line,
        f"Formula: ({exp_metrics.get('total_return_pct', 0):.1f} - {spy_return_pct:.1f}) - "
        f"({score_result['max_drawdown']:.1f} × 0.3) = {exp_metrics.get('total_return_pct', 0) - spy_return_pct:.1f} - "
        f"{score_result['max_drawdown'] * 0.3:.1f} = {score_result['score']}",
        "",
        "# Control Reference",
        f"Control agents (OpenAI + Claude on baseline): "
        f"{ctrl_metrics.get('total_return_pct', 0):+.1f}% return, "
        f"-{ctrl_metrics.get('max_drawdown', 0) * 100:.1f}% drawdown",
        "",
        _format_variants(previous, baseline_score=baseline_score),
        "",
        "# Baseline Prompt (All-Time Best)",
        "This is the prompt that achieved the highest score so far. Use this as your foundation.",
        "```",
        baseline_prompt or "No baseline prompt yet.",
        "```",
        "",
        "# Latest Experiment Prompt (Just Evaluated)",
        "This is the prompt that produced the score at the top of this report.",
        "```",
        current_prompt,
        "```",
        "",
        "# Instructions",
        "Propose a new CORE_ANALYSIS_SYSTEM_PROMPT. Return ONLY valid JSON with "
        "new_prompt_text, change_description, experiment_type, research_reasoning, "
        "and confidence.",
    ]

    return "\n".join(report_parts), score_result, baseline_variant.get("variant_tag") if baseline_variant else None
