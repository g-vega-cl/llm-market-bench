"""Weekly evaluation orchestrator.

Gathers trading data, computes the single score (risk-adjusted return vs SPY),
and formats a minimal report for the auto-research LLM. Returns both the
markdown report and the score dict so the runner does not parse markdown.
"""

import logging
from datetime import date

from core.config import ANTHROPIC_MODEL, AUTORESEARCH_EXPERIMENT_OWNER_IDS, OPENAI_MODEL
from core.db import get_async_supabase_client

from .metrics import _spy_returns, compute_score, compute_wall_street_metrics
from .prompt_store import get_active_prompt, get_all_time_baseline, get_previous_variants
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


async def _fetch_actual_bond_yield(week_start: date, week_end: date) -> float:
    """Fetch the latest 10-year Treasury rate for the evaluation week from FMP.

    Returns the annualized rate (e.g., 4.59 for 4.59%).
    Falls back to 4.5 if API fails or is not available.
    """
    from core.config import FMP_API_KEY

    if not FMP_API_KEY:
        logger.warning("FMP_API_KEY not set. Using fallback bond yield of 4.50%")
        return 4.50

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            url = "https://financialmodelingprep.com/stable/treasury-rates"
            params = {"from": week_start.isoformat(), "to": week_end.isoformat(), "apikey": FMP_API_KEY}
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, list):
                    # Data is sorted descending (newest first). Extract 'year10' from the newest row.
                    newest_row = data[0]
                    # Also try other maturities if year10 is missing
                    rate = newest_row.get("year10") or newest_row.get("year5") or newest_row.get("month3")
                    if rate is not None:
                        return float(rate)
            logger.warning(f"Failed to fetch treasury rates from FMP (status={resp.status_code}). Using fallback 4.50%")
    except Exception as e:
        logger.warning(f"Error fetching treasury rates from FMP: {e}. Using fallback 4.50%")

    return 4.50


async def _fetch_dollar_index_return(week_start: date, week_end: date) -> float:
    """Fetch UUP (US Dollar Index ETF) history from FMP and compute weekly return %.

    Returns return % (e.g., 1.25 for 1.25% gain).
    Falls back to 0.0 if API fails or is not available.
    """
    from core.config import FMP_API_KEY

    if not FMP_API_KEY:
        logger.warning("FMP_API_KEY not set. Using fallback dollar return of 0.00%")
        return 0.0

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            url = "https://financialmodelingprep.com/stable/historical-price-eod/full"
            params = {
                "symbol": "UUP",
                "from": week_start.isoformat(),
                "to": week_end.isoformat(),
                "apikey": FMP_API_KEY,
            }
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                historical = data.get("historical", []) if isinstance(data, dict) else data
                if historical and len(historical) >= 2:
                    # historical is sorted descending (newest first).
                    newest_close = float(historical[0]["close"])
                    oldest_close = float(historical[-1]["close"])
                    if oldest_close > 0:
                        return ((newest_close - oldest_close) / oldest_close) * 100
            logger.warning(f"Failed to fetch UUP history from FMP (status={resp.status_code}). Using fallback 0.00%")
    except Exception as e:
        logger.warning(f"Error fetching UUP history from FMP: {e}. Using fallback 0.00%")

    return 0.0


async def evaluate_week(
    week_start: date | None = None,
    week_end: date | None = None,
    track_id: str = "track_default",
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

    logger.info("Evaluating week %s to %s for track %s", week_start, week_end, track_id)

    try:
        if track_id and track_id != "track_default":
            current_prompt = await get_active_prompt(track_id=track_id)
        else:
            current_prompt = await get_active_prompt()
    except TypeError:
        current_prompt = await get_active_prompt()

    from core.llm.prompts import split_prompt

    if not current_prompt:
        from core.llm import prompts

        current_prompt = prompts.CORE_ANALYSIS_SYSTEM_PROMPT

    _, current_prompt_mutable, _ = split_prompt(current_prompt)

    # Fetch SPY returns once — benchmark for the score.
    sb_client = await get_async_supabase_client()
    spy_returns = await _spy_returns(sb_client, week_start, week_end)

    # Compute SPY return from daily returns.
    spy_return_pct = 0.0
    if spy_returns:
        cumulative = 1.0
        for r in spy_returns:
            cumulative *= 1 + r
        spy_return_pct = (cumulative - 1) * 100

    # Experiment group metrics.
    exp_metrics = await compute_wall_street_metrics(
        AUTORESEARCH_EXPERIMENT_OWNER_IDS,
        week_start,
        week_end,
    )

    # Control group metrics (reference only).
    ctrl_metrics = await compute_wall_street_metrics(
        CONTROL_OWNER_IDS,
        week_start,
        week_end,
    )

    # Fetch actual bond yield and DXY (UUP) return from FMP
    bond_annual_rate = await _fetch_actual_bond_yield(week_start, week_end)
    dollar_return_pct = await _fetch_dollar_index_return(week_start, week_end)

    days_in_period = (week_end - week_start).days + 1
    # Compound the annualized bond yield to the weekly period
    bond_return_pct = ((1 + (bond_annual_rate / 100)) ** (days_in_period / 365.25) - 1) * 100

    # Compute the single score.
    score_result = compute_score(
        portfolio_return_pct=exp_metrics.get("total_return_pct", 0),
        spy_return_pct=spy_return_pct,
        max_drawdown_pct=exp_metrics.get("max_drawdown", 0) * 100,
        bond_return_pct=bond_return_pct,
        dollar_return_pct=dollar_return_pct,
        volatility_pct=exp_metrics.get("volatility", 0) * 100,
        do_nothing_return_pct=exp_metrics.get("do_nothing_return_pct", 0),
    )
    score_result["portfolio_details"] = exp_metrics.get("portfolio_details", {})

    try:
        if track_id and track_id != "track_default":
            previous = await get_previous_variants(limit=5, track_id=track_id)
            baseline_variant = await get_all_time_baseline(track_id=track_id)
        else:
            previous = await get_previous_variants(limit=5)
            baseline_variant = await get_all_time_baseline()
    except TypeError:
        previous = await get_previous_variants(limit=5)
        baseline_variant = await get_all_time_baseline()

    baseline_score = None
    baseline_prompt = None
    baseline_prompt_mutable = "No baseline prompt yet."
    if baseline_variant:
        baseline_prompt = baseline_variant.get("prompt_content")
        if baseline_prompt:
            _, baseline_prompt_mutable, _ = split_prompt(baseline_prompt)
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
        baseline_line = f"Baseline: {baseline_score} (best so far)  (Δ: {delta:+.4f} vs baseline)"
    else:
        baseline_line = "Baseline: N/A (first week, no baseline yet)"

    portfolio_ret = exp_metrics.get("total_return_pct", 0)
    max_drawdown = score_result["max_drawdown"]
    opp_penalty = score_result["opportunity_cost_penalty"]

    report_parts = [
        "# Weekly Performance",
        f"Score: {score_result['score']}  "
        f"(portfolio: {portfolio_ret:+.2f}% | "
        f"Do-Nothing: {score_result['do_nothing_return_pct']:+.2f}% | "
        f"SPY: {spy_return_pct:+.2f}% | "
        f"drawdown: -{max_drawdown:.2f}%)",
        f"Opportunity Cost Hurdle (compounded to {days_in_period} days):",
        f"  - Actual 10-year Treasury Bond Yield (Active Hurdle): {bond_annual_rate:.2f}% annual ({bond_return_pct:+.4f}% compounded)",
        f"  - Actual US Dollar Index Return (DXY/UUP) [Context Only]: {dollar_return_pct:+.4f}%",
        f"  - Opportunity Cost Penalty: {opp_penalty:+.4f}%",
        baseline_line,
        f"Formula: (Portfolio_Return - Do-Nothing_Return) + (Portfolio_Return - SPY_Return) - Opportunity_Cost_Penalty - (Drawdown × 0.3) = "
        f"({portfolio_ret:.2f} - {score_result['do_nothing_return_pct']:.2f}) + ({portfolio_ret:.2f} - {spy_return_pct:.2f}) - {opp_penalty:.2f} - ({max_drawdown:.2f} × 0.3) = "
        f"{portfolio_ret - score_result['do_nothing_return_pct']:.2f} + {portfolio_ret - spy_return_pct:.2f} - {opp_penalty:.2f} - {max_drawdown * 0.3:.2f} = "
        f"{score_result['score']}",
        "",
        "# Control Reference",
        f"Control agents (OpenAI + Claude on baseline): "
        f"{ctrl_metrics.get('total_return_pct', 0):+.2f}% return, "
        f"-{ctrl_metrics.get('max_drawdown', 0) * 100:.2f}% drawdown",
        "",
        _format_variants(previous, baseline_score=baseline_score),
        "",
        "# Baseline Prompt (All-Time Best)",
        "This is the mutable strategies and analysis section of the prompt that achieved the highest score so far. Use this as your foundation.",
        "```",
        baseline_prompt_mutable,
        "```",
        "",
        "# Latest Experiment Prompt (Just Evaluated)",
        "This is the mutable strategies and analysis section of the prompt that produced the score at the top of this report.",
        "```",
        current_prompt_mutable,
        "```",
        "",
        "# Instructions",
        "Propose a new strategy and analysis section to replace the sections shown above. Return ONLY valid JSON with "
        "new_prompt_text (containing the modified strategy and analysis rules section only), "
        "change_description, experiment_type, research_reasoning, and confidence.",
    ]

    return "\n".join(report_parts), score_result, baseline_variant.get("variant_tag") if baseline_variant else None
