"""Daily Stock Picker Task (3 Up, 3 Down).

Screens morning candidate stocks from intelligence briefings, runs multi-model
arena predictions (DeepSeek Flash, MiniMax-M3, GPT Luna), computes a deterministic
consensus basket via Reciprocal Rank Fusion, and persists to daily_stock_baskets/picks.
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from core.config import (
    DEEPSEEK_FLASH_MODEL,
    MINIMAX_MODEL,
    OPENAI_MODEL,
    logger,
)
from core.db import get_supabase_client
from core.llm.clients import close_client, get_deepseek_client, get_openai_client
from core.llm.minimax import MiniMaxClient
from core.llm.stock_picker_prompts import (
    STOCK_PICKER_PROMPT,
    StockPickerOutput,
    StockPickItem,
)

DEFAULT_CANDIDATES = [
    "NVDA", "TSM", "AAPL", "MSFT", "AMZN", "GOOGL",
    "META", "TSLA", "AVGO", "CRWV", "ETR", "CB",
    "XLF", "ABNB", "VRT", "DLR", "JPM", "WMT",
]

TARGET_MODELS = [
    {"name": DEEPSEEK_FLASH_MODEL, "provider": "deepseek"},
    {"name": MINIMAX_MODEL, "provider": "minimax"},
    {"name": OPENAI_MODEL, "provider": "openai"},
]


def get_ny_now() -> datetime:
    """Return current datetime in America/New_York timezone."""
    return datetime.now(ZoneInfo("America/New_York"))


def extract_candidate_tickers(newsletter_text: str | None) -> list[str]:
    """Extract candidate stock tickers mentioned in morning newsletter content."""
    if not newsletter_text:
        return DEFAULT_CANDIDATES

    # Find common uppercase ticker symbols (2-5 letters) in bold or parentheses
    found = set()
    patterns = [
        r"\*\*([A-Z]{2,5})\*\*",
        r"\(([A-Z]{2,5})\)",
        r"\b([A-Z]{2,5})\s*[\+\-]\d",
    ]
    for p in patterns:
        for m in re.finditer(p, newsletter_text):
            sym = m.group(1).upper()
            if sym not in {"CPI", "PCE", "GDP", "FOMC", "ET", "USD", "EUR", "VIX", "SPY", "QQQ", "DIA", "IWM", "TLT"}:
                found.add(sym)

    # Combine with default liquid anchors to guarantee adequate choice
    candidates = list(found.union(DEFAULT_CANDIDATES[:10]))
    return sorted(candidates)[:25]


async def fetch_active_prompt(model_name: str) -> tuple[str, str]:
    """Fetch active or baseline STOCK_PICKER_PROMPT for a given model track."""
    supabase = get_supabase_client()
    try:
        res = (
            supabase.table("prompt_experiments")
            .select("variant_tag, prompt_content")
            .eq("prompt_name", "STOCK_PICKER_PROMPT")
            .eq("track_id", model_name)
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]["variant_tag"], res.data[0]["prompt_content"]

        base_res = (
            supabase.table("prompt_experiments")
            .select("variant_tag, prompt_content")
            .eq("prompt_name", "STOCK_PICKER_PROMPT")
            .eq("track_id", model_name)
            .eq("status", "baseline")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if base_res.data:
            return base_res.data[0]["variant_tag"], base_res.data[0]["prompt_content"]
    except Exception as e:
        logger.warning(f"Failed to query prompt_experiments for {model_name}: {e}")

    return "baseline", STOCK_PICKER_PROMPT


def sanitize_picks(picks: list[StockPickItem], direction: str, candidate_pool: list[str]) -> list[StockPickItem]:
    """Ensure exactly 3 unique valid picks ranked 1-3 for a given direction."""
    seen_tickers = set()
    cleaned = []
    for p in picks:
        ticker = p.ticker.strip().upper()
        if ticker in candidate_pool and ticker not in seen_tickers and len(cleaned) < 3:
            seen_tickers.add(ticker)
            cleaned.append(
                StockPickItem(
                    ticker=ticker,
                    direction=direction,
                    rank=len(cleaned) + 1,
                    confidence=max(50.0, min(100.0, float(p.confidence))),
                    expected_return_pct=p.expected_return_pct,
                    reasoning=p.reasoning,
                )
            )

    # Backfill if fewer than 3 valid picks
    for candidate in candidate_pool:
        if len(cleaned) == 3:
            break
        if candidate not in seen_tickers:
            seen_tickers.add(candidate)
            cleaned.append(
                StockPickItem(
                    ticker=candidate,
                    direction=direction,
                    rank=len(cleaned) + 1,
                    confidence=60.0,
                    expected_return_pct=1.0 if direction == "UP" else -1.0,
                    reasoning=f"System backfill pick for {candidate} from active morning candidate pool.",
                )
            )
    return cleaned


async def execute_model_picker(
    model_info: dict[str, str],
    candidate_pool: list[str],
    briefing_context: str,
) -> StockPickerOutput:
    """Run inference for a single model to select 3 UP and 3 DOWN stocks."""
    model_name = model_info["name"]
    provider = model_info["provider"]
    _, prompt_content = await fetch_active_prompt(model_name)

    user_prompt = (
        f"Target Session Date: {get_ny_now().strftime('%Y-%m-%d')}\n"
        f"Candidate Universe: {', '.join(candidate_pool)}\n\n"
        f"Morning Market Briefing Context:\n{briefing_context[:3000]}\n\n"
        "Select exactly 3 unique stocks to go UP (ranks 1-3) and 3 unique stocks to go DOWN (ranks 1-3)."
    )

    if provider == "minimax":
        client = MiniMaxClient()
        response_text = await client.chat_completion(
            messages=[
                {"role": "system", "content": prompt_content},
                {"role": "user", "content": user_prompt + "\nReturn ONLY valid JSON."},
            ],
            temperature=0.2,
        )
        data = json.loads(re.sub(r"^```(?:json)?|```$", "", response_text.strip(), flags=re.MULTILINE))
        output = StockPickerOutput(**data)
    elif provider == "deepseek":
        ds_client = get_deepseek_client()
        try:
            output = await ds_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": prompt_content},
                    {"role": "user", "content": user_prompt},
                ],
                response_model=StockPickerOutput,
                temperature=0.2,
            )
        finally:
            await close_client(ds_client)
    else:  # openai
        oai_client = get_openai_client()
        try:
            output = await oai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": prompt_content},
                    {"role": "user", "content": user_prompt},
                ],
                response_model=StockPickerOutput,
                temperature=0.2,
            )
        finally:
            await close_client(oai_client)

    # Sanitize and ensure uniqueness across both legs
    picks_up = sanitize_picks(output.picks_up, "UP", candidate_pool)
    used_tickers = {p.ticker for p in picks_up}
    avail_down = [c for c in candidate_pool if c not in used_tickers]
    picks_down = sanitize_picks(output.picks_down, "DOWN", avail_down)

    return StockPickerOutput(
        picks_up=picks_up,
        picks_down=picks_down,
        market_regime_rationale=output.market_regime_rationale,
    )


def compute_consensus_basket(
    model_outputs: dict[str, StockPickerOutput],
    candidate_pool: list[str],
) -> StockPickerOutput:
    """Compute consensus 3 UP and 3 DOWN basket via Reciprocal Rank Fusion with leg exclusivity."""
    scores_up: dict[str, float] = {}
    scores_down: dict[str, float] = {}
    conf_up: dict[str, list[float]] = {}
    conf_down: dict[str, list[float]] = {}
    reasons_up: dict[str, str] = {}
    reasons_down: dict[str, str] = {}

    for _, output in model_outputs.items():
        for pick in output.picks_up:
            score = (1.0 / (60.0 + pick.rank)) * (pick.confidence / 100.0)
            scores_up[pick.ticker] = scores_up.get(pick.ticker, 0.0) + score
            conf_up.setdefault(pick.ticker, []).append(pick.confidence)
            reasons_up[pick.ticker] = pick.reasoning
        for pick in output.picks_down:
            score = (1.0 / (60.0 + pick.rank)) * (pick.confidence / 100.0)
            scores_down[pick.ticker] = scores_down.get(pick.ticker, 0.0) + score
            conf_down.setdefault(pick.ticker, []).append(pick.confidence)
            reasons_down[pick.ticker] = pick.reasoning

    # Leg Exclusivity: resolve conflicting tickers appearing in both UP and DOWN
    conflicts = set(scores_up.keys()).intersection(set(scores_down.keys()))
    for c in conflicts:
        if scores_up[c] >= scores_down[c]:
            del scores_down[c]
        else:
            del scores_up[c]

    def _rank_direction(
        score_map: dict[str, float], conf_map: dict[str, list[float]], reasons: dict[str, str], direction: str
    ) -> list[StockPickItem]:
        sorted_tickers = sorted(
            score_map.keys(),
            key=lambda t: (score_map[t], sum(conf_map[t]) / len(conf_map[t])),
            reverse=True,
        )
        res = []
        for rank, ticker in enumerate(sorted_tickers[:3], start=1):
            avg_conf = sum(conf_map[ticker]) / len(conf_map[ticker])
            res.append(
                StockPickItem(
                    ticker=ticker,
                    direction=direction,
                    rank=rank,
                    confidence=round(avg_conf, 1),
                    expected_return_pct=1.5 if direction == "UP" else -1.5,
                    reasoning=f"[Consensus] {reasons[ticker]}",
                )
            )
        return res

    final_up = sanitize_picks(_rank_direction(scores_up, conf_up, reasons_up, "UP"), "UP", candidate_pool)
    used_for_up = {p.ticker for p in final_up}
    avail_down_candidates = [c for c in candidate_pool if c not in used_for_up]
    final_down = sanitize_picks(
        _rank_direction(scores_down, conf_down, reasons_down, "DOWN"), "DOWN", avail_down_candidates
    )

    return StockPickerOutput(
        picks_up=final_up,
        picks_down=final_down,
        market_regime_rationale="Consensus synthesis generated via Reciprocal Rank Fusion across all arena models.",
    )


async def persist_stock_basket(
    target_date: str,
    model_name: str,
    output: StockPickerOutput,
) -> str:
    """Persist parent basket and 6 child picks into Supabase."""
    supabase = get_supabase_client()

    basket_row = {
        "target_date": target_date,
        "model_name": model_name,
        "status": "pending",
    }
    basket_res = (
        supabase.table("daily_stock_baskets").upsert(basket_row, on_conflict="target_date,model_name").execute()
    )
    basket_id = basket_res.data[0]["id"]

    picks_data = []
    all_picks = output.picks_up + output.picks_down
    for pick in all_picks:
        picks_data.append(
            {
                "basket_id": basket_id,
                "target_date": target_date,
                "model_name": model_name,
                "ticker": pick.ticker,
                "direction": pick.direction,
                "rank": pick.rank,
                "confidence": pick.confidence,
                "expected_return_pct": pick.expected_return_pct,
                "reasoning": pick.reasoning,
                "status": "pending",
            }
        )

    supabase.table("daily_stock_picks").upsert(
        picks_data,
        on_conflict="target_date,model_name,ticker",
    ).execute()

    return basket_id


async def run_daily_stock_picker(
    target_date: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Main orchestration entry point for the morning daily stock picker arena."""
    now_et = get_ny_now()
    session_date = target_date or now_et.strftime("%Y-%m-%d")
    logger.info(f"Starting Daily Stock Picker Arena for session: {session_date}")

    supabase = get_supabase_client()
    # Check if consensus basket already exists for today unless forced
    if not force:
        existing = (
            supabase.table("daily_stock_baskets")
            .select("id")
            .eq("target_date", session_date)
            .eq("model_name", "consensus")
            .execute()
        )
        if existing.data:
            logger.info(f"Consensus basket already exists for {session_date}. Skipping (use --force to overwrite).")
            return {"status": "skipped", "target_date": session_date}

    # Fetch latest morning briefing text
    briefing_res = (
        supabase.table("generated_newsletters").select("content").order("created_at", desc=True).limit(1).execute()
    )
    briefing_text = briefing_res.data[0]["content"] if briefing_res.data else ""
    candidate_pool = extract_candidate_tickers(briefing_text)
    logger.info(f"Candidate pool for {session_date}: {candidate_pool}")

    # Run models in parallel
    tasks = [execute_model_picker(m, candidate_pool, briefing_text) for m in TARGET_MODELS]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    model_outputs: dict[str, StockPickerOutput] = {}
    for m, res in zip(TARGET_MODELS, results, strict=False):
        if isinstance(res, Exception):
            logger.error(f"Error executing stock picker for model {m['name']}: {res}", exc_info=res)
        else:
            model_outputs[m["name"]] = res
            await persist_stock_basket(session_date, m["name"], res)

    if not model_outputs:
        raise RuntimeError("All models failed in Daily Stock Picker Arena.")

    # Compute and persist consensus basket
    consensus_output = compute_consensus_basket(model_outputs, candidate_pool)
    consensus_basket_id = await persist_stock_basket(session_date, "consensus", consensus_output)

    logger.info(
        f"Daily Stock Picker completed successfully for {session_date}. Consensus Basket ID: {consensus_basket_id}"
    )
    return {
        "status": "success",
        "target_date": session_date,
        "consensus_basket_id": consensus_basket_id,
        "models_run": list(model_outputs.keys()),
    }
