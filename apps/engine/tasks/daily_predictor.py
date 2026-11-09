from __future__ import annotations

import asyncio
import contextlib
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import (
    DEEPSEEK_FLASH_MODEL,
    JEV_MODEL,
    MINIMAX_MODEL,
    OPENROUTER_API_KEY,
    logger,
)
from core.db import get_supabase_client
from core.llm.clients import close_client, get_deepseek_client
from core.llm.daily_predictor_prompts import (
    DAILY_PREDICTOR_PROMPT,
    HOLD_CONFIDENCE_THRESHOLD,
    JEV_DEFAULT_CRITERIA,
    JEV_PREDICTOR_INSTRUCTIONS,
    JEV_PREDICTOR_QUESTION_KEY,
    JEV_PREDICTOR_QUESTION_TYPE,
    DailyPredictionOutput,
    apply_confidence_hold_gate,
    format_jev_curated_prompt_content,
    format_jev_prompt_content,
    format_laya_curated_prompt_content,
    parse_jev_curated_prompt_content,
    parse_jev_prompt_content,
    parse_laya_curated_prompt_content,
    split_daily_predictor_prompt,
)
from core.llm.minimax import MiniMaxClient
from local_autoresearch.document_builder import (
    DEFAULT_INGESTION_SYSTEM_PROMPT,
    generate_daily_document,
)
from local_autoresearch.laya_client import evaluate_with_laya
from local_autoresearch.manifest import DataManifest, JevCriteriaConfig, pack_daily_context


def get_ny_now() -> datetime:
    """Helper to return current New York datetime."""
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        return datetime.now()


async def predict_daily_with_jev(
    context: str,
    criteria: dict[str, str] | None = None,
    ticker: str = "SPY",
    model_name: str = JEV_MODEL,
) -> dict:
    """Execute intraday decision prediction using Jev on OpenRouter Decisions API."""
    key = OPENROUTER_API_KEY
    if not key:
        raise ValueError("OPENROUTER_API_KEY is not set. Cannot run Jev prediction.")

    crit = criteria or JEV_DEFAULT_CRITERIA
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "state": {
            "ticker": ticker.upper(),
            "market_context": context,
        },
        "questions": {
            JEV_PREDICTOR_QUESTION_KEY: {
                "type": JEV_PREDICTOR_QUESTION_TYPE,
                "instructions": JEV_PREDICTOR_INSTRUCTIONS,
                "criteria": {
                    "UP": crit.get("UP", JEV_DEFAULT_CRITERIA["UP"]),
                    "DOWN": crit.get("DOWN", JEV_DEFAULT_CRITERIA["DOWN"]),
                },
            }
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post("https://openrouter.ai/api/alpha/decisions", headers=headers, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"OpenRouter Decisions API error {resp.status_code}: {resp.text}")
        data = resp.json()

    answers = data.get("answers", {})
    dir_ans = answers.get(JEV_PREDICTOR_QUESTION_KEY, {})
    choice = str(dir_ans.get("choice", "UP")).upper()
    probabilities = dir_ans.get("probabilities", {})
    prob = float(probabilities.get(choice, dir_ans.get("confidence", 0.5)))
    confidence = round(prob * 100.0, 1) if prob <= 1.0 else round(prob, 1)

    rationale = (
        f"Jev System One decision: {choice} (P={prob:.2f}, "
        f"confidence={dir_ans.get('confidence', 0):.2f}, "
        f"distribution={probabilities})"
    )

    return {
        "predicted_direction": choice,
        "confidence": confidence,
        "expected_return_pct": 0.0,
        "rationale": rationale,
        "catalysts": [],
    }


async def seed_daily_predictor_prompt(model_name: str = DEEPSEEK_FLASH_MODEL) -> tuple[str, str]:
    """Seed the prompt/criteria as the active live baseline for a specific model in Supabase."""
    client = get_supabase_client()
    today = datetime.now(UTC).date()
    tag = f"daily-pred-seeded-{model_name}"

    is_laya_curated = "laya" in model_name.lower()
    is_jev_curated = not is_laya_curated and (
        "local" in model_name.lower() or "curated" in model_name.lower() or "four-regime" in model_name.lower()
    )
    is_jev = "jev" in model_name.lower() and not is_jev_curated
    if is_laya_curated:
        prompt_content = format_laya_curated_prompt_content(
            DEFAULT_INGESTION_SYSTEM_PROMPT, JEV_DEFAULT_CRITERIA, min_confidence=0.0
        )
        change_desc = f"Seeded baseline ingestion prompt and decision criteria for {model_name}."
    elif is_jev_curated:
        prompt_content = format_jev_curated_prompt_content(
            JEV_DEFAULT_CRITERIA, min_confidence=0.0, manifest=DataManifest().model_dump()
        )
        change_desc = f"Seeded baseline decision criteria and curated manifest for {model_name}."
    elif is_jev:
        prompt_content = format_jev_prompt_content(JEV_DEFAULT_CRITERIA)
        change_desc = f"Seeded baseline decision criteria for {model_name}."
    else:
        prompt_content = DAILY_PREDICTOR_PROMPT
        change_desc = f"Seeded baseline predictor prompt for {model_name}."

    try:
        # Demote previous active/baseline live predictor prompts for this track to saved
        client.table("prompt_experiments").update({"status": "saved"}).eq("prompt_name", "DAILY_PREDICTOR_PROMPT").eq(
            "track_id", model_name
        ).eq("status", "active").execute()

        # Insert new seeded prompt as active baseline
        client.table("prompt_experiments").insert(
            {
                "variant_tag": tag,
                "prompt_name": "DAILY_PREDICTOR_PROMPT",
                "prompt_content": prompt_content,
                "track_id": model_name,
                "week_start": today.isoformat(),
                "week_end": (today + timedelta(days=7)).isoformat(),
                "status": "active",
                "experiment_type": "baseline",
                "change_description": change_desc,
            }
        ).execute()

        logger.info(f"Successfully seeded and deployed live active prompt variant for {model_name}: {tag}")
        return tag, prompt_content
    except Exception as e:
        logger.error(f"Error seeding daily predictor prompt for {model_name}: {e}")

    return tag, prompt_content


async def fetch_active_daily_prompt(model_name: str = DEEPSEEK_FLASH_MODEL) -> tuple[str, str]:
    """Fetch active DAILY_PREDICTOR_PROMPT for a specific model track from database, or bootstrap baseline."""
    client = get_supabase_client()
    try:
        # 1. Try track-specific active prompt
        response = (
            client.table("prompt_experiments")
            .select("variant_tag, prompt_content")
            .eq("prompt_name", "DAILY_PREDICTOR_PROMPT")
            .eq("track_id", model_name)
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0]["variant_tag"], response.data[0]["prompt_content"]

        # 2. Try track-specific baseline prompt
        baseline_resp = (
            client.table("prompt_experiments")
            .select("variant_tag, prompt_content")
            .eq("prompt_name", "DAILY_PREDICTOR_PROMPT")
            .eq("track_id", model_name)
            .eq("status", "baseline")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if baseline_resp.data:
            return baseline_resp.data[0]["variant_tag"], baseline_resp.data[0]["prompt_content"]

        logger.info(f"No active DAILY_PREDICTOR_PROMPT found for {model_name}. Seeding baseline...")
        return await seed_daily_predictor_prompt(model_name=model_name)
    except Exception as e:
        logger.error(f"Error fetching active daily predictor prompt for {model_name}: {e}")

    default_content = (
        format_jev_prompt_content(JEV_DEFAULT_CRITERIA) if "jev" in model_name.lower() else DAILY_PREDICTOR_PROMPT
    )
    return f"fallback-daily-{model_name}", default_content


async def _append_calendar_and_newsletters(
    ticker: str,
    today_str: str,
    include_full_prior_close: bool,
    context_lines: list[str],
    data_record: dict[str, Any],
) -> None:
    from core.llm.handlers.base import execute_tool
    from core.llm.tools import execute_fetch_daily_newsletter_tool

    try:
        econ_summary = await execute_tool(
            "get_today_economic_releases",
            {"target_date": today_str, "country": "US"},
            model_name="daily_predictor",
        )
        if econ_summary and not econ_summary.startswith(("Error", "No scheduled")):
            context_lines.append(econ_summary)
            data_record["economic_calendar"] = econ_summary
    except Exception as e:
        logger.warning(f"Error fetching today's economic releases for daily predictor: {e}")

    try:
        cal_str = await execute_tool(
            "get_calendar_scenario_analysis",
            {"timeframe": "tomorrow", "ticker": ticker, "min_importance": 6, "detail": False},
            model_name="daily_predictor",
        )
        if cal_str and not cal_str.startswith("Error"):
            context_lines.append(f"Upcoming High-Impact Catalysts & Scenarios:\n{cal_str}")
    except Exception as e:
        logger.warning(f"Error fetching forward calendar scenarios for daily predictor: {e}")

    try:
        prior_close_str = await execute_fetch_daily_newsletter_tool(
            session="close", include_full_content=include_full_prior_close
        )
        if prior_close_str and not prior_close_str.startswith(("Error", "No generated")):
            context_lines.append(f"Previous Session Close Briefing:\n{prior_close_str}")
    except Exception as e:
        logger.warning(f"Error fetching previous close newsletter briefing: {e}")

    try:
        open_newsletter_str = await execute_fetch_daily_newsletter_tool(
            session="open", target_date=today_str, include_full_content=True
        )
        if open_newsletter_str and not open_newsletter_str.startswith(("Error", "No generated")):
            context_lines.append(f"Morning Newsletter Briefing:\n{open_newsletter_str}")
            data_record["synthetic_newsletter"] = open_newsletter_str
    except Exception as e:
        logger.warning(f"Error fetching morning newsletter briefing: {e}")


async def _append_premarket_and_trend_context(
    ticker: str,
    today_str: str,
    context_lines: list[str],
    data_record: dict[str, Any],
) -> None:
    from execution.market_data import MarketDataManager

    try:
        mdm = MarketDataManager()
        is_pm = await mdm.is_premarket()
        context_lines.append(
            "=== LIVE PRE-MARKET ACTION & GAP ANALYSIS ==="
            if is_pm
            else "=== LIVE SESSION / OVERNIGHT GAP ANALYSIS ==="
        )

        pm_quote = await mdm.get_premarket_quote(ticker)
        if pm_quote:
            asset_label = f"Target Asset ({ticker})" if is_pm else "Live Pre-Market / Early Session Quote"
            context_lines.append(
                f"{asset_label}: ${pm_quote['price']:.2f} | "
                f"Overnight Gap: {pm_quote['change']:+.2f} ({pm_quote['change_pct']:+.2f}%) vs Prev Close ${pm_quote['previous_close']:.2f}"
            )
        else:
            logger.warning(f"Could not retrieve live pre-market/session quote for target asset {ticker}")

        macro_proxies = [
            ("QQQ", "Nasdaq 100"),
            ("DIA", "Dow Jones"),
            ("IWM", "Russell 2000"),
            ("EWJ", "Japan MSCI"),
            ("VGK", "Europe FTSE"),
            ("TLT", "20+yr Treasury / Long Yields"),
            ("IEF", "7-10yr Treasury / Intermediate Yields"),
            ("GLD", "Gold"),
            ("USO", "WTI Crude Oil"),
            ("UUP", "US Dollar Index"),
        ]
        active_proxies = [(sym, label) for sym, label in macro_proxies if sym != ticker]
        proxy_quotes = await asyncio.gather(
            *[mdm.get_premarket_quote(sym) for sym, _ in active_proxies], return_exceptions=True
        )
        proxy_lines: list[str] = []
        proxies_map: dict[str, dict[str, float]] = {}
        for (sym, label), q in zip(active_proxies, proxy_quotes, strict=False):
            if isinstance(q, dict) and q.get("price") is not None and q.get("change_pct") is not None:
                proxy_lines.append(f"- {sym} ({label}): ${q['price']:.2f} | Overnight Gap: {q['change_pct']:+.2f}%")
                proxies_map[sym] = {"price": float(q["price"]), "change_pct": float(q["change_pct"])}
            elif isinstance(q, Exception):
                logger.debug(f"Failed to fetch pre-market quote for proxy {sym}: {q}")
        data_record["proxies"] = proxies_map
        if proxy_lines:
            context_lines.append(
                "Pre-Market Benchmark Indices & Key Macro Drivers (Live Overnight Gaps):"
                if is_pm
                else "Benchmark Indices & Key Macro Drivers (Live Overnight Gaps):"
            )
            context_lines.extend(proxy_lines)
        context_lines.append("=============================================")

        history = await mdm.get_history(ticker, days=45)
        from analytics.trend_profile import compute_trend_profile

        trend_prof = compute_trend_profile(history, target_date=today_str)
        if trend_prof.is_available:
            context_lines.extend(trend_prof.summary_lines)
            data_record["trend_vector"] = trend_prof.as_dict()

        await _append_intraday_profile(ticker, context_lines, data_record)
    except Exception as e:
        logger.warning(
            f"Error fetching technical indicators & pre-market quote via MarketDataManager for {ticker}: {e}"
        )


async def _append_intraday_profile(ticker: str, context_lines: list[str], data_record: dict[str, Any]) -> None:
    try:
        from analytics.intraday_profile import get_intraday_movement_report

        intra_rep = await get_intraday_movement_report(
            ticker=ticker, date_str="latest_completed", include_hourly_tape=False
        )
        md = intra_rep.get("markdown") if intra_rep else None
        if md and not md.startswith(("Error", "No intraday")):
            context_lines.append(md)
            data_record["intraday_profile"] = md
    except Exception as e:
        logger.debug(f"Could not retrieve prior intraday movement profile for {ticker}: {e}")


async def _append_macro_and_options_context(ticker: str, context_lines: list[str], data_record: dict[str, Any]) -> None:
    from core.llm.handlers.base import execute_tool

    try:
        options_str = await execute_tool(
            "get_macro_options_sentiment", {"primary_ticker": ticker}, model_name="daily_predictor"
        )
        if options_str and not options_str.startswith(("Error", "No options", "No macro options")):
            context_lines.append(f"Options Derivatives Positioning ({ticker}):\n{options_str}")
            data_record["options_sentiment"] = options_str
        elif options_str and options_str.startswith("Error"):
            logger.warning(f"Options derivatives retrieval returned error for {ticker}: {options_str}")
    except Exception as e:
        logger.warning(f"Error fetching options derivatives context for {ticker}: {e}")

    tool_specs = [
        ("get_global_macro_context", {}, "Prior Session Macro Baseline", None, None),
        ("get_volatility_index_details", {"lookback_days": 90}, "Volatility Index Details", None, None),
        ("get_market_health_barometer", {"limit": 5}, "Market Health Barometer", "market_barometer", None),
        ("get_market_feeling", {}, "Recent Market Feeling", "market_feeling", 500),
    ]
    for tool_name, args, header, record_key, max_len in tool_specs:
        try:
            res_str = await execute_tool(tool_name, args, model_name="daily_predictor")
            if res_str and not res_str.startswith("Error"):
                snippet = res_str[:max_len] if max_len else res_str
                context_lines.append(f"{header}:\n{snippet}")
                if record_key:
                    data_record[record_key] = res_str
        except Exception as e:
            logger.warning(f"Error fetching {tool_name}: {e}")


def _populate_recent_newsletters_manifest(data_record: dict[str, Any]) -> None:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    try:
        sb = get_supabase_client()
        cutoff = (datetime.now(UTC) - timedelta(hours=36)).isoformat()
        ns_resp = (
            sb.table("newsletter_snapshots")
            .select("sender, subject, content_clean")
            .gte("received_at", cutoff)
            .order("received_at", desc=True)
            .limit(50)
            .execute()
        )
        if ns_resp and hasattr(ns_resp, "data") and ns_resp.data:
            data_record["newsletters"] = [
                {
                    "sender": item.get("sender", "Unknown"),
                    "subject": item.get("subject", ""),
                    "content": item.get("content_clean", ""),
                }
                for item in ns_resp.data
            ]
    except Exception as e:
        logger.debug(f"Could not load recent newsletter snapshots for curated data manifest: {e}")


async def get_structured_daily_market_context(
    ticker: str = "SPY", include_full_prior_close: bool = False
) -> tuple[str, dict[str, Any]]:
    """Fetch recent market data context and structured data record for curated models."""
    from core.time_utils import get_current_day_info

    day_info = get_current_day_info()
    context_lines = [
        f"Asset: {ticker} (S&P 500 ETF)",
        f"=== EXACT TEMPORAL CONTEXT ===\n{day_info}\n==============================",
    ]
    today_str = datetime.now(UTC).date().isoformat()
    data_record: dict[str, Any] = {
        "target_date": today_str,
        "ticker": ticker.upper(),
        "economic_calendar": None,
        "synthetic_newsletter": None,
        "newsletters": [],
        "proxies": {},
        "options_sentiment": None,
        "intraday_profile": None,
        "market_barometer": None,
        "market_feeling": None,
        "trend_vector": None,
    }

    await _append_calendar_and_newsletters(ticker, today_str, include_full_prior_close, context_lines, data_record)
    await _append_premarket_and_trend_context(ticker, today_str, context_lines, data_record)
    await _append_macro_and_options_context(ticker, context_lines, data_record)
    _populate_recent_newsletters_manifest(data_record)

    context_lines.append(f"Prediction Target Date: {today_str}")
    return "\n".join(context_lines), data_record


async def get_daily_market_context(
    ticker: str = "SPY",
    include_full_prior_close: bool = False,
    return_data_record: bool = False,
) -> str | tuple[str, dict[str, Any]]:
    """Fetch recent market data context using canonical MarketDataManager (FMP) and pre-made tools."""
    full_text, data_record = await get_structured_daily_market_context(
        ticker=ticker, include_full_prior_close=include_full_prior_close
    )
    if return_data_record:
        return full_text, data_record
    return full_text


async def _can_run_daily_prediction(now_et: datetime, today, ticker: str) -> bool:
    from execution.market_data import MarketDataManager

    if now_et.hour > 9 or (now_et.hour == 9 and now_et.minute >= 30):
        logger.warning(
            f"Refusing to run daily prediction for {today}: current time ({now_et.strftime('%H:%M')} ET) "
            f"is after market open (09:30 ET). Daily predictions must run pre-market. Use --force to override."
        )
        return False
    if now_et.hour < 4:
        logger.warning(
            f"Refusing to run daily prediction for {today}: current time ({now_et.strftime('%H:%M')} ET) "
            f"is before pre-market open (04:00 ET). Use --force to override."
        )
        return False

    mdm = MarketDataManager()
    if not await mdm.is_trading_day(today):
        logger.info(
            f"Skipping daily prediction for {ticker} on {today}: "
            f"Market is closed (weekend or holiday). Use --force to override."
        )
        return False

    client = get_supabase_client()
    existing = (
        client.table("daily_predictions")
        .select("id")
        .eq("target_date", today.isoformat())
        .eq("ticker", ticker.upper())
        .execute()
    )
    if existing and getattr(existing, "data", None) and isinstance(existing.data, list) and len(existing.data) > 0:
        logger.warning(
            f"Daily predictions for {ticker} on {today} already exist in database ({len(existing.data)} records). "
            f"Refusing to overwrite existing morning predictions. Use --force to override."
        )
        return False
    return True


async def _call_instructor_daily_model(
    model_name: str, provider: str, prompt_content: str, user_msg: str
) -> tuple[str, float, float, str, list[str]]:
    deepseek_client = get_deepseek_client()
    try:
        create_kwargs: dict[str, Any] = {
            "model": model_name,
            "response_model": DailyPredictionOutput,
            "messages": [
                {"role": "system", "content": prompt_content},
                {"role": "user", "content": user_msg},
            ],
        }
        if provider == "deepseek" or "deepseek" in model_name.lower():
            create_kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
        elif provider == "anthropic":
            from core.llm.handlers.anthropic import get_anthropic_thinking_kwargs

            create_kwargs["cache_control"] = {"type": "ephemeral"}
            create_kwargs["system"] = [{"type": "text", "text": prompt_content, "cache_control": {"type": "ephemeral"}}]
            create_kwargs["messages"] = [{"role": "user", "content": user_msg}]
            create_kwargs.update(get_anthropic_thinking_kwargs(model_name, budget_tokens=2048, effort="medium"))
            create_kwargs["max_tokens"] = 4000
        elif provider == "gemini":
            from google.genai import types

            if hasattr(types, "ThinkingConfig"):
                create_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level="high")
        elif provider == "openai":
            create_kwargs["reasoning_effort"] = "low"

        resp_awaitable = deepseek_client.chat.completions.create(**create_kwargs)
        resp = (
            await resp_awaitable
            if (hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable))
            else resp_awaitable
        )
        return (
            resp.predicted_direction.upper(),
            float(resp.confidence),
            float(resp.expected_return_pct),
            resp.rationale,
            resp.catalysts,
        )
    finally:
        await close_client(deepseek_client, provider)


async def _execute_model_daily_prediction(
    model_cfg: dict[str, str],
    ticker: str,
    context: str,
    data_record: dict[str, Any],
    user_msg: str,
    raw_prompt_content: str,
    prompt_content: str,
) -> tuple[str, float, float, str, list[str], str]:
    model_name = model_cfg["name"]
    m_type = model_cfg["type"]
    provider = model_cfg["provider"]

    if m_type == "instructor":
        pred_dir, confidence, exp_ret, rationale, catalysts = await _call_instructor_daily_model(
            model_name, provider, prompt_content, user_msg
        )
        return pred_dir, confidence, exp_ret, rationale, catalysts, context

    if m_type == "minimax":
        minimax_client = MiniMaxClient()
        try:
            minimax_user_msg = (
                f"{user_msg}\n\n"
                "Note: Output ONLY the required JSON object conforming to the output schema. "
                "Do not include Markdown headers or YAML. "
                'Example: {"predicted_direction": "UP", "confidence": 65.0, "expected_return_pct": 0.35, "rationale": "...", "catalysts": ["..."]}'
            )
            messages = [
                {"role": "system", "content": prompt_content},
                {"role": "user", "content": minimax_user_msg},
            ]
            parsed_json = await minimax_client.chat_with_json_response(
                messages, model=model_name, max_completion_tokens=8192
            )
            return (
                str(parsed_json.get("predicted_direction", "UP")).upper(),
                float(parsed_json.get("confidence", 50.0)),
                float(parsed_json.get("expected_return_pct", 0.0)),
                str(parsed_json.get("rationale", "")),
                parsed_json.get("catalysts", []),
                context,
            )
        finally:
            await minimax_client.close()

    if m_type == "jev":
        crit = parse_jev_prompt_content(raw_prompt_content)
        jev_res = await predict_daily_with_jev(context=context, criteria=crit, ticker=ticker, model_name=model_name)
        return (
            jev_res["predicted_direction"],
            float(jev_res["confidence"]),
            float(jev_res["expected_return_pct"]),
            jev_res["rationale"],
            jev_res["catalysts"],
            context,
        )

    if m_type == "jev_curated":
        crit, _min_conf, manifest_dict = parse_jev_curated_prompt_content(raw_prompt_content)
        manifest = DataManifest(**manifest_dict) if manifest_dict else DataManifest()
        curated_context = pack_daily_context(data_record, manifest)
        jev_res = await predict_daily_with_jev(
            context=curated_context, criteria=crit, ticker=ticker, model_name=JEV_MODEL
        )
        return (
            str(jev_res["predicted_direction"]).upper(),
            float(jev_res["confidence"]),
            float(jev_res["expected_return_pct"]),
            jev_res["rationale"],
            jev_res["catalysts"],
            curated_context,
        )

    ingestion_prompt, crit, min_conf = parse_laya_curated_prompt_content(raw_prompt_content)
    daily_doc = await generate_daily_document(
        day_record=data_record, ingestion_prompt=ingestion_prompt, allow_fallback=True
    )
    criteria_obj = JevCriteriaConfig(criteria_up=crit["UP"], criteria_down=crit["DOWN"], min_confidence=min_conf)
    laya_res = await evaluate_with_laya(context=daily_doc, criteria=criteria_obj, ticker=ticker, fallback_to_jev=True)
    raw_dir = str(laya_res["predicted_direction"]).upper()
    confidence = float(laya_res["confidence"])
    backend_note = laya_res.get("model_backend", "laya-local")
    rationale = (
        f"Laya Decision ({backend_note}): {raw_dir} (Confidence: {confidence:.1f}%, "
        f"distribution={laya_res.get('probabilities', {})})"
    )
    return raw_dir, confidence, 0.0, rationale, [], daily_doc


async def run_daily_prediction(ticker: str = "SPY", force: bool = False) -> list[dict]:
    """Run daily predictions ahead of market open for target ticker across model arena (DeepSeek & MiniMax)."""
    now_et = get_ny_now()
    today = now_et.date()

    if not force and not await _can_run_daily_prediction(now_et, today, ticker):
        return []

    client = get_supabase_client()
    ctx_res = await get_daily_market_context(ticker=ticker, return_data_record=True)
    if isinstance(ctx_res, tuple) and len(ctx_res) == 2:
        context, data_record = ctx_res
    else:
        context = str(ctx_res)
        data_record = {"ticker": ticker.upper(), "target_date": today.isoformat()}

    user_msg = (
        f"Market Context:\n{context}\n\n"
        f"Analyze the market context and predict whether {ticker} will close HIGHER (UP) or LOWER (DOWN) "
        f"at 4:00 PM ET today compared to the 9:30 AM ET Open price."
    )

    models = [
        {"name": DEEPSEEK_FLASH_MODEL, "type": "instructor", "provider": "deepseek"},
        {"name": MINIMAX_MODEL, "type": "minimax", "provider": "minimax"},
        {"name": JEV_MODEL, "type": "jev", "provider": "openrouter"},
        {"name": "jev-four-regime-champion", "type": "jev_curated", "provider": "openrouter"},
        {"name": "laya-local-autoresearched", "type": "laya_curated", "provider": "local"},
    ]

    results = []

    for model_cfg in models:
        model_name = model_cfg["name"]
        m_type = model_cfg["type"]
        prompt_tag, raw_prompt_content = await fetch_active_daily_prompt(model_name=model_name)
        if m_type not in ("jev", "jev_curated", "laya_curated"):
            header, mutable, footer = split_daily_predictor_prompt(raw_prompt_content)
            prompt_content = header + mutable + footer
        else:
            prompt_content = raw_prompt_content

        success = False
        for attempt in range(3):
            try:
                (
                    pred_dir,
                    confidence,
                    expected_return_pct,
                    rationale,
                    catalysts,
                    model_context,
                ) = await _execute_model_daily_prediction(
                    model_cfg, ticker, context, data_record, user_msg, raw_prompt_content, prompt_content
                )
                model_min_conf = HOLD_CONFIDENCE_THRESHOLD
                if raw_prompt_content:
                    with contextlib.suppress(Exception):
                        parsed_raw = json.loads(raw_prompt_content)
                        if isinstance(parsed_raw, dict) and "min_confidence" in parsed_raw:
                            model_min_conf = float(parsed_raw["min_confidence"])

                pred_dir, expected_return_pct, rationale = apply_confidence_hold_gate(
                    direction=pred_dir,
                    confidence=confidence,
                    expected_return_pct=expected_return_pct,
                    rationale=rationale,
                    min_confidence=model_min_conf,
                )
                prediction_row = {
                    "prediction_date": today.isoformat(),
                    "target_date": today.isoformat(),
                    "ticker": ticker.upper(),
                    "model_name": model_name,
                    "prompt_variant_tag": prompt_tag,
                    "predicted_direction": pred_dir,
                    "confidence": confidence,
                    "expected_return_pct": expected_return_pct,
                    "rationale": rationale,
                    "catalysts": catalysts,
                    "status": "pending",
                    "market_context": model_context,
                }

                client.table("daily_predictions").upsert(
                    prediction_row,
                    on_conflict="target_date,ticker,model_name",
                ).execute()

                logger.info(
                    f"Successfully logged daily prediction for {ticker} ({model_name}) on {today}: "
                    f"{pred_dir} with {confidence}% confidence."
                )
                results.append(prediction_row)
                success = True
                break
            except Exception as e:
                logger.exception(f"Prediction attempt {attempt + 1} failed for {model_name} on {ticker}: {e}")
                if attempt < 2 and not os.environ.get("PYTEST_CURRENT_TEST"):
                    await asyncio.sleep(2)
        if not success:
            logger.error(f"Daily prediction failed for {model_name} on {ticker} after 3 attempts.")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run daily S&P predictions across model arena.")
    parser.add_argument("--ticker", type=str, default="SPY", help="Ticker to predict (default: SPY)")
    parser.add_argument("--force", action="store_true", help="Force prediction even on weekends or market holidays.")
    args = parser.parse_args()

    asyncio.run(run_daily_prediction(ticker=args.ticker, force=args.force))
