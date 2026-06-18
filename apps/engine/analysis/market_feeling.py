import json
from datetime import UTC, datetime
from typing import Any

from core.config import MINIMAX_API_KEY, MINIMAX_MODEL, logger
from core.db import get_supabase_client
from core.llm import MiniMaxClient

f"""Market Feeling Analysis - LLM-driven market sentiment.

This module generates the "How I'm feeling and why" sentiment analysis
by calling MiniMax {MINIMAX_MODEL} with today's trading data (trades, lessons, memories).

The result is stored in the market_feeling table and is displayed on the Today page.
"""

MARKET_FEELING_PROMPT = """You are an expert AI market analyst observing the AI trading agents' decisions and reasoning.

CONTEXT:
You have access to the following data from today's trading session:
- Recent trades executed: {trades_summary}
- Trade attempts (some rejected - shows agent conviction even when execution failed): {attempts_summary}
- Lessons learned from past failures: {lessons}
- Market events and consensus: {events}
- Key decision reasoning: {reasoning}
- Financial newsletters received today:
{newsletters_summary}
- S&P 500 Market Health Barometer:
{barometer_summary}
- Active prediction market odds:
{prediction_markets_summary}
- Price swings of traded/proposed tickers:
{price_swings_summary}

TASK:
Analyze this data holistically and provide a market sentiment assessment.

Think step-by-step:
1. What is the overall tone of recent trades?
2. Are there rejected attempts that show strong agent conviction despite execution failure?
3. Are there any lessons that suggest caution or different positioning?
4. What market events and external newsletters/news are driving current decisions?
5. How does the S&P 500 valuation barometer and prediction market consensus support or contrast with the agents' actions?
6. What risks or opportunities are top-of-mind?

OUTPUT (JSON only, no markdown code blocks, no preamble, no postamble):
{{
  "sentiment_label": "string (2-4 words, e.g., 'Cautiously Optimistic', 'Risk-Off', 'Wait-and-See', 'Defensive', 'Opportunistic', 'Uncertain')",
  "sentiment_emoji": "string (single emoji that best represents the sentiment)",
  "confidence_score": 0-100 (how confident are you in this assessment based on available data - higher if more trades/lessons available),
  "why_explanation": "string (2-3 sentences explaining the reasoning behind this sentiment - be specific about what you're seeing in the trades, newsletters, barometer, and prediction markets)",
  "market_direction": "BULLISH|BEARISH|NEUTRAL",
  "primary_concern": "string (the most important risk or opportunity currently - be specific)",
  "secondary_concern": "string (secondary consideration)"
 }}"""

WEEKEND_MARKET_FEELING_PROMPT = """You are an expert AI market analyst preparing a weekend market sentiment summary.

CONTEXT:
You have access to the following data from the past week:
- Trades executed this week: {trades_summary}
- Trade attempts (some rejected - shows agent conviction even when execution failed): {attempts_summary}
- Lessons learned from past failures: {lessons}
- Market events and consensus: {events}
- Key decision reasoning from the week: {reasoning}
- Financial newsletters received this week:
{newsletters_summary}
- S&P 500 Market Health Barometer:
{barometer_summary}
- Active prediction market odds:
{prediction_markets_summary}
- Price swings of traded/proposed tickers:
{price_swings_summary}

TASK:
Provide a weekend recap sentiment assessment. This is a read-only analysis - no new trades will be executed until markets reopen.

Think step-by-step:
1. How did the week go overall in terms of trading outcomes?
2. Are there rejected attempts that show strong agent conviction despite execution failure?
3. What lessons from past failures are most relevant going into next week?
4. What market events and newsletters should I be thinking about for next week?
5. How does the S&P 500 valuation barometer and prediction market consensus support or contrast with the agents' actions?
6. What are the key risks and opportunities heading into the new week?

OUTPUT (JSON only, no markdown code blocks, no preamble, no postamble):
{{
  "sentiment_label": "string (2-4 words, e.g., 'Weekend Recap', 'Cautiously Optimistic', 'Risk-Off', 'Wait-and-See', 'Defensive', 'Opportunistic', 'Uncertain')",
  "sentiment_emoji": "string (single emoji that best represents the sentiment)",
  "confidence_score": 0-100 (how confident are you in this assessment based on available data - higher if more trades/lessons available),
  "why_explanation": "string (2-3 sentences explaining the reasoning behind this weekend recap - be specific about what happened in the trades, newsletters, barometer, and prediction markets)",
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
    now = datetime.now(UTC)
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
    trades_res = (
        sb_client.table("trades")
        .select("id, ticker, signal, quantity, price, total_cost, executed_at, portfolios(owner_id)")
        .gte("executed_at", start_date)
        .execute()
    )
    trades = trades_res.data or []

    # 2. Fetch memories (events, lessons, incentives)
    memories_res = sb_client.table("memories").select("*").gte("created_at", start_date).execute()
    memories = memories_res.data or []

    # Categorize memories
    lessons = [m for m in memories if m.get("memory_type") == "LESSON_LEARNED"]
    events = [m for m in memories if m.get("memory_type") in ("MARKET_EVENT", "GOVERNMENT_INCENTIVE")]

    # 3. Fetch decisions for reasoning context and separate executed vs rejected
    decisions_res = (
        sb_client.table("decisions")
        .select("id, ticker, signal, confidence, reasoning, model_name, status")
        .gte("created_at", start_date)
        .execute()
    )
    decisions = decisions_res.data or []

    # Separate executed trades (from decisions table) vs rejected attempts
    executed_from_decisions = [d for d in decisions if d.get("status") == "EXECUTED"]
    rejected_attempts = [d for d in decisions if d.get("status", "").startswith("REJECTED_")]

    # Also include trades from the trades table (executed trades)
    # Combine: trades from trades table + executed decisions = all executed activity
    executed_trades = trades + executed_from_decisions

    # Use all decisions for reasoning context (includes executed, rejected, and validated)
    all_decisions = decisions

    logger.info(
        f"Gathered {date_label} data: {len(executed_trades)} executed, {len(rejected_attempts)} rejected, {len(lessons)} lessons, {len(events)} events"
    )

    # 4. Fetch newsletters
    newsletters_res = (
        sb_client.table("newsletter_snapshots")
        .select("sender, subject, content, date")
        .gte("date", start_date)
        .order("date", desc=True)
        .execute()
    )
    newsletters = newsletters_res.data or []

    # 5. Fetch latest S&P 500 barometer
    barometer_res = sb_client.table("market_barometer_history").select("*").order("date", desc=True).limit(1).execute()
    barometer = barometer_res.data[0] if barometer_res.data else None

    # 6. Fetch active prediction market odds
    prediction_markets_res = (
        sb_client.table("prediction_market_snapshots")
        .select("*")
        .eq("is_active", True)
        .order("volume_usd", desc=True)
        .limit(5)
        .execute()
    )
    prediction_markets = prediction_markets_res.data or []

    # 7. Calculate price swings of traded/proposed tickers
    tickers = list(
        {t.get("ticker") for t in executed_trades if t.get("ticker")}
        | {d.get("ticker") for d in all_decisions if d.get("ticker")}
        | {d.get("ticker") for d in rejected_attempts if d.get("ticker")}
    )

    price_swings = {}
    if tickers:
        try:
            price_history_res = (
                sb_client.table("price_history")
                .select("ticker, price, fetched_at")
                .in_("ticker", tickers)
                .gte("fetched_at", start_date)
                .order("fetched_at", desc=True)
                .execute()
            )
            rows = price_history_res.data or []

            history_by_ticker = {}
            for row in rows:
                t = row.get("ticker")
                if t:
                    if t not in history_by_ticker:
                        history_by_ticker[t] = []
                    history_by_ticker[t].append(row)

            for ticker in tickers:
                t_rows = history_by_ticker.get(ticker, [])
                if not t_rows:
                    fallback_res = (
                        sb_client.table("price_history")
                        .select("price, fetched_at")
                        .eq("ticker", ticker)
                        .order("fetched_at", desc=True)
                        .limit(2)
                        .execute()
                    )
                    t_rows = fallback_res.data or []

                if len(t_rows) >= 2:
                    latest_price = float(t_rows[0]["price"])
                    oldest_price = float(t_rows[-1]["price"])
                    pct_change = ((latest_price - oldest_price) / oldest_price) * 100 if oldest_price > 0 else 0.0
                    price_swings[ticker] = {
                        "latest_price": latest_price,
                        "oldest_price": oldest_price,
                        "pct_change": pct_change,
                    }
                elif len(t_rows) == 1:
                    price_swings[ticker] = {
                        "latest_price": float(t_rows[0]["price"]),
                        "oldest_price": float(t_rows[0]["price"]),
                        "pct_change": 0.0,
                    }
                else:
                    price_swings[ticker] = {
                        "latest_price": 0.0,
                        "oldest_price": 0.0,
                        "pct_change": 0.0,
                    }
        except Exception as e:
            logger.warning(f"Failed to fetch price history swings: {e}")

    return {
        "trades": executed_trades,
        "memories": memories,
        "lessons": lessons,
        "events": events,
        "decisions": all_decisions,
        "rejected_attempts": rejected_attempts,
        "newsletters": newsletters,
        "barometer": barometer,
        "prediction_markets": prediction_markets,
        "price_swings": price_swings,
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


def build_attempts_summary(rejected_decisions: list[dict], weekend_mode: bool = False) -> str:
    """Build a summary of rejected trade attempts (shows agent conviction).

    These are decisions that were rejected for various reasons (margin, hallucination,
    liquidity, etc.) but show agent intent/conviction.
    """
    date_label = "this week" if weekend_mode else "today"
    if not rejected_decisions:
        return f"No rejected trade attempts {date_label}."

    rejected_buys = [d for d in rejected_decisions if d.get("signal", "").upper() == "BUY"]
    rejected_sells = [d for d in rejected_decisions if d.get("signal", "").upper() == "SELL"]

    # Group by rejection reason
    by_reason = {}
    for d in rejected_decisions:
        reason = d.get("status", "UNKNOWN").replace("REJECTED_", "")
        by_reason[reason] = by_reason.get(reason, 0) + 1

    parts = []

    if rejected_buys:
        tickers = [d["ticker"] for d in rejected_buys[:3]]
        parts.append(
            f"Rejected buys: {len(rejected_buys)} ({', '.join(tickers)}{'...' if len(rejected_buys) > 3 else ''})"
        )

    if rejected_sells:
        tickers = [d["ticker"] for d in rejected_sells[:3]]
        parts.append(
            f"Rejected sells: {len(rejected_sells)} ({', '.join(tickers)}{'...' if len(rejected_sells) > 3 else ''})"
        )

    if by_reason:
        reasons = ", ".join([f"{r}={c}" for r, c in by_reason.items()])
        parts.append(f"Reasons: {reasons}")

    return "; ".join(parts) if parts else f"No rejected trade attempts {date_label}."


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

        reasoning_parts.append(f"- {ticker}: {signal} (conf: {confidence}%) - {reasoning}...")

    return "\n".join(reasoning_parts) if reasoning_parts else f"No decisions made {date_label}."


def build_newsletters_summary(newsletters: list[dict], weekend_mode: bool = False) -> str:
    """Build a summary of newsletters."""
    date_label = "this week" if weekend_mode else "today"
    if not newsletters:
        return f"No newsletters received {date_label}."

    lines = []
    for i, ns in enumerate(newsletters[:10], 1):
        sender = ns.get("sender", "Unknown")
        subject = ns.get("subject", "No Subject")
        content_snippet = ns.get("content", "")[:200].replace("\n", " ").strip()
        lines.append(f"{i}. From: {sender} | Subject: {subject} | Snippet: {content_snippet}...")
    return "\n".join(lines)


def build_barometer_summary(barometer: dict | None) -> str:
    """Build a summary of the S&P 500 Market Health Barometer."""
    if not barometer:
        return "No S&P 500 Market Health Barometer data available."
    pe = barometer.get("pe_ratio")
    fwd_pe = barometer.get("forward_pe")
    pb = barometer.get("pb_ratio")
    ps = barometer.get("ps_ratio")
    surprise = barometer.get("earnings_surprise_momentum")

    pe_val = f"{float(pe):.2f}" if pe is not None else "N/A"
    fwd_pe_val = f"{float(fwd_pe):.2f}" if fwd_pe is not None else "N/A"
    pb_val = f"{float(pb):.2f}" if pb is not None else "N/A"
    ps_val = f"{float(ps):.2f}" if ps is not None else "N/A"
    surprise_val = f"{float(surprise):.1f}%" if surprise is not None else "N/A"

    return (
        f"S&P 500 Aggregate Metrics (Snapshot from {barometer.get('date', 'N/A')}):\n"
        f"- Trailing P/E: {pe_val}\n"
        f"- Forward P/E: {fwd_pe_val}\n"
        f"- P/B Ratio: {pb_val}\n"
        f"- P/S Ratio: {ps_val}\n"
        f"- Earnings Surprise Momentum: {surprise_val}"
    )


def build_prediction_markets_summary(prediction_markets: list[dict]) -> str:
    """Build a summary of active prediction market sentiment."""
    if not prediction_markets:
        return "No active prediction market sentiment data available."
    lines = []
    for i, pm in enumerate(prediction_markets, 1):
        yes_pct = float(pm.get("yes_odds") or 0) * 100
        no_pct = float(pm.get("no_odds") or 0) * 100
        lines.append(
            f"{i}. {pm['question']} ({pm['platform'].upper()}) - YES: {yes_pct:.1f}% / NO: {no_pct:.1f}% (Volume: ${pm.get('volume_usd', 0):,.2f})"
        )
    return "\n".join(lines)


def build_price_swings_summary(swings: dict[str, dict[str, Any]]) -> str:
    """Build a summary of calculated price swings."""
    if not swings:
        return "No price swings recorded for today's tickers."

    lines = []
    for ticker, data in sorted(swings.items()):
        pct = data["pct_change"]
        sign = "+" if pct >= 0 else ""
        lines.append(f"- {ticker}: ${data['latest_price']:.2f} ({sign}{pct:.2f}%)")
    return "\n".join(lines)


def build_prompt(data: dict[str, Any], weekend_mode: bool = False) -> str:
    """Build the market feeling prompt with today's (or week's) data.

    Args:
        data: Dict with trades, lessons, events, decisions, and rejected_attempts.
        weekend_mode: If True, uses the weekend prompt variant.

    Returns:
        Formatted prompt string.
    """
    trades_summary = build_trades_summary(data["trades"], weekend_mode)
    attempts_summary = build_attempts_summary(data.get("rejected_attempts", []), weekend_mode)
    lessons_summary = build_lessons_summary(data["lessons"])
    events_summary = build_events_summary(data["events"], weekend_mode)
    reasoning_summary = build_reasoning_summary(data["decisions"], weekend_mode)

    newsletters_summary = build_newsletters_summary(data.get("newsletters", []), weekend_mode)
    barometer_summary = build_barometer_summary(data.get("barometer"))
    prediction_markets_summary = build_prediction_markets_summary(data.get("prediction_markets", []))
    price_swings_summary = build_price_swings_summary(data.get("price_swings", {}))

    template = WEEKEND_MARKET_FEELING_PROMPT if weekend_mode else MARKET_FEELING_PROMPT

    return template.format(
        trades_summary=trades_summary,
        attempts_summary=attempts_summary,
        lessons=lessons_summary,
        events=events_summary,
        reasoning=reasoning_summary,
        newsletters_summary=newsletters_summary,
        barometer_summary=barometer_summary,
        prediction_markets_summary=prediction_markets_summary,
        price_swings_summary=price_swings_summary,
    )


async def analyze_market_feeling(weekend_mode: bool = False) -> dict[str, Any] | None:
    """Generate market feeling sentiment using MiniMax.

    This function:
    1. Gathers today's (or week's) trading data
    2. Calls MiniMax to generate sentiment analysis
    3. Stores the result in the market_feeling table
    4. Returns the created record

    Args:
        weekend_mode: If True, gathers week's data and uses weekend prompt variant.

    Returns:
        The created market_feeling record, or None if failed.
    """
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
        required_fields = [
            "sentiment_label",
            "sentiment_emoji",
            "confidence_score",
            "why_explanation",
            "market_direction",
            "primary_concern",
        ]
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

        # 6b. Prepare rejected attempts summary for storage
        rejected = data.get("rejected_attempts", [])
        rejected_buys = [d for d in rejected if d.get("signal", "").upper() == "BUY"]
        rejected_sells = [d for d in rejected if d.get("signal", "").upper() == "SELL"]

        attempts_summary = {
            "rejected_buys": len(rejected_buys),
            "rejected_sells": len(rejected_sells),
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
            "attempts_summary": attempts_summary,
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
    res = sb_client.table("market_feeling").select("*").order("created_at", desc=True).limit(1).execute()

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
    now = datetime.now(UTC)

    age_hours = (now - created_at).total_seconds() / 3600
    return age_hours > stale_threshold_hours
