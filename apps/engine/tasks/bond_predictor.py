"""Systematic Daily Bond Predictor Module (Vertical Slice Island).

Executes tool-first, pull-based daily predictions on TLT (20+ Year Treasury Bond ETF):
- Enforces GEMINI.md Principle 8: Lean temporal prompt + autonomous tool pulling.
- Models: GPT-5.6 Luna (OpenAI) & DeepSeek-v4-Flash (DeepSeek) via multi-turn tool loops.
- Jev: Single-turn Decisions API via automated lean tool bundle context.
- Idempotent persistence to Supabase daily_predictions table with ticker='TLT'.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from core.config import (
    DEEPSEEK_FLASH_MODEL,
    JEV_MODEL,
    OPENAI_MODEL,
    logger,
)
from core.db import get_supabase_client
from core.llm.clients import close_client, get_deepseek_client, get_openai_client
from core.llm.daily_predictor_prompts import DailyPredictionOutput
from core.llm.handlers import deepseek, openai
from core.llm.tools import (
    CANONICAL_TOOLS_REGISTRY,
    execute_get_today_economic_releases_tool,
    execute_get_treasury_yield_curve_tool,
)
from tasks.daily_predictor import predict_daily_with_jev

BOND_TOOLBOX: list[str] = [
    "get_treasury_yield_curve",
    "get_today_economic_releases",
    "get_yield_curve_regime",
    "get_macro_options_sentiment",
    "get_calendar_scenario_analysis",
]

BOND_PREDICTOR_MODELS: list[dict[str, str]] = [
    {"name": OPENAI_MODEL, "provider": "openai", "type": "tool_loop"},
    {"name": DEEPSEEK_FLASH_MODEL, "provider": "deepseek", "type": "tool_loop"},
    {"name": JEV_MODEL, "provider": "openrouter", "type": "jev"},
]

BOND_SYSTEM_PROMPT = """You are an elite fixed-income quantitative strategist predicting open-to-close price direction for the 20+ Year Treasury Bond ETF (TLT).

Fixed Income Mechanics:
- Bond prices move inversely to Treasury yields. Falling yields = TLT UP; Rising yields = TLT DOWN.
- High duration (~17 years) makes TLT sensitive to morning economic prints (CPI, PPI, Jobs, NFP), Fed expectations, and Treasury auction tails.
- Use your callable tools autonomously to inspect the Treasury yield curve, today's scheduled economic releases, options sentiment, and calendar triggers.
- Formulate an objective, unbiased conviction on whether TLT will close HIGHER (UP) or LOWER (DOWN) at 4:00 PM ET compared to 9:30 AM ET open.
"""


def get_ny_now() -> datetime:
    """Helper to return current New York datetime."""
    try:
        return datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        return datetime.now()


def construct_lean_bond_prompt(ticker: str = "TLT", quote: dict | None = None, date_str: str | None = None) -> str:
    """Constructs minimal, tool-first prompt containing only temporal and quote context."""
    today = date_str or datetime.now(UTC).date().isoformat()
    lines = [
        f"Target Asset: {ticker.upper()} (iShares 20+ Year Treasury Bond ETF)",
        f"Prediction Target Date: {today}",
        "Regular Market Session: 09:30 AM ET to 04:00 PM ET",
    ]
    if quote and quote.get("price") is not None:
        p = float(quote["price"])
        chg = float(quote.get("change") or 0.0)
        chg_pct = float(quote.get("change_pct") or 0.0)
        prev = float(quote.get("previous_close") or p)
        lines.append(
            f"Pre-Market / Overnight Quote: ${p:.2f} | Gap: {chg:+.2f} ({chg_pct:+.2f}%) vs Prev Close ${prev:.2f}"
        )

    lines.append(
        "\nTask:\n"
        "1. Autonomously pull necessary data using your available tools (Treasury yield curve, today's economic releases, macro options sentiment, calendar triggers).\n"
        f"2. Predict whether {ticker} will close HIGHER (UP) or LOWER (DOWN) at 4:00 PM ET today vs 9:30 AM ET Open.\n"
        "3. Provide predicted_direction (UP/DOWN), confidence (50-100%), expected_return_pct, rationale, and catalysts."
    )
    return "\n".join(lines)


async def compile_jev_bond_context(ticker: str = "TLT", quote: dict | None = None, date_str: str | None = None) -> str:
    """Compiles automated lean tool bundle into market context for single-turn Jev Decisions API."""
    today = date_str or datetime.now(UTC).date().isoformat()
    context_lines = [
        f"Asset: {ticker} (20+ Year Treasury Bond ETF)",
        f"Target Date: {today}",
    ]
    if quote and quote.get("price") is not None:
        context_lines.append(f"Pre-Market Quote: ${quote['price']:.2f} | Gap: {quote.get('change_pct', 0.0):+.2f}%")

    try:
        yc_str = await execute_get_treasury_yield_curve_tool()
        if yc_str and not yc_str.startswith("Error"):
            context_lines.append(yc_str)
    except Exception as e:
        logger.warning(f"Error compiling yield curve context for Jev: {e}")

    try:
        econ_str = await execute_get_today_economic_releases_tool(target_date=today)
        if econ_str and not econ_str.startswith("Error") and not econ_str.startswith("No scheduled"):
            context_lines.append(econ_str)
    except Exception as e:
        logger.warning(f"Error compiling economic releases context for Jev: {e}")

    return "\n\n".join(context_lines)


async def predict_bond_with_reasoning_model(
    model_name: str,
    provider: str,
    user_prompt: str,
    tool_names: list[str] = BOND_TOOLBOX,
) -> dict[str, Any]:
    """Executes multi-turn autonomous tool loop followed by structured prediction extraction."""
    override_tools = [CANONICAL_TOOLS_REGISTRY[t] for t in tool_names if t in CANONICAL_TOOLS_REGISTRY]
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": BOND_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    client = None
    try:
        if provider == "openai":
            client = get_openai_client()
            await openai.run_tool_loop(
                client,
                model_name=model_name,
                messages=messages,
                provider="openai",
                override_tools=override_tools,
            )
        elif provider == "deepseek":
            client = get_deepseek_client()
            await deepseek.run_tool_loop(
                client,
                model_name=model_name,
                messages=messages,
                provider="deepseek",
                override_tools=override_tools,
            )

        # Final structured extraction using instructor client
        instructor_client = get_deepseek_client() if provider == "deepseek" else get_openai_client()
        formatted_messages = deepseek.prepare_messages_for_instructor(messages) if provider == "deepseek" else messages

        create_kwargs = {
            "model": model_name,
            "response_model": DailyPredictionOutput,
            "messages": formatted_messages,
        }
        if provider == "deepseek":
            create_kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
        elif provider == "openai":
            create_kwargs["reasoning_effort"] = "low"

        resp_awaitable = instructor_client.chat.completions.create(**create_kwargs)
        resp = await resp_awaitable if asyncio.iscoroutine(resp_awaitable) else resp_awaitable

        return {
            "predicted_direction": resp.predicted_direction.upper(),
            "confidence": float(resp.confidence),
            "expected_return_pct": float(resp.expected_return_pct),
            "rationale": resp.rationale,
            "catalysts": resp.catalysts,
        }
    finally:
        if client:
            await close_client(client, provider)


async def run_daily_bond_prediction(ticker: str = "TLT", force: bool = False) -> list[dict[str, Any]]:
    """Runs daily bond predictions pre-market across model arena (GPT-5.6 Luna, DeepSeek, Jev)."""
    from execution.market_data import MarketDataManager

    now_et = get_ny_now()
    today = now_et.date()
    today_str = today.isoformat()

    if not force:
        if now_et.hour > 9 or (now_et.hour == 9 and now_et.minute >= 30):
            logger.warning(
                f"Refusing daily bond prediction for {today_str}: current time ({now_et.strftime('%H:%M')} ET) is after open."
            )
            return []
        if now_et.hour < 4:
            logger.warning(f"Refusing daily bond prediction for {today_str}: before pre-market open.")
            return []

        mdm = MarketDataManager()
        if not await mdm.is_trading_day(today):
            logger.info(f"Skipping daily bond prediction for {today_str}: Market closed.")
            return []

        client = get_supabase_client()
        existing = (
            client.table("daily_predictions")
            .select("id")
            .eq("target_date", today_str)
            .eq("ticker", ticker.upper())
            .execute()
        )
        if existing and existing.data:
            logger.warning(
                f"Daily predictions for {ticker} on {today_str} already exist ({len(existing.data)} records). Skipping."
            )
            return []

    mdm = MarketDataManager()
    pm_quote = await mdm.get_premarket_quote(ticker)
    lean_prompt = construct_lean_bond_prompt(ticker=ticker, quote=pm_quote, date_str=today_str)
    client = get_supabase_client()
    results = []

    for model_cfg in BOND_PREDICTOR_MODELS:
        model_name = model_cfg["name"]
        m_type = model_cfg["type"]
        provider = model_cfg["provider"]

        try:
            if m_type == "tool_loop":
                pred = await predict_bond_with_reasoning_model(
                    model_name=model_name,
                    provider=provider,
                    user_prompt=lean_prompt,
                    tool_names=BOND_TOOLBOX,
                )
            else:  # Jev single-turn
                jev_context = await compile_jev_bond_context(ticker=ticker, quote=pm_quote, date_str=today_str)
                pred = await predict_daily_with_jev(context=jev_context, ticker=ticker, model_name=model_name)

            db_payload = {
                "target_date": today_str,
                "ticker": ticker.upper(),
                "model_name": model_name,
                "prompt_variant_tag": f"pull-bond-{model_name}",
                "predicted_direction": pred["predicted_direction"],
                "confidence": pred["confidence"],
                "expected_return_pct": pred.get("expected_return_pct", 0.0),
                "rationale": pred.get("rationale", ""),
                "catalysts": pred.get("catalysts", []),
                "market_context": lean_prompt if m_type == "tool_loop" else jev_context,
                "status": "pending",
                "created_at": datetime.now(UTC).isoformat(),
            }
            insert_res = client.table("daily_predictions").insert(db_payload).execute()
            pred_id = insert_res.data[0]["id"] if insert_res and insert_res.data else "unknown"

            results.append({"status": "success", "id": pred_id, "model": model_name, "prediction": pred})
            logger.info(
                f"Successfully recorded bond prediction for {model_name} on {ticker}: {pred['predicted_direction']} ({pred['confidence']}%)"
            )

        except Exception as e:
            logger.exception(f"Error predicting bond direction for {model_name}: {e}")
            results.append({"status": "error", "model": model_name, "error": str(e)})

    return results
