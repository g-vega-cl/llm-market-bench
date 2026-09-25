"""Daily Predictor Post-Mortem Island.

Audits intraday S&P 500 (SPY) daily predictions after market close using OpenAI Luna
(gpt-5.6-luna). Grounded strictly between the morning prediction rationale, the verified
regular trading hours (RTH) price tape, and the evening Wall Street close briefing.
Categorizes root causes into a closed taxonomy to feed weekly prompt autoresearch without hallucination.
"""

import asyncio
from datetime import UTC, datetime
from enum import StrEnum

import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from core import config
from core.config import OPENAI_MODEL, logger
from core.db import get_supabase_client
from memory.store import add_memory


class PostMortemCategory(StrEnum):
    ACCURATE_CAPTURE = "ACCURATE_CAPTURE"  # Direction and magnitude hit cleanly
    TIMID_MAGNITUDE = "TIMID_MAGNITUDE"  # Correct direction, but capped target too low on trend day
    OVERSHOT_TARGET = "OVERSHOT_TARGET"  # Correct direction, but target exceeded session volatility
    CATALYST_INVERSION = "CATALYST_INVERSION"  # Morning catalyst occurred, but market reacted opposite
    INTRADAY_REVERSAL = "INTRADAY_REVERSAL"  # Thesis worked initially, but faded/reversed in afternoon
    RANGEBOUND_CHOP = "RANGEBOUND_CHOP"  # Flat tape with zero momentum; forced direction on chop
    UNFORESEEN_SHOCK = "UNFORESEEN_SHOCK"  # Mid-day news or shock breaking after 9:30 AM


class DailyPredictionDiagnosis(BaseModel):
    category: PostMortemCategory = Field(
        ...,
        description="The primary classification of the prediction outcome or failure mode.",
    )
    was_predictable: bool = Field(
        ...,
        description=(
            "True if this outcome or failure was foreseeable from pre-market signals, "
            "options positioning, or macro indicators. False if driven by random noise inside "
            "a tight range or post-open breaking news."
        ),
    )
    observed_driver: str = Field(
        ...,
        description="The verified primary catalyst or driver from the evening close brief and price action.",
    )
    flawed_assumption: str = Field(
        ...,
        description=(
            "The specific flawed assumption in the morning prediction rationale that broke down, "
            "or 'None' if the prediction was accurate."
        ),
    )
    actionable_lesson: str = Field(
        ...,
        description=(
            "A concise 1-2 sentence conditional rule or heuristic to guide future models "
            "(e.g., 'When 10Y yield surges >4 bps pre-market, fade tech gap-ups regardless of earnings.')."
        ),
    )


def get_luna_client():
    """Create an async OpenAI client wrapped with Instructor Mode.JSON to allow active thinking."""
    raw_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY, timeout=180)
    return instructor.from_openai(raw_client, mode=instructor.Mode.JSON)


def format_intraday_tape_summary(rth_bars: list[dict]) -> str:
    """Format regular trading hours hourly bars into an easily readable intraday path table."""
    if not rth_bars:
        return "No hourly bar tape available."

    lines = [
        "| Time (ET) | Open | High | Low | Close | Hourly Move |",
        "|---|---|---|---|---|---|",
    ]
    for b in rth_bars:
        date_str = b.get("date", "")
        time_part = date_str.split(" ")[1] if " " in date_str else date_str
        open_p = float(b.get("open", 0.0))
        high_p = float(b.get("high", 0.0))
        low_p = float(b.get("low", 0.0))
        close_p = float(b.get("close", 0.0))
        pct_change = ((close_p - open_p) / open_p) * 100.0 if open_p > 0 else 0.0
        lines.append(
            f"| {time_part} | {open_p:.2f} | {high_p:.2f} | {low_p:.2f} | {close_p:.2f} | {pct_change:+.2f}% |"
        )
    return "\n".join(lines)


async def fetch_rth_bars_for_date(ticker: str, target_date_str: str) -> list[dict]:
    """Fetch timestamped hourly bars strictly within regular market hours (09:30 - 16:00 ET)."""
    try:
        from execution.market_data import MarketDataManager

        mdm = MarketDataManager()
        provider = mdm.provider
        if provider and hasattr(provider, "get_hourly_history"):
            bars = await provider.get_hourly_history(ticker, target_date_str, target_date_str)
            if bars:
                rth_bars = []
                for b in bars:
                    bar_date = b.get("date", "") if isinstance(b, dict) else getattr(b, "date", "")
                    time_part = bar_date.split(" ")[1] if " " in bar_date else ""
                    if "09:30:00" <= time_part <= "16:00:00":
                        rth_bars.append(b if isinstance(b, dict) else vars(b))
                return sorted(rth_bars, key=lambda x: x.get("date", ""))
    except Exception as e:
        logger.warning(f"Error fetching RTH hourly bars for {ticker} on {target_date_str}: {e}")
    return []


async def fetch_evening_newsletter_summary(client, target_date_str: str) -> dict | None:
    """Fetch the evening close newsletter from generated_newsletters."""
    try:
        res = (
            client.table("generated_newsletters")
            .select("title, summary, bullet_points, content, created_at")
            .eq("session", "close")
            .gte("created_at", f"{target_date_str}T00:00:00")
            .lte("created_at", f"{target_date_str}T23:59:59")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if res and res.data:
            return res.data[0]

        # Fallback to latest close newsletter if date mismatch
        fallback = (
            client.table("generated_newsletters")
            .select("title, summary, bullet_points, content, created_at")
            .eq("session", "close")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if fallback and fallback.data:
            return fallback.data[0]
    except Exception as e:
        logger.warning(f"Error fetching evening close newsletter for post-mortem: {e}")
    return None


async def diagnose_daily_prediction(
    prediction: dict,
    rth_bars: list[dict],
    close_newsletter: dict | None = None,
    luna_client=None,
) -> DailyPredictionDiagnosis:
    """Invokes GPT-5.6 Luna to diagnose the prediction outcome without hallucination."""
    client = luna_client or get_luna_client()

    ticker = prediction.get("ticker", "SPY")
    target_date = prediction.get("target_date", "N/A")
    pred_dir = prediction.get("predicted_direction", "N/A")
    confidence = prediction.get("confidence", 50.0)
    expected_return = prediction.get("expected_return_pct", 0.0)
    rationale = prediction.get("rationale", "No rationale provided.")
    catalysts = prediction.get("catalysts") or []
    open_p = prediction.get("open_price", 0.0)
    high_p = prediction.get("high_price", 0.0)
    low_p = prediction.get("low_price", 0.0)
    close_p = prediction.get("close_price", 0.0)
    actual_dir = prediction.get("actual_direction", "N/A")
    is_correct = prediction.get("is_correct") is True
    intraday_hit = prediction.get("intraday_hit") is True

    tape_table = format_intraday_tape_summary(rth_bars)

    news_text = "No evening market brief available."
    if close_newsletter:
        title = close_newsletter.get("title", "")
        summary = close_newsletter.get("summary", "")
        bullets = "\n".join([f"- {b}" for b in (close_newsletter.get("bullet_points") or [])])
        news_text = f"Title: {title}\nSummary: {summary}\nKey Takeaways:\n{bullets}"

    system_prompt = (
        "You are an elite quantitative trading post-mortem analyst auditing an intraday S&P 500 (SPY) forecast.\n\n"
        "### STRICT ANTI-HALLUCINATION RULES:\n"
        "1. GROUND TRUTH ONLY: Do NOT invent unverified macro excuses or narratives. You must cite evidence "
        "present in the verified evening market brief or the hourly price tape.\n"
        "2. ACCURATE PREDICTIONS: If the prediction was correct and captured the move, classify as ACCURATE_CAPTURE, "
        "set was_predictable=True, and set flawed_assumption='None'.\n"
        "3. TIMID VS OVERSHOT: If direction was right but target was missed, distinguish whether the model was "
        "TIMID_MAGNITUDE (underestimated a massive trend day) or OVERSHOT_TARGET (targeted moves beyond session ATR).\n"
        "4. CATALYST INVERSION: If the model expected a catalyst to lift markets, but the market sold off on that catalyst "
        "(e.g. rate hike fears or 'sell the news'), classify as CATALYST_INVERSION.\n"
        "5. INTRADAY REVERSAL: If the market followed the thesis early (first 1-2 hours) but reversed in the afternoon, "
        "classify as INTRADAY_REVERSAL.\n"
        "6. RANGEBOUND CHOP: If the entire session stayed within a 0.20% band around open with no trend, classify as RANGEBOUND_CHOP.\n"
        "7. UNFORESEEN SHOCK: If a breaking headline after 9:30 AM caused an unpredictable move, classify as UNFORESEEN_SHOCK "
        "and set was_predictable=False.\n"
        "8. ACTIONABLE LESSON: Synthesize exactly 1-2 sentences stating a concrete conditional rule to prevent repeating this error."
    )

    user_prompt = (
        f"### SESSION CONTEXT: {ticker} on {target_date}\n\n"
        f"#### 1. MORNING PREDICTION (Issued 9:15 AM ET):\n"
        f"- Predicted Direction: {pred_dir} (Confidence: {confidence:.1f}%)\n"
        f"- Target Return: {expected_return:+.2f}%\n"
        f"- Cited Catalysts: {', '.join(catalysts) if catalysts else 'None'}\n"
        f"- Morning Rationale: {rationale}\n\n"
        f"#### 2. ACTUAL SESSION PRICE ACTION (9:30 AM to 4:00 PM ET):\n"
        f"- Open: ${open_p:.2f} | High: ${high_p:.2f} | Low: ${low_p:.2f} | Close: ${close_p:.2f}\n"
        f"- Actual Direction: {actual_dir} | Correct: {is_correct} | Intraday Target Hit: {intraday_hit}\n\n"
        f"#### 3. HOURLY INTRADAY TAPE:\n{tape_table}\n\n"
        f"#### 4. OFFICIAL EVENING MARKET CLOSE BRIEF:\n{news_text}\n\n"
        "Diagnose the prediction using the specified schema."
    )

    resp_awaitable = client.chat.completions.create(
        model=OPENAI_MODEL,
        response_model=DailyPredictionDiagnosis,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        reasoning_effort="medium",
    )
    if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
        return await resp_awaitable
    return resp_awaitable


async def run_daily_postmortem(
    target_date: str | None = None,
    force: bool = False,
    client=None,
    luna_client=None,
) -> list[dict]:
    """Execute post-mortem analysis for evaluated daily predictions on target_date."""
    sb = client or get_supabase_client()
    luna = luna_client or get_luna_client()

    query = sb.table("daily_predictions").select("*").eq("status", "evaluated")
    if target_date:
        query = query.eq("target_date", target_date)
    else:
        # Default to the most recent evaluated target date
        latest_resp = (
            sb.table("daily_predictions")
            .select("target_date")
            .eq("status", "evaluated")
            .order("target_date", desc=True)
            .limit(1)
            .execute()
        )
        if not latest_resp.data:
            logger.info("No evaluated daily predictions found for post-mortem.")
            return []
        target_date = latest_resp.data[0]["target_date"]
        query = query.eq("target_date", target_date)

    response = query.execute()
    predictions = response.data or []
    if not predictions:
        logger.info(f"No evaluated predictions found for {target_date}.")
        return []

    # Filter out already evaluated unless forced
    pending_audit = [p for p in predictions if force or not p.get("postmortem_evaluated_at")]
    if not pending_audit:
        logger.info(f"All predictions for {target_date} already have post-mortems. Use force=True to re-run.")
        return []

    ticker = pending_audit[0].get("ticker", "SPY")
    rth_bars = await fetch_rth_bars_for_date(ticker, target_date)
    close_newsletter = await fetch_evening_newsletter_summary(sb, target_date)

    updated_records = []
    now_iso = datetime.now(UTC).isoformat()

    for pred in pending_audit:
        pred_id = pred["id"]
        model_name = pred.get("model_name", "unknown")
        try:
            diagnosis = await diagnose_daily_prediction(
                prediction=pred,
                rth_bars=rth_bars,
                close_newsletter=close_newsletter,
                luna_client=luna,
            )

            update_payload = {
                "postmortem_category": diagnosis.category.value,
                "postmortem_flawed_assumption": diagnosis.flawed_assumption,
                "postmortem_lesson": diagnosis.actionable_lesson,
                "was_predictable": diagnosis.was_predictable,
                "postmortem_evaluated_at": now_iso,
            }

            sb.table("daily_predictions").update(update_payload).eq("id", pred_id).execute()

            # Record memory if actionable and predictable
            if diagnosis.was_predictable and diagnosis.category != PostMortemCategory.ACCURATE_CAPTURE:
                try:
                    add_memory(
                        content=(
                            f"[{model_name.upper()} DAILY PREDICTOR POST-MORTEM ({target_date})] "
                            f"{diagnosis.actionable_lesson} (Category: {diagnosis.category.value})"
                        ),
                        memory_type="AUTORESEARCH_INSIGHT",
                        importance_score=8,
                        metadata={
                            "scope": "daily_predictor",
                            "track_id": model_name,
                            "model_name": model_name,
                            "target_date": target_date,
                            "postmortem_category": diagnosis.category.value,
                            "was_predictable": True,
                        },
                        check_similarity=True,
                    )
                except Exception as e:
                    logger.warning(f"Failed to record post-mortem memory for {pred_id}: {e}")

            updated_row = dict(pred)
            updated_row.update(update_payload)
            updated_records.append(updated_row)
            logger.info(
                f"Completed post-mortem for {model_name} on {target_date}: "
                f"Category={diagnosis.category.value}, Predictable={diagnosis.was_predictable}"
            )
        except Exception as e:
            logger.exception(f"Post-mortem diagnosis failed for prediction {pred_id} ({model_name}): {e}")

    return updated_records
