import json
import logging
from datetime import datetime, timezone
from typing import Any

from core.config import logger, MINIMAX_API_KEY, MINIMAX_MODEL
from core.db import get_supabase_client
from core.llm import MiniMaxClient

"""Market Feeling Analysis - LLM-driven market sentiment.

This module generates the "How I'm feeling and why" sentiment analysis
by calling MiniMax {model} with today's trading data (trades, lessons, memories).

The result is stored in the market_feeling table and is displayed on the Today page.
""".format(model=MINIMAX_MODEL)

MARKET_FEELING_PROMPT = """You are an expert AI market analyst observing the AI trading agents' decisions and reasoning.

CONTEXT:
You have access to the following data from today's trading session:
- Recent trades executed: {trades_summary}
- Lessons learned from past failures: {lessons}
- Market events and consensus: {events}
- Key decision reasoning: {reasoning}

TASK:
Analyze this data holistically and provide a market sentiment assessment.

Think step-by-step:
1. What is the overall tone of recent trades?
2. Are there any lessons that suggest caution or different positioning?
3. What market events are driving current decisions?
4. What risks or opportunities are top-of-mind?

OUTPUT (JSON only, no markdown code blocks, no preamble, no postamble):
{{
  "sentiment_label": "string (2-4 words, e.g., 'Cautiously Optimistic', 'Risk-Off', 'Wait-and-See', 'Defensive', 'Opportunistic', 'Uncertain')",
  "sentiment_emoji": "string (single emoji that best represents the sentiment)",
  "confidence_score": 0-100 (how confident are you in this assessment based on available data - higher if more trades/lessons available),
  "why_explanation": "string (2-3 sentences explaining the reasoning behind this sentiment - be specific about what you're seeing)",
  "market_direction": "BULLISH|BEARISH|NEUTRAL",
  "primary_concern": "string (the most important risk or opportunity currently - be specific)",
  "secondary_concern": "string (secondary consideration)"
}}"""

WEEKEND_MARKET_FEELING_PROMPT = """You are an expert AI market analyst preparing a weekend market sentiment summary.

CONTEXT:
You have access to the following data from the past week:
- Trades executed this week: {trades_summary}
- Lessons learned from past failures: {lessons}
- Market events and consensus: {events}
- Key decision reasoning from the week: {reasoning}

TASK:
Provide a weekend recap sentiment assessment. This is a read-only analysis - no new trades will be executed until markets reopen.

Think step-by-step:
1. How did the week go overall in terms of trading outcomes?
2. What lessons from past failures are most relevant going into next week?
3. What market events should I be thinking about for next week?
4. What are the key risks and opportunities heading into the new week?

OUTPUT (JSON only, no markdown code blocks, no preamble, no postamble):
{{
  "sentiment_label": "string (2-4 words, e.g., 'Weekend Recap', 'Cautiously Optimistic', 'Risk-Off', 'Wait-and-See', 'Defensive', 'Opportunistic', 'Uncertain')",
  "sentiment_emoji": "string (single emoji that best represents the sentiment)",
  "confidence_score": 0-100 (how confident are you in this assessment based on available data - higher if more trades/lessons available),
  "why_explanation": "string (2-3 sentences explaining the reasoning behind this weekend recap - be specific about what happened this week)",
  "market_direction": "BULLISH|BEARISH|NEUTRAL",
  "primary_concern": "string (the most important risk or opportunity for next week - be specific)",
  "secondary_concern": "string (secondary consideration for next week)"
}}"""


async def gather_today_data(sb_client, weekend_mode: bool = False) -> dict[str, Any]:
    """Gather data for market feeling analysis.

    Args:
        sb_client: Supabase client.
        weekend_mode: If True, fetches the past week's data instead of just today.

    Returns:
        Dict with trades, lessons, events, and reasoning.
    """
    now = datetime.now(timezone.utc)
    est_date_str = now.strftime("%Y-%m-%d")

    if weekend_mode:
        from datetime import timedelta
        week_start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        start_date = f"{week_start}T00:00:00"
        date_label = "this week"
    else:
        start_date = f"{est_date_str}T00:00:00"
        date_label = "today"

    # 1. Fetch trades
    trades_res = sb_client.table("trades").select(
        "id, ticker, signal, quantity, price, total_cost, executed_at, portfolios(owner_id)"
    ).gte("executed_at", start_date).execute()
    trades = trades_res.data or []

    # 2. Fetch memories (events, lessons, incentives)
    memories_res = sb_client.table("memories").select("*").gte("created_at", start_date).execute()
    memories = memories_res.data or []

    # Categorize memories
    lessons = [m for m in memories if m.get("memory_type") == "LESSON_LEARNED"]
    events = [m for m in memories if m.get("memory_type") in ("MARKET_EVENT", "GOVERNMENT_INCENTIVE")]

    # 3. Fetch decisions for reasoning context
    decisions_res = sb_client.table("decisions").select(
        "id, ticker, signal, confidence, reasoning, model_name, status"
    ).gte("created_at", start_date).execute()
    decisions = decisions_res.data or []

    logger.info(f"Gathered {date_label} data: {len(trades)} trades, {len(lessons)} lessons, {len(events)} events, {len(decisions)} decisions")

    return {
        "trades": trades,
        "memories": memories,
        "lessons": lessons,
        "events": events,
        "decisions": decisions,
    }


def build_trades_summary(trades: list[dict], weekend_mode: bool = False) -> str:
    """Build a human-readable summary of trades."""
    date_label = "this week" if weekend_mode else "today"
    if not trades:
        return f"No trades executed {date_label}."

    buys = [t for t in trades if t.get("signal", "").upper() == "BUY"]
    sells = [t for t in trades if t.get("signal", "").upper() == "SELL"]

    total_value = sum(t.get("total_cost", 0) for t in trades)

    summary_parts = []
    summary_parts.append(f"Total trades: {len(trades)} ({len(buys)} buys, {len(sells)} sells)")
    summary_parts.append(f"Total value: ${total_value:,.2f}")

    if buys:
        buy_tickers = [t["ticker"] for t in buys[:5]]
        summary_parts.append(f"Buy orders: {', '.join(buy_tickers)}{'...' if len(buys) > 5 else ''}")

    if sells:
        sell_tickers = [t["ticker"] for t in sells[:5]]
        summary_parts.append(f"Sell orders: {', '.join(sell_tickers)}{'...' if len(sells) > 5 else ''}")

    return "; ".join(summary_parts)


def build_lessons_summary(lessons: list[dict]) -> str:
    """Build a summary of lessons learned."""
    if not lessons:
        return "No lessons learned available."

    lesson_summaries = []
    for lesson in lessons[:5]:  # Limit to 5 most recent
        content = lesson.get("content", "")[:200]  # Truncate long content
        lesson_summaries.append(f"- {content}")

    return "\n".join(lesson_summaries) if lesson_summaries else "No lessons learned available."


def build_events_summary(events: list[dict], weekend_mode: bool = False) -> str:
    """Build a summary of market events."""
    date_label = "this week" if weekend_mode else "today"
    if not events:
        return f"No market events recorded {date_label}."

    event_summaries = []
    for event in events[:5]:  # Limit to 5 most recent
        content = event.get("content", "")[:200]
        event_summaries.append(f"- {content}")

    return "\n".join(event_summaries) if event_summaries else f"No market events recorded {date_label}."


def build_reasoning_summary(decisions: list[dict], weekend_mode: bool = False) -> str:
    """Build a summary of key decision reasoning."""
    date_label = "this week" if weekend_mode else "today"
    if not decisions:
        return f"No decisions made {date_label}."

    reasoning_parts = []
    for decision in decisions[:10]:  # Limit to 10 most recent
        ticker = decision.get("ticker", "Unknown")
        signal = decision.get("signal", "Unknown")
        confidence = decision.get("confidence", 0)
        reasoning = decision.get("reasoning", "No reasoning")[:150]

        reasoning_parts.append(
            f"- {ticker}: {signal} (conf: {confidence}%) - {reasoning}..."
        )

    return "\n".join(reasoning_parts) if reasoning_parts else f"No decisions made {date_label}."


def build_prompt(data: dict[str, Any], weekend_mode: bool = False) -> str:
    """Build the market feeling prompt with today's (or week's) data.

    Args:
        data: Dict with trades, lessons, events, and decisions.
        weekend_mode: If True, uses the weekend prompt variant.

    Returns:
        Formatted prompt string.
    """
    trades_summary = build_trades_summary(data["trades"], weekend_mode)
    lessons_summary = build_lessons_summary(data["lessons"])
    events_summary = build_events_summary(data["events"], weekend_mode)
    reasoning_summary = build_reasoning_summary(data["decisions"], weekend_mode)

    template = WEEKEND_MARKET_FEELING_PROMPT if weekend_mode else MARKET_FEELING_PROMPT

    return template.format(
        trades_summary=trades_summary,
        lessons=lessons_summary,
        events=events_summary,
        reasoning=reasoning_summary,
    )


async def analyze_market_feeling(weekend_mode: bool = False) -> dict[str, Any] | None:
    """Generate market feeling sentiment using MiniMax.

    This function:
    1. Gathers today's (or week's) trading data
    2. Calls MiniMax {model} to generate sentiment analysis
    3. Stores the result in the market_feeling table
    4. Returns the created record

    Args:
        weekend_mode: If True, gathers week's data and uses weekend prompt variant.

    Returns:
        The created market_feeling record, or None if failed.
    """.format(model=MINIMAX_MODEL)
    mode_label = "weekend" if weekend_mode else "daily"
    logger.info(f"Starting {mode_label} market feeling analysis with MiniMax {MINIMAX_MODEL}...")

    sb_client = get_supabase_client()

    # 1. Gather data
    data = await gather_today_data(sb_client, weekend_mode=weekend_mode)

    trades_count = len(data["trades"])
    lessons_count = len(data["lessons"])
    memories_count = len(data["events"])
    decisions_count = len(data["decisions"])

    date_label = "week" if weekend_mode else "day"
    logger.info(
        f"Market feeling data ({date_label}): {trades_count} trades, {lessons_count} lessons, "
        f"{memories_count} events, {decisions_count} decisions"
    )

    # 2. Check if we have enough data to analyze
    if trades_count == 0 and decisions_count == 0 and lessons_count == 0:
        logger.warning("No data available for market feeling analysis. Skipping.")
        return None

    # 3. Build prompt
    prompt = build_prompt(data, weekend_mode=weekend_mode)

    # 4. Call MiniMax
    if not MINIMAX_API_KEY:
        logger.error("MINIMAX_API_KEY not configured. Cannot analyze market feeling.")
        return None

    try:
        minimax = MiniMaxClient(api_key=MINIMAX_API_KEY)

        messages = [
            {"role": "system", "name": "MiniMax AI", "content": "You are an expert AI market analyst."},
            {"role": "user", "name": "User", "content": prompt},
        ]

        logger.info(f"Calling MiniMax {MINIMAX_MODEL} for market sentiment...")
        result = await minimax.chat_with_json_response(
            messages=messages,
            temperature=0.4,  # Lower for more consistent structured output
            max_completion_tokens=1024,
        )

        await minimax.close()

        logger.info(f"MiniMax response: {json.dumps(result, indent=2)[:500]}")

        # 5. Validate response structure
        required_fields = ["sentiment_label", "sentiment_emoji", "confidence_score",
                          "why_explanation", "market_direction", "primary_concern"]
        for field in required_fields:
            if field not in result:
                logger.error(f"MiniMax response missing required field: {field}")
                return None

        # 6. Prepare trades summary for storage
        buys = [t for t in data["trades"] if t.get("signal", "").upper() == "BUY"]
        sells = [t for t in data["trades"] if t.get("signal", "").upper() == "SELL"]
        total_value = sum(t.get("total_cost", 0) for t in data["trades"])

        trades_summary = {
            "buys": len(buys),
            "sells": len(sells),
            "total_value": total_value,
        }

        # 7. Store in market_feeling table (upsert - keep history, 30-day retention handled by cleanup)
        record = {
            "sentiment_label": result["sentiment_label"],
            "sentiment_emoji": result.get("sentiment_emoji", "🤔"),
            "confidence_score": result.get("confidence_score", 50),
            "why_explanation": result.get("why_explanation", ""),
            "market_direction": result.get("market_direction", "NEUTRAL"),
            "primary_concern": result.get("primary_concern", ""),
            "secondary_concern": result.get("secondary_concern", ""),
            "trades_summary": trades_summary,
            "lessons_incorporated": lessons_count,
            "memories_incorporated": memories_count,
            "model_used": MINIMAX_MODEL,
            "processing_time_ms": result.get("processing_time_ms"),
            "input_tokens": result.get("usage", {}).get("input_tokens"),
            "output_tokens": result.get("usage", {}).get("output_tokens"),
        }

        insert_res = sb_client.table("market_feeling").insert(record).execute()

        if insert_res.data:
            created_record = insert_res.data[0]
            logger.info(f"Market feeling stored: {created_record['id']}")
            logger.info(
                f"Sentiment: {created_record['sentiment_label']} {created_record['sentiment_emoji']} "
                f"(confidence: {created_record['confidence_score']}%)"
            )
            return created_record
        else:
            logger.error("Failed to insert market feeling record")
            return None

    except Exception as e:
        logger.error(f"Market feeling analysis failed: {repr(e)}")
        return None


async def get_latest_market_feeling() -> dict[str, Any] | None:
    """Fetch the most recent market feeling from the database.

    Returns:
        The latest market_feeling record, or None if not found.
    """
    sb_client = get_supabase_client()
    res = sb_client.table("market_feeling").select("*").order(
        "created_at", desc=True
    ).limit(1).execute()

    return res.data[0] if res.data else None


def is_market_feeling_stale(feeling: dict[str, Any], stale_threshold_hours: int = 4) -> bool:
    """Check if a market feeling record is stale.

    Args:
        feeling: The market_feeling record.
        stale_threshold_hours: Hours after which the feeling is considered stale.

    Returns:
        True if the feeling is stale, False otherwise.
    """
    if not feeling or not feeling.get("created_at"):
        return True

    created_at = datetime.fromisoformat(feeling["created_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)

    age_hours = (now - created_at).total_seconds() / 3600
    return age_hours > stale_threshold_hours