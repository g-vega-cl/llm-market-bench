"""Missed Gainers Post-Mortem Audit Module.

Analyzes daily, weekly (5D), and monthly (1M) market gainers against
Benchify internal prediction logs (decisions, trades, sector predictions).
Invokes gpt-5.6-luna with thinking to diagnose root causes and record
actionable lessons into long-term memory.
"""

from datetime import UTC, datetime, timedelta

import httpx
import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from core import config
from core.config import FMP_API_KEY, logger
from core.db import get_supabase_client
from memory.store import add_memory

FMP_BASE_URL = "https://financialmodelingprep.com/stable"
FMP_TIMEOUT = httpx.Timeout(10.0)

SECTOR_TICKERS = ["XLK", "SMH", "XLE", "XLF", "XLV", "XLY", "XLI", "XLB", "XLU", "XLRE", "XLC", "XOP", "XME", "XBI"]


class GainerItem(BaseModel):
    symbol: str
    name: str
    timeframe: str
    price: float
    change_pct: float
    sector: str | None = None
    market_cap: float | None = None
    volume: int | None = None


class PredictionAuditRecord(BaseModel):
    ticker: str
    found_in_decisions: bool
    signals_seen: list[str]
    decisions_summary: str
    found_in_trades: bool
    trades_summary: str
    sector_name: str | None = None
    sector_prediction_summary: str
    was_missed: bool


class MissedGainerDiagnosis(BaseModel):
    ticker: str
    timeframe: str
    return_pct: float
    actual_catalyst: str = Field(..., description="Primary driver of the move")
    predictability_score: int = Field(..., description="1-5 predictability score")
    missed_reason_category: str = Field(
        ...,
        description="One of: BLINDSPOT_CATALYST, EXCESSIVE_RISK_AVERSION, MOMENTUM_TIMIDITY, COVERAGE_GAP, UNPREDICTABLE_SURPRISE, PREMATURE_EXIT",
    )
    why_missed: str = Field(..., description="Why our models missed or faded it")
    actionable_lesson: str = Field(..., description="Concrete rule or heuristic for future models")


def get_diagnosis_openai_client():
    """Create an async OpenAI client wrapped with Instructor Mode.JSON to allow active thinking."""
    raw_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY, timeout=180)
    return instructor.from_openai(raw_client, mode=instructor.Mode.JSON)


async def fetch_top_gainers(
    timeframe: str = "daily",
    limit: int = 5,
    client: httpx.AsyncClient | None = None,
    api_key: str | None = None,
) -> list[GainerItem]:
    """Fetch top market gainers across daily, weekly (5D), or monthly (1M) horizons."""
    effective_key = api_key or FMP_API_KEY
    if not effective_key:
        logger.warning("FMP_API_KEY missing, skipping gainers fetch.")
        return []

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=FMP_TIMEOUT)
        should_close = True

    try:
        tf = timeframe.lower()
        if tf in ("daily", "1d"):
            resp = await client.get(f"{FMP_BASE_URL}/biggest-gainers", params={"apikey": effective_key})
            if resp.status_code != 200:
                logger.warning(f"FMP biggest-gainers returned status {resp.status_code}")
                return []
            raw_gainers = resp.json()
            # Filter liquid stocks: price >= 2.0 and non-empty symbol
            filtered = [
                GainerItem(
                    symbol=str(g["symbol"]).upper(),
                    name=str(g.get("name") or g["symbol"]),
                    timeframe="daily",
                    price=float(g.get("price") or 0.0),
                    change_pct=float(g.get("changesPercentage") or g.get("change") or 0.0),
                    volume=int(g["volume"]) if g.get("volume") is not None else None,
                )
                for g in raw_gainers
                if float(g.get("price") or 0.0) >= 2.0 and g.get("symbol")
            ]
            filtered.sort(key=lambda x: x.change_pct, reverse=True)
            return filtered[:limit]

        # Weekly (5D) or Monthly (1M) Screener
        resp_screener = await client.get(
            f"{FMP_BASE_URL}/company-screener",
            params={
                "marketCapMoreThan": 2000000000,
                "isActivelyTrading": "true",
                "limit": 40,
                "apikey": effective_key,
            },
        )
        if resp_screener.status_code != 200:
            logger.warning(f"FMP company-screener returned status {resp_screener.status_code}")
            return []

        screener_data = resp_screener.json()
        symbols = [s["symbol"] for s in screener_data if "symbol" in s]
        all_symbols = list(dict.fromkeys(symbols + SECTOR_TICKERS))

        resp_pc = await client.get(
            f"{FMP_BASE_URL}/stock-price-change",
            params={"symbol": ",".join(all_symbols[:45]), "apikey": effective_key},
        )
        if resp_pc.status_code != 200:
            logger.warning(f"FMP stock-price-change returned status {resp_pc.status_code}")
            return []

        pc_data = resp_pc.json()
        key = "5D" if tf in ("weekly", "5d") else "1M"
        tf_label = "weekly" if tf in ("weekly", "5d") else "monthly"

        items = []
        for item in pc_data:
            pct = item.get(key)
            if pct is not None:
                sym = str(item.get("symbol", "")).upper()
                items.append(
                    GainerItem(
                        symbol=sym,
                        name=sym,
                        timeframe=tf_label,
                        price=0.0,
                        change_pct=float(pct),
                    )
                )

        items.sort(key=lambda x: x.change_pct, reverse=True)
        return items[:limit]

    except Exception as e:
        logger.exception(f"Error fetching top gainers for timeframe '{timeframe}': {e}")
        return []
    finally:
        if should_close:
            await client.aclose()


async def fetch_recent_ticker_news(
    ticker: str,
    limit: int = 3,
    client: httpx.AsyncClient | None = None,
    api_key: str | None = None,
) -> list[str]:
    """Fetch recent headlines for target ticker to provide catalyst context."""
    effective_key = api_key or FMP_API_KEY
    if not effective_key:
        return []

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=FMP_TIMEOUT)
        should_close = True

    try:
        resp = await client.get(
            f"{FMP_BASE_URL}/news/stock",
            params={"symbols": ticker.upper(), "limit": limit, "apikey": effective_key},
        )
        if resp.status_code != 200:
            return []
        news_items = resp.json()
        headlines = []
        for n in news_items:
            title = n.get("title", "")
            date_str = n.get("publishedDate", "")
            if title:
                headlines.append(f"{title} ({date_str[:10]})" if date_str else title)
        return headlines
    except Exception as e:
        logger.warning(f"Failed to fetch stock news for {ticker}: {e}")
        return []
    finally:
        if should_close:
            await client.aclose()


async def audit_internal_predictions(ticker: str, timeframe: str, sb_client=None) -> PredictionAuditRecord:
    """Cross-reference ticker against internal decisions, trades, and sector predictions."""
    sb = sb_client or get_supabase_client()
    days = 2 if timeframe == "daily" else (7 if timeframe == "weekly" else 30)
    lookback = (datetime.now(UTC) - timedelta(days=days)).isoformat()

    dec_res = (
        sb.table("decisions")
        .select("ticker, signal, confidence, reasoning, model_name, created_at")
        .eq("ticker", ticker.upper())
        .gte("created_at", lookback)
        .execute()
    )
    decisions = dec_res.data or []

    trades_res = (
        sb.table("trades")
        .select("ticker, signal, price, quantity, executed_at")
        .eq("ticker", ticker.upper())
        .gte("executed_at", lookback)
        .execute()
    )
    trades = trades_res.data or []

    sector_res = (
        sb.table("sector_predictions")
        .select("predicted_sector, predicted_worst_sector, prediction_date")
        .order("prediction_date", desc=True)
        .limit(2)
        .execute()
    )
    sector_preds = sector_res.data or []

    signals = [d.get("signal", "").upper() for d in decisions if d.get("signal")]
    has_buy = any(s == "BUY" for s in signals)
    was_missed = not has_buy

    dec_summary = ""
    if decisions:
        parts = [
            f"{d.get('model_name')}: {d.get('signal')} (conf={d.get('confidence')}%) - {d.get('reasoning', '')[:120]}"
            for d in decisions[:3]
        ]
        dec_summary = "; ".join(parts)
    else:
        dec_summary = "Zero decisions recorded by any model."

    trades_summary = f"{len(trades)} executed trades recorded." if trades else "Zero executed trades."

    sector_summary = ""
    if sector_preds:
        top_sec = sector_preds[0].get("predicted_sector")
        worst_sec = sector_preds[0].get("predicted_worst_sector")
        sector_summary = f"Recent sector model predicted Top: {top_sec}, Worst: {worst_sec}."
    else:
        sector_summary = "No recent sector predictions found."

    return PredictionAuditRecord(
        ticker=ticker.upper(),
        found_in_decisions=len(decisions) > 0,
        signals_seen=signals,
        decisions_summary=dec_summary,
        found_in_trades=len(trades) > 0,
        trades_summary=trades_summary,
        sector_name=None,
        sector_prediction_summary=sector_summary,
        was_missed=was_missed,
    )


async def diagnose_missed_gainer(
    gainer: GainerItem,
    audit: PredictionAuditRecord,
    headlines: list[str] | None = None,
    client=None,
) -> MissedGainerDiagnosis:
    """Run gpt-5.6-luna with thinking to produce structured root cause diagnosis and lesson."""
    cl = client or get_diagnosis_openai_client()
    news_text = "\n".join([f"- {h}" for h in (headlines or [])]) or "No specific headline available."

    prompt_user = f"""AUDIT TARGET:
- Ticker: {gainer.symbol} ({gainer.name})
- Timeframe: {gainer.timeframe.upper()} move: +{gainer.change_pct:.1f}%
- Current / End Price: ${gainer.price:.2f}

RECENT NEWS / HEADLINES:
{news_text}

BENCHIFY SYSTEM INTERNAL RECORD:
- Decisions found: {audit.found_in_decisions} (Signals: {audit.signals_seen or "None"})
- Decisions Detail: {audit.decisions_summary}
- Trades executed: {audit.found_in_trades} ({audit.trades_summary})
- Sector Context: {audit.sector_prediction_summary}

QUESTION: Why didn't our models predict or capture this move?
Conduct an adversarial, candid audit diagnosing:
1. Root cause category (BLINDSPOT_CATALYST, EXCESSIVE_RISK_AVERSION, MOMENTUM_TIMIDITY, COVERAGE_GAP, UNPREDICTABLE_SURPRISE, PREMATURE_EXIT)
2. Predictability rating (1 to 5)
3. Actual catalyst driving the rally
4. Deep explanation of why our models missed or faded the move
5. Actionable lesson or screening rule for future models
"""

    resp_awaitable = cl.chat.completions.create(
        model=config.OPENAI_MODEL,
        response_model=MissedGainerDiagnosis,
        messages=[
            {
                "role": "system",
                "content": "You are Benchify's Chief Trading Auditor. You perform strict, adversarial post-mortems on why automated LLM trading models missed market winners.",
            },
            {"role": "user", "content": prompt_user},
        ],
        reasoning_effort="medium",
    )

    if hasattr(resp_awaitable, "__await__"):
        return await resp_awaitable
    return resp_awaitable


async def save_gainer_postmortem_memory(diagnosis: MissedGainerDiagnosis, sb_client=None) -> str | None:
    """Store postmortem into Supabase memories table with 7-day deduplication."""
    sb = sb_client or get_supabase_client()
    seven_days_ago = (datetime.now(UTC) - timedelta(days=7)).isoformat()

    existing = (
        sb.table("memories")
        .select("id")
        .filter("metadata->>ticker", "eq", diagnosis.ticker.upper())
        .filter("metadata->>timeframe", "eq", diagnosis.timeframe.lower())
        .filter("metadata->>type", "eq", "gainers_postmortem")
        .gte("created_at", seven_days_ago)
        .execute()
    )

    if existing.data:
        logger.info(
            f"Skipping duplicate gainers post-mortem memory for {diagnosis.ticker} ({diagnosis.timeframe}): already exists in last 7 days."
        )
        return None

    content = (
        f"[{diagnosis.timeframe.upper()} GAINER POST-MORTEM] {diagnosis.ticker} (+{diagnosis.return_pct:.1f}%): "
        f"{diagnosis.actionable_lesson} | ROOT CAUSE: {diagnosis.why_missed}"
    )

    metadata = {
        "ticker": diagnosis.ticker.upper(),
        "timeframe": diagnosis.timeframe.lower(),
        "return_pct": diagnosis.return_pct,
        "predictable_score": diagnosis.predictability_score,
        "category": diagnosis.missed_reason_category,
        "actual_catalyst": diagnosis.actual_catalyst,
        "type": "gainers_postmortem",
    }

    success = add_memory(
        content=content,
        memory_type="POST_MORTEM",
        importance_score=8,
        metadata=metadata,
        check_similarity=True,
    )
    if success:
        logger.info(f"Saved gainers post-mortem memory for {diagnosis.ticker} ({diagnosis.timeframe}).")
        return diagnosis.ticker
    return None


async def run_gainers_postmortem(
    timeframe: str = "all", limit: int = 3, save_memory: bool = True, sb_client=None
) -> list[MissedGainerDiagnosis]:
    """Orchestrate the full missed gainers audit pipeline across target timeframes."""
    timeframes = ["daily", "weekly", "monthly"] if timeframe.lower() == "all" else [timeframe.lower()]
    all_diagnoses = []
    sb = sb_client or get_supabase_client()

    for tf in timeframes:
        logger.info(f"Auditing top {limit} {tf} gainers...")
        gainers = await fetch_top_gainers(timeframe=tf, limit=limit)
        for g in gainers:
            audit = await audit_internal_predictions(g.symbol, tf, sb_client=sb)
            headlines = await fetch_recent_ticker_news(g.symbol, limit=3)
            try:
                diagnosis = await diagnose_missed_gainer(g, audit, headlines=headlines)
                all_diagnoses.append(diagnosis)
                print(f"\n[{tf.upper()} GAINER] {diagnosis.ticker} (+{diagnosis.return_pct:.1f}%)")
                print(
                    f"  • Category: {diagnosis.missed_reason_category} (Predictability: {diagnosis.predictability_score}/5)"
                )
                print(f"  • Catalyst: {diagnosis.actual_catalyst}")
                print(f"  • Why Missed: {diagnosis.why_missed}")
                print(f"  • Lesson: {diagnosis.actionable_lesson}")
                if save_memory:
                    saved = await save_gainer_postmortem_memory(diagnosis, sb_client=sb)
                    if saved:
                        print(f"  • Saved POST_MORTEM memory to Supabase for {diagnosis.ticker}")
            except Exception as e:
                logger.exception(f"Failed to diagnose missed gainer {g.symbol}: {e}")

    return all_diagnoses
