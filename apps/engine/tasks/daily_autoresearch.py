import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel, Field

from core.config import (
    DEEPSEEK_FLASH_MODEL,
    JEV_MODEL,
    MINIMAX_MODEL,
    OPENAI_MODEL,
    logger,
)
from core.db import get_supabase_client
from core.llm.clients import close_client, get_deepseek_client, get_openai_client
from core.llm.daily_predictor_prompts import (
    DAILY_PREDICTOR_CONSTRAINTS_FOOTER,
    DAILY_PREDICTOR_CONSTRAINTS_HEADER,
    JEV_PREDICTOR_INSTRUCTIONS,
    format_jev_prompt_content,
    parse_jev_prompt_content,
    split_daily_predictor_prompt,
)


class DailyMetaPromptResponse(BaseModel):
    new_prompt: str = Field(
        ..., description="The complete modified strategy and analytical reasoning instructions text"
    )
    research_insight: str | None = Field(
        default=None,
        description=(
            "A concise, durable strategic takeaway or lesson learned from this week's prediction results "
            "(e.g. how specific macro catalysts, gap-ups, or VIX levels affected SPY accuracy and magnitude calibration). "
            "This will be preserved in long-term memory for this model track."
        ),
    )


class JevMetaCriteriaResponse(BaseModel):
    criteria_up: str = Field(
        ...,
        description="The mutated criteria text defining when the market will close HIGHER (UP). Focus on specific technical, catalyst, or macro conditions.",
    )
    criteria_down: str = Field(
        ...,
        description="The mutated criteria text defining when the market will close LOWER (DOWN). Focus on specific technical, catalyst, or macro conditions.",
    )
    research_insight: str | None = Field(
        default=None,
        description=(
            "A concise, durable strategic takeaway or lesson learned from this week's prediction results "
            "(e.g. how specific macro catalysts, gap-ups, or VIX levels affected Jev's classification accuracy). "
            "This will be preserved in long-term memory for the Jev model track."
        ),
    )


DEFAULT_DAILY_PREDICTOR_TOOLS = [
    "fetch_daily_newsletter",
    "get_calendar_scenario_analysis",
    "get_global_macro_context",
    "get_macro_options_sentiment",
    "get_volatility_index_details",
    "get_market_health_barometer",
    "get_market_feeling",
    "get_today_economic_releases",
    "get_premarket_quote",
]


def calculate_magnitude_capture(p: dict) -> float:
    """Calculate magnitude capture percentage (0-100%) for a single prediction."""
    is_correct = p.get("is_correct") is True
    intraday_hit = p.get("intraday_hit") is True or (p.get("intraday_hit") is None and is_correct)

    if not is_correct or not intraday_hit:
        return 0.0

    expected_return_pct = p.get("expected_return_pct")
    exp_pct = abs(float(expected_return_pct)) if expected_return_pct is not None else 0.0

    open_p = p.get("open_price") or p.get("actual_open_price")
    high_p = p.get("high_price") or p.get("actual_high_price")
    low_p = p.get("low_price") or p.get("actual_low_price")
    close_p = p.get("close_price") or p.get("actual_close_price")
    predicted_dir = (p.get("predicted_direction") or ("UP" if is_correct else "DOWN")).upper()

    if open_p and open_p > 0:
        close_return = abs((close_p - open_p) / open_p) * 100.0 if close_p else 0.0
        if predicted_dir == "UP":
            peak_return = max(0.0, ((high_p - open_p) / open_p) * 100.0) if high_p else close_return
        else:
            peak_return = max(0.0, ((open_p - low_p) / open_p) * 100.0) if low_p else close_return

        actual_move = max(peak_return, close_return)
        if actual_move > 0:
            return min(1.0, exp_pct / actual_move) * 100.0
        return 100.0 if exp_pct == 0 else 0.0

    return 100.0


def calculate_daily_ratchet_metrics(predictions: list[dict]) -> dict:
    """Calculate the full ratchet performance metrics breakdown for daily predictions.

    Score is based on:
    - EOD Close Directional Accuracy % (weight: 0.55)
    - Intraday Target Hit Rate % (weight: 0.35)
    - Magnitude Capture Ratio % (weight: 0.10)
    - Mean Brier Score penalty (penalty multiplier: 50.0)
    Combined Score = (0.55 * close_acc) + (0.35 * hit_rate) + (0.10 * mag_capture) - (mean_brier * 50.0).
    """
    if not predictions:
        return {
            "score": 0.0,
            "close_accuracy_pct": 0.0,
            "intraday_hit_pct": 0.0,
            "magnitude_capture_pct": 0.0,
            "mean_brier": 0.25,
            "predictions_evaluated": 0,
            "correct_count": 0,
            "intraday_hit_count": 0,
        }

    correct_count = sum(1 for p in predictions if p.get("is_correct") is True)
    close_accuracy_pct = (correct_count / len(predictions)) * 100.0

    intraday_hit_count = sum(
        1
        for p in predictions
        if p.get("intraday_hit") is True or (p.get("intraday_hit") is None and p.get("is_correct") is True)
    )
    intraday_hit_pct = (intraday_hit_count / len(predictions)) * 100.0

    magnitude_captures = [calculate_magnitude_capture(p) for p in predictions]
    mean_mag_capture = sum(magnitude_captures) / len(magnitude_captures)

    brier_scores = [p.get("brier_score") for p in predictions if p.get("brier_score") is not None]
    mean_brier = (sum(brier_scores) / len(brier_scores)) if brier_scores else 0.25

    final_score = (
        (0.55 * close_accuracy_pct) + (0.35 * intraday_hit_pct) + (0.10 * mean_mag_capture) - (mean_brier * 50.0)
    )
    return {
        "score": round(float(final_score), 4),
        "close_accuracy_pct": round(float(close_accuracy_pct), 2),
        "intraday_hit_pct": round(float(intraday_hit_pct), 2),
        "magnitude_capture_pct": round(float(mean_mag_capture), 2),
        "mean_brier": round(float(mean_brier), 4),
        "predictions_evaluated": len(predictions),
        "correct_count": correct_count,
        "intraday_hit_count": intraday_hit_count,
    }


def calculate_daily_ratchet_score(predictions: list[dict]) -> float:
    """Calculate the ratchet performance score for daily predictions."""
    return float(calculate_daily_ratchet_metrics(predictions)["score"])


def fetch_autoresearch_context(client, start_date_str: str, end_date_str: str, track_id: str | None = None) -> dict:
    """Fetch recent newsletters, market events, active concept themes, and track-specific autoresearch memories."""
    context = {
        "daily_events": {},
        "active_concepts": [],
        "track_id": track_id,
        "track_memories": "",
    }

    try:
        # 1. Fetch newsletter snapshots within the date window
        news_resp = (
            client.table("newsletter_snapshots")
            .select("date, sender, subject, content")
            .gte("date", f"{start_date_str}T00:00:00Z")
            .lte("date", f"{end_date_str}T23:59:59Z")
            .order("date", desc=True)
            .limit(20)
            .execute()
        )
        if news_resp and news_resp.data:
            for item in news_resp.data:
                d_str = str(item.get("date") or "")[:10]
                if not d_str:
                    continue
                sender = item.get("sender", "Unknown")
                subject = item.get("subject", "No Subject")
                snippet = (item.get("content") or "").strip().replace("\n", " ")[:150]
                entry = f"{sender}: {subject}" + (f" ({snippet}...)" if snippet else "")
                context["daily_events"].setdefault(d_str, {"newsletters": [], "events": []})["newsletters"].append(
                    entry
                )
    except Exception as e:
        logger.warning(f"Error fetching newsletters for autoresearch context: {e}")

    try:
        # 2. Fetch market events / resolved memories within the date window
        events_resp = (
            client.table("memories")
            .select("id, content, metadata, memory_type, created_at")
            .in_("memory_type", ["MARKET_EVENT", "POST_MORTEM", "RESOLUTION"])
            .gte("created_at", f"{start_date_str}T00:00:00Z")
            .lte("created_at", f"{end_date_str}T23:59:59Z")
            .order("created_at", desc=True)
            .limit(15)
            .execute()
        )
        if events_resp and events_resp.data:
            for item in events_resp.data:
                d_str = str(item.get("created_at") or "")[:10]
                if not d_str:
                    continue
                content = (item.get("content") or "").strip().replace("\n", " ")[:160]
                entry = f"[{item.get('memory_type', 'EVENT')}] {content}"
                context["daily_events"].setdefault(d_str, {"newsletters": [], "events": []})["events"].append(entry)
    except Exception as e:
        logger.warning(f"Error fetching events for autoresearch context: {e}")

    try:
        # 3. Fetch top active concept metrics
        concepts_resp = (
            client.table("concept_metrics")
            .select("concept_name, velocity_score, mention_count, last_mention_at")
            .order("velocity_score", desc=True)
            .limit(8)
            .execute()
        )
        if concepts_resp and concepts_resp.data:
            for c in concepts_resp.data:
                c_name = c.get("concept_name")
                if c_name:
                    vel = float(c.get("velocity_score") or 0.0)
                    mentions = int(c.get("mention_count") or 0)
                    context["active_concepts"].append(f"- **{c_name}** (Velocity: {vel:.1f}, Mentions: {mentions})")
    except Exception as e:
        logger.warning(f"Error fetching active concepts for autoresearch context: {e}")

    if track_id:
        try:
            from memory.store import retrieve_autoresearch_memories

            track_memories = retrieve_autoresearch_memories(track_id=track_id, scope="daily_predictor", limit=5)
            if track_memories:
                context["track_memories"] = track_memories
        except Exception as e:
            logger.warning(f"Error fetching autoresearch memories for {track_id}: {e}")

    return context


def compute_magnitude_postmortem_summary(
    predictions: list[dict],
    macro_context: dict | None = None,
) -> str:
    """Generate a structured markdown postmortem analyzing magnitude calibration and timid vs overshooting errors."""
    if not predictions:
        return "No recent prediction history available."

    daily_events = macro_context.get("daily_events", {}) if macro_context else {}
    has_catalysts = bool(daily_events)

    headers = [
        "### RECENT PREDICTIONS POSTMORTEM & MAGNITUDE CALIBRATION",
        "| Date | Dir | Pred % | Peak % | Close % | Correct? | Hit? | Brier | Capture % | Diagnosis |"
        + (" Key Catalysts / News |" if has_catalysts else ""),
        "|---|---|---|---|---|---|---|---|---|---|" + ("---|" if has_catalysts else ""),
    ]
    lines = list(headers)

    timid_cases = []
    overshot_cases = []
    luna_postmortems = []

    for p in predictions:
        date_str = str(p.get("target_date") or p.get("prediction_date") or "N/A")[:10]
        direction = str(p.get("predicted_direction") or "N/A").upper()
        exp_pct = float(p.get("expected_return_pct") or 0.0)
        open_p = p.get("open_price") or p.get("actual_open_price")
        high_p = p.get("high_price") or p.get("actual_high_price")
        low_p = p.get("low_price") or p.get("actual_low_price")
        close_p = p.get("close_price") or p.get("actual_close_price")
        is_correct = p.get("is_correct") is True
        intraday_hit = p.get("intraday_hit") is True or (p.get("intraday_hit") is None and is_correct)
        brier = float(p.get("brier_score") or 0.0)
        capture = calculate_magnitude_capture(p)

        peak_pct = 0.0
        close_pct = 0.0
        if open_p and open_p > 0:
            if close_p:
                close_pct = ((close_p - open_p) / open_p) * 100.0
            if direction == "UP" and high_p:
                peak_pct = ((high_p - open_p) / open_p) * 100.0
            elif direction == "DOWN" and low_p:
                peak_pct = ((low_p - open_p) / open_p) * 100.0
            else:
                peak_pct = close_pct

        actual_move = max(abs(peak_pct), abs(close_pct))

        # Check for verified GPT-5.6 Luna post-mortem
        pm_cat = p.get("postmortem_category")
        pm_lesson = p.get("postmortem_lesson")
        pm_flaw = p.get("postmortem_flawed_assumption")
        if pm_lesson and pm_cat:
            flaw_str = f" (Flawed assumption: {pm_flaw})" if pm_flaw and pm_flaw != "None" else ""
            luna_postmortems.append(f"- **{date_str} [{pm_cat}]**: {pm_lesson}{flaw_str}")

        # Build day's catalyst summary
        day_news = daily_events.get(date_str, {}).get("newsletters", [])
        day_evts = daily_events.get(date_str, {}).get("events", [])
        all_day_catalysts = day_news + day_evts
        catalyst_snippet = "; ".join(all_day_catalysts[:2]) if all_day_catalysts else "None recorded"

        if pm_cat:
            diagnosis = pm_cat
        elif is_correct and intraday_hit:
            if actual_move >= 0.60 and capture < 40.0:
                diagnosis = "Timid / Underestimated"
                timid_cases.append(
                    f"- **{date_str}**: Predicted {direction} {exp_pct:+.2f}%, but market moved {actual_move:+.2f}% (only {capture:.1f}% captured). Catalyst context: {catalyst_snippet}. Strong momentum was left on the table."
                )
            else:
                diagnosis = "Well-Calibrated"
        elif not intraday_hit and is_correct:
            if abs(exp_pct) >= 0.60:
                diagnosis = "Overshot / Missed Target"
                overshot_cases.append(
                    f"- **{date_str}**: Target {exp_pct:+.2f}% was too aggressive for actual intraday range (peak {peak_pct:+.2f}%). Catalyst context: {catalyst_snippet}."
                )
            else:
                diagnosis = "Missed Target"
        else:
            diagnosis = "Wrong Direction"

        row = (
            f"| {date_str} | {direction} | {exp_pct:+.2f}% | {peak_pct:+.2f}% | {close_pct:+.2f}% | "
            f"{'Yes' if is_correct else 'No'} | {'Yes' if intraday_hit else 'No'} | {brier:.3f} | {capture:.1f}% | {diagnosis} |"
        )
        if has_catalysts:
            row += f" {catalyst_snippet} |"
        lines.append(row)

    if luna_postmortems:
        lines.append("\n#### VERIFIED DAILY POST-MORTEMS & FAILURE DIAGNOSES (GPT-5.6 LUNA):")
        lines.extend(luna_postmortems)

    lines.append("\n#### Magnitude Calibration Diagnosis:")
    if timid_cases:
        lines.append(
            "**Timid / Underestimated Instances (Need more aggressive magnitude on high-conviction catalysts):**"
        )
        lines.extend(timid_cases)
    else:
        lines.append("- No severe underestimation instances detected in recent sample.")

    if overshot_cases:
        lines.append("**Overshot / Missed Target Instances (Target was set beyond available volatility):**")
        lines.extend(overshot_cases)
    else:
        lines.append("- No severe overshooting errors detected.")

    # Append Active Concepts & Narrative Playbooks section if present
    active_concepts = macro_context.get("active_concepts", []) if macro_context else []
    if active_concepts:
        lines.append("\n#### ACTIVE THEMATIC CONCEPTS & MARKET PLAYBOOKS:")
        lines.extend(active_concepts)

    # Append Prior Autoresearch Memories for this track if present
    track_mems = macro_context.get("track_memories") if macro_context else None
    if track_mems:
        track_name = macro_context.get("track_id") or "CURRENT TRACK"
        lines.append(f"\n#### PRIOR AUTORESEARCH MEMORIES & LESSONS (Track: {track_name}):")
        lines.append(track_mems)

    return "\n".join(lines)


async def generate_new_daily_prompt(
    old_prompt: str,
    baseline_score: float,
    predictions: list[dict] | None = None,
    macro_context: dict | None = None,
    meta_researcher=None,
    cold_start: bool = False,
) -> tuple[str, str | None]:
    """Generate a mutated strategy instruction prompt using DeepSeek Flash."""
    _, mutable_strategies, _ = split_daily_predictor_prompt(old_prompt)

    postmortem_context = (
        compute_magnitude_postmortem_summary(predictions, macro_context=macro_context)
        if predictions
        else "No recent prediction postmortem available."
    )

    if cold_start:
        strategy_block = (
            "=== COLD START RESET (STRATEGY FROM SCRATCH) ===\n"
            "This cycle is a COLD START RESET (1-in-6 stochastic exploration to escape local optima).\n"
            "DO NOT anchor on or adapt the prior strategy. Generate an entirely novel, high-conviction analytical strategy and reasoning rules for SPY daily movement from scratch.\n"
            "Remember that system header rules and the required JSON output schema are FROZEN and automatically appended.\n"
            "Output ONLY the raw new strategy instructions text."
        )
    else:
        strategy_block = (
            "CURRENT STRATEGY INSTRUCTIONS (MUTABLE SECTION ONLY):\n"
            f"```text\n{mutable_strategies}\n```\n\n"
            "Output ONLY the raw new strategy instructions text."
        )

    meta_prompt = (
        "You are a Meta-Researcher AI optimizing an LLM prompt for predicting intraday S&P 500 (SPY) open-to-close price movement.\n\n"
        f"The current prompt strategy achieved a ratchet score of {baseline_score:.2f}.\n\n"
        f"{postmortem_context}\n\n"
        "### STRUCTURAL PROMPT SECTIONS & MUTATION RULES:\n"
        "1. STRUCTURAL SECTIONS ARE FROZEN: System constraints (trader identity, available market context injection, zero-mean anti-bias mandate, and required JSON output format) are FROZEN and managed automatically by the engine.\n"
        "2. Do NOT include system header rules, context definitions, zero-mean mandates, or JSON schemas in your output. You are modifying ONLY the analytical reasoning and strategy section.\n"
        "3. Prioritize Directional Accuracy (55% weight) and Intraday Hit Rate (35% weight) first and foremost.\n"
        "4. Learn from Cause & Effect: Analyze the correlation between recent market catalysts, newsletters, and prediction failures/successes. "
        "Incorporate concrete cause-and-effect reasoning heuristics (e.g., how SPY reacts to yield shifts, tech capex surges, or pre-market gap-downs).\n"
        "5. Optimize Magnitude Calibration (10% weight): When high-impact catalysts or strong trend conditions align, "
        "instruct the predictor to be more confident and aggressive in expected_return_pct magnitude (e.g. +0.50% to +1.20% instead of timid +0.20%).\n"
        "6. On rangebound, ambiguous, or high-VIX days, keep expected_return_pct conservative (+0.15% to +0.25%) to ensure target hit reliability.\n"
        "7. Provide a concise `research_insight` (1-2 sentences) summarizing the core lesson or causal rule learned from this week's results to persist in this track's institutional memory.\n\n"
        f"{strategy_block}"
    )

    try:
        resp_awaitable = meta_researcher.chat.completions.create(
            model="deepseek-v4-flash",
            response_model=DailyMetaPromptResponse,
            messages=[{"role": "user", "content": meta_prompt}],
        )
        if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
            resp = await resp_awaitable
        else:
            resp = resp_awaitable

        new_strategies = resp.new_prompt.strip()
        if new_strategies.startswith("```"):
            lines = new_strategies.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            new_strategies = "\n".join(lines).strip()

        # Sanitize new_strategies through split_daily_predictor_prompt to guarantee
        # no structural headers or footers accidentally included by the LLM pollute assembled_prompt
        _, clean_strategies, _ = split_daily_predictor_prompt(new_strategies)
        assembled_prompt = DAILY_PREDICTOR_CONSTRAINTS_HEADER + clean_strategies + DAILY_PREDICTOR_CONSTRAINTS_FOOTER
        insight = getattr(resp, "research_insight", None)
        if insight:
            insight = insight.strip()
        return assembled_prompt, insight
    except Exception as e:
        logger.error(f"Error generating new daily predictor prompt: {e}")
        return old_prompt, None


async def generate_new_jev_criteria(
    old_prompt_content: str,
    predictions: list[dict],
    macro_context: dict,
    baseline_score: float,
    openai_meta,
    cold_start: bool = False,
) -> tuple[str, str | None]:
    """Generate mutated UP and DOWN criteria for Jev using OpenAI Luna (gpt-5.6-luna)."""
    current_criteria = parse_jev_prompt_content(old_prompt_content)

    postmortem_context = (
        compute_magnitude_postmortem_summary(predictions, macro_context=macro_context)
        if predictions
        else "No recent prediction postmortem available."
    )

    if cold_start:
        criteria_block = (
            "=== COLD START RESET (CRITERIA FROM SCRATCH) ===\n"
            "This cycle is a COLD START RESET (1-in-6 stochastic exploration).\n"
            "DO NOT anchor on prior criteria. Generate entirely fresh, high-conviction classification rules "
            "for UP (bullish session) and DOWN (bearish session) from scratch."
        )
    else:
        criteria_block = (
            "CURRENT JEV CLASSIFICATION CRITERIA:\n"
            f"UP Criteria: {current_criteria.get('UP', '')}\n"
            f"DOWN Criteria: {current_criteria.get('DOWN', '')}\n"
        )

    meta_prompt = (
        f"You are a Meta-Researcher AI optimizing the decision criteria for Jev, a fast System One probability classifier.\n"
        f"Jev answers the question: '{JEV_PREDICTOR_INSTRUCTIONS}'\n"
        f"It classifies market state into 'UP' or 'DOWN' and outputs probabilities.\n\n"
        f"The current criteria achieved a ratchet score of {baseline_score:.2f}.\n\n"
        f"{postmortem_context}\n\n"
        "### CRITICAL STRUCTURAL BOUNDARIES:\n"
        "1. Question structure, choices ('UP', 'DOWN'), and instructions are FROZEN.\n"
        "2. You are modifying ONLY `criteria_up` and `criteria_down`.\n"
        "3. Keep each criteria concise, specific, and actionable (2-4 sentences describing technical VWAP behavior, catalyst follow-through, yield moves, or overnight gap dynamics).\n"
        "4. Both criteria MUST be symmetric and balanced. Avoid bullish drift.\n"
        "5. Provide a concise `research_insight` (1-2 sentences) summarizing what misled Jev this week.\n\n"
        f"{criteria_block}"
    )

    try:
        resp_awaitable = openai_meta.chat.completions.create(
            model=OPENAI_MODEL,
            response_model=JevMetaCriteriaResponse,
            messages=[{"role": "user", "content": meta_prompt}],
        )
        if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
            resp = await resp_awaitable
        else:
            resp = resp_awaitable

        new_crit = {
            "UP": resp.criteria_up.strip(),
            "DOWN": resp.criteria_down.strip(),
        }
        insight = getattr(resp, "research_insight", None)
        if insight:
            insight = insight.strip()
        return format_jev_prompt_content(new_crit), insight
    except Exception as e:
        logger.error(f"Error generating new Jev criteria with OpenAI Luna: {e}")
        return old_prompt_content, None


async def run_daily_autoresearch_for_model(
    model_name: str,
    client,
    today,
    seven_days_ago,
    fourteen_days_ago,
    deepseek_meta,
    openai_meta=None,
    dry_run: bool = False,
    cold_start: bool | None = None,
):
    """Run weekly prompt evolution and ratchet check for a single daily predictor model track."""
    from autoresearch.runner import roll_cold_start_dice

    is_cold_start = roll_cold_start_dice() if cold_start is None else cold_start
    if is_cold_start:
        logger.info(f"COLD START: Stochastic 1-in-6 dice triggered fresh SPY strategy from 0 for {model_name}")

    # 1. Fetch evaluated daily predictions for this model over the past 7 days (all available trading sessions)
    response = (
        client.table("daily_predictions")
        .select("*")
        .eq("status", "evaluated")
        .eq("model_name", model_name)
        .gte("target_date", seven_days_ago.isoformat())
        .lte("target_date", today.isoformat())
        .execute()
    )

    predictions = [
        p
        for p in (response.data or [])
        if not (p.get("prompt_variant_tag") and "backtest" in p["prompt_variant_tag"].lower())
    ]
    if not predictions:
        logger.info(f"No evaluated daily predictions found for {model_name} in the past week. Skipping autoresearch.")
        return

    current_metrics = calculate_daily_ratchet_metrics(predictions)
    current_score = current_metrics["score"]

    # 2. Fetch active prompt variant for this model track
    prompt_response = (
        client.table("prompt_experiments")
        .select("*")
        .eq("prompt_name", "DAILY_PREDICTOR_PROMPT")
        .eq("track_id", model_name)
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not prompt_response.data:
        # Fallback to model track baseline
        prompt_response = (
            client.table("prompt_experiments")
            .select("*")
            .eq("prompt_name", "DAILY_PREDICTOR_PROMPT")
            .eq("track_id", model_name)
            .eq("status", "baseline")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

    if not prompt_response.data:
        # If no variants exist yet for this model, seed the baseline
        from tasks.daily_predictor import seed_daily_predictor_prompt

        tag, content = await seed_daily_predictor_prompt(model_name=model_name)
        prompt_response = (
            client.table("prompt_experiments")
            .select("*")
            .eq("prompt_name", "DAILY_PREDICTOR_PROMPT")
            .eq("track_id", model_name)
            .eq("variant_tag", tag)
            .execute()
        )

    if not prompt_response.data:
        logger.warning(f"No active DAILY_PREDICTOR_PROMPT found for {model_name}. Cannot run daily autoresearch.")
        return

    current_prompt = prompt_response.data[0]["prompt_content"]
    parent_tag = prompt_response.data[0]["variant_tag"]

    # 3. Update active prompt metrics with full breakdown
    if dry_run:
        logger.info(f"[DRY RUN] Would update metrics for {parent_tag}: {current_metrics}")
    else:
        client.table("prompt_experiments").update({"metrics": current_metrics}).eq("variant_tag", parent_tag).execute()

    # 4. Fetch baseline variants to perform ratchet comparison strictly within this model track
    all_variants_resp = (
        client.table("prompt_experiments")
        .select("*")
        .eq("prompt_name", "DAILY_PREDICTOR_PROMPT")
        .eq("track_id", model_name)
        .execute()
    )
    all_variants = all_variants_resp.data or []

    baseline_score = -100.0
    baseline_tag = parent_tag
    baseline_content = current_prompt

    for v in all_variants:
        if v["variant_tag"] == parent_tag:
            continue
        m = v.get("metrics") or {}
        score = m.get("score")
        if score is not None and score > baseline_score:
            baseline_score = score
            baseline_tag = v["variant_tag"]
            baseline_content = v["prompt_content"]

    # Compare recent score with baseline
    if baseline_score != -100.0 and current_score < baseline_score:
        logger.info(
            f"DAILY RATCHET ({model_name}): Score {current_score:.2f} failed to beat baseline {baseline_score:.2f}. "
            f"Reverting to baseline {baseline_tag}."
        )
        if not dry_run:
            client.table("prompt_experiments").update({"status": "discarded"}).eq("variant_tag", parent_tag).execute()
        current_prompt = baseline_content
        parent_tag = baseline_tag
    else:
        logger.info(
            f"DAILY RATCHET ({model_name}): Score {current_score:.2f} beats/equals baseline {baseline_score:.2f}. "
            f"Establishing {parent_tag} as new baseline."
        )
        if not dry_run:
            client.table("prompt_experiments").update({"status": "baseline"}).eq("variant_tag", parent_tag).execute()

    # 5. Fetch 14-day rich macro, newsletter, and concepts context
    macro_context = fetch_autoresearch_context(
        client, fourteen_days_ago.isoformat(), today.isoformat(), track_id=model_name
    )

    # 6. Mutate prompt using DeepSeek Flash or OpenAI Luna for Jev
    is_jev = "jev" in model_name.lower()
    if is_jev:
        new_prompt, research_insight = await generate_new_jev_criteria(
            old_prompt_content=current_prompt,
            baseline_score=current_score,
            predictions=predictions,
            macro_context=macro_context,
            openai_meta=openai_meta,
            cold_start=is_cold_start,
        )
    else:
        new_prompt, research_insight = await generate_new_daily_prompt(
            old_prompt=current_prompt,
            baseline_score=current_score,
            predictions=predictions,
            macro_context=macro_context,
            meta_researcher=deepseek_meta,
            cold_start=is_cold_start,
        )

    # 7. Deploy new active prompt variant scoped to track_id, demoting prior active variants
    new_tag = f"daily-pred-{model_name}-{uuid.uuid4().hex[:8]}"
    week_end = today + timedelta(days=7)
    is_baseline_beat = (baseline_score == -100.0) or (current_score >= baseline_score)

    if research_insight:
        if dry_run:
            logger.info(f"[DRY RUN] Would record track memory for {model_name}: {research_insight}")
        else:
            try:
                from memory.store import add_memory

                importance = 9 if is_baseline_beat else 6
                add_memory(
                    content=f"[{model_name.upper()} DAILY PREDICTOR INSIGHT] {research_insight}",
                    memory_type="AUTORESEARCH_INSIGHT",
                    importance_score=importance,
                    metadata={
                        "scope": "daily_predictor",
                        "track_id": model_name,
                        "model_name": model_name,
                        "ratchet_score": current_score,
                        "baseline_score": baseline_score if baseline_score != -100.0 else None,
                        "is_baseline_beat": is_baseline_beat,
                        "variant_tag": new_tag,
                    },
                    check_similarity=True,
                )
                logger.info(f"Recorded autoresearch memory for {model_name}: {research_insight[:80]}...")
            except Exception as e:
                logger.warning(f"Failed to record autoresearch memory for {model_name}: {e}")

    if dry_run:
        logger.info(
            f"[DRY RUN] Would deploy new active prompt variant for {model_name}: {new_tag}\n"
            f"[DRY RUN] Parent Tag: {parent_tag}\n"
            f"[DRY RUN] Mutated Strategy Content Preview:\n{new_prompt[:300]}..."
        )
        return

    # Demote all existing active variants for this model track to saved
    client.table("prompt_experiments").update({"status": "saved"}).eq("prompt_name", "DAILY_PREDICTOR_PROMPT").eq(
        "track_id", model_name
    ).eq("status", "active").execute()

    research_output = {
        "research_insight": research_insight,
        "hypothesis": research_insight,
        "thought_process": research_insight,
        "research_reasoning": research_insight,
        "confidence": 0.85 if is_baseline_beat else 0.50,
        "selected_tools": ["openrouter_decisions"] if is_jev else DEFAULT_DAILY_PREDICTOR_TOOLS,
        "is_cold_start": is_cold_start,
    }

    exp_type = "radical" if is_cold_start else "incremental"
    desc = (
        f"Weekly daily autoresearch cold start (from 0) for {model_name}"
        if is_cold_start
        else f"Weekly daily autoresearch mutation for {model_name} from score {current_score:.2f}"
    )

    client.table("prompt_experiments").insert(
        {
            "variant_tag": new_tag,
            "prompt_name": "DAILY_PREDICTOR_PROMPT",
            "prompt_content": new_prompt,
            "track_id": model_name,
            "week_start": today.isoformat(),
            "week_end": week_end.isoformat(),
            "status": "active",
            "experiment_type": exp_type,
            "parent_tag": parent_tag,
            "change_description": desc,
            "research_output": research_output,
        }
    ).execute()

    logger.info(f"Successfully mutated and deployed new daily predictor prompt variant for {model_name}: {new_tag}")


async def run_daily_autoresearch(dry_run: bool = False, cold_start: bool | None = None):
    """Run weekly prompt evolution and ratchet check independently for all predictor models on Sunday."""
    client = get_supabase_client()
    today = datetime.now(UTC).date()
    seven_days_ago = today - timedelta(days=7)
    fourteen_days_ago = today - timedelta(days=14)

    target_models = [DEEPSEEK_FLASH_MODEL, MINIMAX_MODEL, JEV_MODEL]
    deepseek_meta = get_deepseek_client()
    openai_meta = get_openai_client()

    from autoresearch.runner import roll_cold_start_dice

    cold_start_triggered = False
    try:
        for model_name in target_models:
            if cold_start is True:
                m_cold = True
            elif cold_start is False:
                m_cold = False
            else:
                # Automated mode: roll 1-in-6 dice with max-1 guardrail
                if not cold_start_triggered and roll_cold_start_dice():
                    m_cold = True
                    cold_start_triggered = True
                else:
                    m_cold = False

            await run_daily_autoresearch_for_model(
                model_name=model_name,
                client=client,
                today=today,
                seven_days_ago=seven_days_ago,
                fourteen_days_ago=fourteen_days_ago,
                deepseek_meta=deepseek_meta,
                openai_meta=openai_meta,
                dry_run=dry_run,
                cold_start=m_cold,
            )
    finally:
        await close_client(deepseek_meta, "deepseek")
        await close_client(openai_meta, "openai")


if __name__ == "__main__":
    asyncio.run(run_daily_autoresearch())
