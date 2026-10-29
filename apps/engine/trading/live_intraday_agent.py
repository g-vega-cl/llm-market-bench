"""Live autonomous intraday agent trader and multi-tier LLM execution engine.

Pulls real-time 1m tape from Alpaca, calculates rolling technical snapshots (VWAP, RSI, EMA),
aggregates cross-source deduplicated news, pulls episodic memories, and queries local Strata
with automatic fallback to the CLVG free proxy.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from analysis.intraday_news_aggregator import aggregate_intraday_news
from core.config import (
    FMP_API_KEY,
    MASSIVE_API_KEY,
    logger,
)
from core.db import get_supabase_client

DEFAULT_STRATA_URL = os.getenv("STRATA_BASE_URL", "http://localhost:8080/v1")
DEFAULT_CHEAP_PROXY_URL = os.getenv("FREE_LLM_PROXY_URL", "https://llm.clvg.uk/v1")


def calculate_technical_snapshot(bars: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate rolling VWAP, RSI-14, and EMA-20/50 from intraday 1m bars."""
    if not bars:
        return {
            "vwap": 0.0,
            "rsi_14": 50.0,
            "ema_20": 0.0,
            "ema_50": 0.0,
            "last_close": 0.0,
            "trend": "NEUTRAL",
        }

    # 1. VWAP
    cum_vol = 0.0
    cum_pv = 0.0
    closes = []
    for b in bars:
        c = float(b["close"])
        h = float(b["high"])
        low_val = float(b["low"])
        v = float(b["volume"])
        typ = (h + low_val + c) / 3.0
        cum_pv += typ * v
        cum_vol += v
        closes.append(c)

    vwap = round(cum_pv / cum_vol, 2) if cum_vol > 0 else round(closes[-1], 2)
    last_close = closes[-1]

    # 2. RSI (14 periods)
    rsi_14 = 50.0
    if len(closes) >= 15:
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0.0 for d in deltas[-14:]]
        losses = [-d if d < 0 else 0.0 for d in deltas[-14:]]
        avg_gain = sum(gains) / 14.0
        avg_loss = sum(losses) / 14.0
        if avg_loss == 0.0:
            rsi_14 = 100.0 if avg_gain > 0 else 50.0
        else:
            rs = avg_gain / avg_loss
            rsi_14 = round(100.0 - (100.0 / (1.0 + rs)), 1)

    # 3. EMA 20
    k20 = 2.0 / (20.0 + 1.0)
    ema_20 = closes[0]
    for c in closes[1:]:
        ema_20 = (c * k20) + (ema_20 * (1.0 - k20))
    ema_20 = round(ema_20, 2)

    # Trend classification
    trend = "NEUTRAL"
    if last_close > vwap and last_close > ema_20:
        trend = "BULLISH"
    elif last_close < vwap and last_close < ema_20:
        trend = "BEARISH"

    return {
        "vwap": vwap,
        "rsi_14": rsi_14,
        "ema_20": ema_20,
        "last_close": last_close,
        "trend": trend,
    }


def _extract_json_decision(raw_text: str | None) -> dict[str, Any]:
    """Parse JSON trading decision from raw LLM output."""
    if not raw_text:
        return {"action": "HOLD", "conviction": 50, "thought": "No LLM output received.", "allocation_pct": 0}
    clean = raw_text.strip()
    if clean.startswith("```"):
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean)
        if match:
            clean = match.group(1).strip()

    try:
        return json.loads(clean)
    except Exception:
        match = re.search(r"(\{[\s\S]*\})", clean)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
    return {"action": "HOLD", "conviction": 50, "thought": clean[:250], "allocation_pct": 0}


async def query_multi_tier_llm(
    messages: list[dict[str, str]],
    strata_url: str = DEFAULT_STRATA_URL,
    cheap_proxy_url: str = DEFAULT_CHEAP_PROXY_URL,
    http_client: httpx.AsyncClient | None = None,
) -> str:
    """Query local Strata first, falling back cleanly to the free proxy."""
    should_close = False
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=20.0)
        should_close = True

    try:
        # Tier 1: Local Strata
        try:
            url_strata = f"{strata_url.rstrip('/')}/chat/completions"
            payload = {
                "model": os.getenv("STRATA_MODEL", "orcarouter-qwen3.8-flash-next-uncensored-iq3_xxs"),
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 600,
            }
            resp = await http_client.post(url_strata, json=payload, timeout=12.0)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            logger.warning(f"Strata returned status {resp.status_code}. Attempting fallback...")
        except Exception as e:
            logger.info(f"Strata unavailable or timed out ({e}). Cascading to fallback proxy...")

        # Tier 2: CLVG Free Proxy
        try:
            url_fallback = f"{cheap_proxy_url.rstrip('/')}/chat/completions"
            payload_fallback = {
                "model": os.getenv("FREE_PROXY_MODEL", "deepseek-chat"),
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 600,
            }
            resp = await http_client.post(url_fallback, json=payload_fallback, timeout=20.0)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            logger.warning(f"Fallback proxy returned status {resp.status_code}: {resp.text[:120]}")
        except Exception as e:
            logger.warning(f"Fallback proxy call failed: {e}")

        # Default fallback decision
        return json.dumps(
            {
                "action": "HOLD",
                "conviction": 50,
                "thought": "All LLM endpoints currently unavailable; holding neutral position.",
                "memories_consulted": [],
                "allocation_pct": 0,
            }
        )
    finally:
        if should_close:
            await http_client.aclose()


async def fetch_intraday_bars(
    alpaca_data_client: Any, ticker: str = "SPY", window_minutes: int = 120
) -> list[dict[str, Any]]:
    """Fetch rolling 120m 1m bars from Alpaca."""
    if not alpaca_data_client:
        return []
    try:
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame

        now_utc = datetime.now(UTC)
        req = StockBarsRequest(
            symbol_or_symbols=ticker,
            timeframe=TimeFrame.Minute,
            start=now_utc - timedelta(minutes=window_minutes + 60),
            limit=window_minutes + 30,
        )
        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(None, alpaca_data_client.get_stock_bars, req)
        bars = []
        if hasattr(resp, "data") and isinstance(resp.data, dict):
            bars = resp.data.get(ticker, [])
        elif isinstance(resp, dict) or hasattr(resp, "get"):
            bars = resp.get(ticker, [])
        elif hasattr(resp, "__getitem__"):
            try:
                bars = resp[ticker]
            except Exception:
                bars = []
        return [
            {
                "time": b.timestamp.isoformat() if hasattr(b.timestamp, "isoformat") else str(b.timestamp),
                "open": float(b.open),
                "high": float(b.high),
                "low": float(b.low),
                "close": float(b.close),
                "volume": float(b.volume),
            }
            for b in bars
        ]
    except Exception:
        logger.exception(f"Failed to fetch intraday bars for {ticker}")
        return []


async def fetch_active_candle(alpaca_data_client: Any, ticker: str = "SPY") -> dict[str, Any] | None:
    """Fetch the active forming 1m candle from Alpaca using Sort.DESC."""
    if not alpaca_data_client:
        return None
    try:
        from alpaca.common.enums import Sort
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame

        now_utc = datetime.now(UTC)
        req = StockBarsRequest(
            symbol_or_symbols=ticker,
            timeframe=TimeFrame.Minute,
            start=now_utc - timedelta(hours=2),
            sort=Sort.DESC,
            limit=1,
        )
        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(None, alpaca_data_client.get_stock_bars, req)
        bars = []
        if hasattr(resp, "data") and isinstance(resp.data, dict):
            bars = resp.data.get(ticker, [])
        elif isinstance(resp, dict) or hasattr(resp, "get"):
            bars = resp.get(ticker, [])
        elif hasattr(resp, "__getitem__"):
            try:
                bars = resp[ticker]
            except Exception:
                bars = []
        if not bars:
            return None
        b = bars[0]
        return {
            "time": b.timestamp.isoformat() if hasattr(b.timestamp, "isoformat") else str(b.timestamp),
            "open": float(b.open),
            "high": float(b.high),
            "low": float(b.low),
            "close": float(b.close),
            "volume": float(b.volume),
        }
    except Exception:
        logger.exception(f"Failed to fetch active candle for {ticker}")
        return None


async def execute_intraday_agent_step(
    alpaca_data_client: Any = None,
    alpaca_trading_client: Any = None,
    sb_client: Any = None,
    http_client: httpx.AsyncClient | None = None,
    ticker: str = "SPY",
    strata_url: str = DEFAULT_STRATA_URL,
    cheap_proxy_url: str = DEFAULT_CHEAP_PROXY_URL,
) -> dict[str, Any]:
    """Execute one 5-minute autonomous trading and reasoning turn."""
    sb = sb_client or get_supabase_client()

    # 1. Pull rolling 120m bars and calculate technical snapshot
    bars = await fetch_intraday_bars(alpaca_data_client, ticker=ticker, window_minutes=120)
    technicals = calculate_technical_snapshot(bars)

    # 2. Gather deduplicated news
    news_items = await aggregate_intraday_news(
        http_client=http_client,
        massive_api_key=MASSIVE_API_KEY,
        fmp_api_key=FMP_API_KEY,
        symbols=ticker,
        limit_per_source=5,
    )

    # 3. Fetch episodic memories
    memories: list[dict[str, Any]] = []
    try:
        mem_resp = sb.table("memories").select("id, content").order("created_at", desc=True).limit(5).execute()
        memories = mem_resp.data or []
    except Exception:
        logger.exception("Failed to query memories for intraday agent")

    # 4. Formulate lean prompt
    news_bullets = "\n".join([f"- [{n['source']}] {n['headline']}" for n in news_items[:5]]) or "- No breaking news"
    memory_bullets = (
        "\n".join([f"- [{m.get('id', '')}] {m.get('content', '')[:100]}" for m in memories[:3]]) or "- No prior lessons"
    )

    system_prompt = (
        "You are an autonomous intraday quantitative trader managing a paper portfolio in SPY.\n"
        "Analyze the technical tape, news catalysts, and past memories to form your 5-minute stance.\n"
        "Respond ONLY with valid JSON strictly matching this schema:\n"
        "{\n"
        '  "action": "BUY" | "SELL" | "HOLD",\n'
        '  "conviction": 0-100,\n'
        '  "thought": "2-3 concise sentences detailing your rationale.",\n'
        '  "allocation_pct": integer 0-25,\n'
        '  "memories_consulted": ["mem_id_1"]\n'
        "}"
    )

    user_prompt = (
        f"### {ticker} 120-MINUTE TAPE SNAPSHOT:\n"
        f"- Last Price: ${technicals['last_close']:.2f} | VWAP: ${technicals['vwap']:.2f}\n"
        f"- RSI(14): {technicals['rsi_14']} | Trend: {technicals['trend']}\n\n"
        f"### BREAKING HEADLINES:\n{news_bullets}\n\n"
        f"### RELEVANT LESSONS & EPISODIC MEMORIES:\n{memory_bullets}\n\n"
        "Decide your action, conviction, and reasoning."
    )

    raw_output = await query_multi_tier_llm(
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        strata_url=strata_url,
        cheap_proxy_url=cheap_proxy_url,
        http_client=http_client,
    )
    decision = _extract_json_decision(raw_output)

    # 5. Execute paper order if action is BUY or SELL
    order_id = None
    if decision.get("action") in ("BUY", "SELL") and alpaca_trading_client:
        try:
            account = alpaca_trading_client.get_account()
            cash = float(getattr(account, "cash", 10000.0) or 10000.0)
            alloc_pct = min(25, max(1, int(decision.get("allocation_pct", 5))))
            allocated_dollars = cash * (alloc_pct / 100.0)
            price = technicals["last_close"] or 580.0
            shares = max(1, int(allocated_dollars / price))

            from alpaca.trading.enums import OrderSide, TimeInForce
            from alpaca.trading.requests import MarketOrderRequest

            side = OrderSide.BUY if decision["action"] == "BUY" else OrderSide.SELL
            order_req = MarketOrderRequest(
                symbol=ticker,
                qty=shares,
                side=side,
                time_in_force=TimeInForce.DAY,
            )
            order_res = alpaca_trading_client.submit_order(order_req)
            order_id = getattr(order_res, "id", None)
            logger.info(f"Submitted Alpaca paper {decision['action']} order for {shares} {ticker} (ID: {order_id})")
        except Exception:
            logger.exception("Failed to submit Alpaca paper order")

    # 6. Persist step into market_feeling table
    sentiment_label = (
        "Accumulating Dips"
        if decision.get("action") == "BUY"
        else "Defensive Cash"
        if decision.get("action") == "HOLD"
        else "Reducing Risk"
    )
    market_direction = (
        "BULLISH" if decision.get("action") == "BUY" else "BEARISH" if decision.get("action") == "SELL" else "NEUTRAL"
    )

    trades_payload = {
        "action": decision.get("action"),
        "allocation_pct": decision.get("allocation_pct"),
        "order_id": str(order_id) if order_id else None,
        "technicals": technicals,
        "memories_consulted": decision.get("memories_consulted", []),
        "news_count": len(news_items),
        "bars_count": len(bars),
    }

    try:
        sb.table("market_feeling").insert(
            {
                "sentiment_label": sentiment_label,
                "sentiment_emoji": "⚡",
                "confidence_score": int(decision.get("conviction", 50)),
                "why_explanation": decision.get("thought", ""),
                "market_direction": market_direction,
                "primary_concern": f"RSI: {technicals['rsi_14']} | Trend: {technicals['trend']}",
                "secondary_concern": f"VWAP: ${technicals['vwap']:.2f}",
                "trades_summary": trades_payload,
                "model_used": "Strata / Cheap-LLM-Cascade",
            }
        ).execute()
    except Exception:
        logger.exception("Failed to persist intraday agent thought to market_feeling")

    return {
        "action": decision.get("action", "HOLD"),
        "conviction": int(decision.get("conviction", 50)),
        "thought": decision.get("thought", ""),
        "order_id": str(order_id) if order_id else None,
        "technicals": technicals,
    }
