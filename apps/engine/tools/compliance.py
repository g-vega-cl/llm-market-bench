"""Compliance, trade verification, investment theses, catalyst radar, and congressional trading tools."""

import inspect
import json
from typing import Any

from core.config import logger
from tools._compat import get_async_supabase_client


async def execute_get_verifier_rejections_tool(
    ticker: str | None = None, limit: int = 5, model_name: str | None = None
) -> str:
    """Retrieve recent trade rejection logs and verifier feedback reasons from the database."""
    try:
        sb_client = await get_async_supabase_client()
        query = (
            sb_client.table("decisions")
            .select("id, ticker, signal, status, reasoning, model_name, metadata, created_at")
            .order("created_at", desc=True)
            .limit(limit * 2)
        )
        if ticker:
            query = query.eq("ticker", ticker.upper())

        res = query.execute()
        if inspect.isawaitable(res):
            res = await res
        rows = res.data or []

        rejected_rows = [r for r in rows if str(r.get("status", "")).startswith("REJECTED_")][:limit]
        if not rejected_rows:
            return "No trade rejections found matching the criteria."

        lines = [f"=== Recent Trade Rejections & Verifier Feedback (Count: {len(rejected_rows)}) ==="]
        for r in rejected_rows:
            meta = r.get("metadata")
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            elif not isinstance(meta, dict):
                meta = {}

            reason = meta.get("reason") or meta.get("info") or "No explicit verifier reason recorded"
            agent_thesis = r.get("reasoning", "") or ""
            if len(agent_thesis) > 150:
                agent_thesis = agent_thesis[:150] + "..."

            lines.append(
                f"- [{r.get('status')}] {r.get('signal')} {r.get('ticker')} (Model: {r.get('model_name') or 'N/A'})\n"
                f"  • Verifier Reason: {reason}\n"
                f"  • Agent Thesis: {agent_thesis}"
            )

        return "\n".join(lines)
    except Exception as e:
        logger.exception(f"Error in execute_get_verifier_rejections_tool: {e}")
        return f"Error retrieving verifier rejections: {str(e)}"


async def execute_inspect_verifier_rules_tool(
    limit: int = 5,
    ticker: str | None = None,
    track_id: str = "track_claude",
) -> str:
    """Retrieve verifier system SOP prompt, recent rejected trades, and strategic autoresearch nudge.

    Strictly scoped to track_claude where skeptical second-step verification is active.
    """
    if track_id != "track_claude":
        return (
            f"Error: 'inspect_verifier_rules_and_rejections' is strictly scoped to 'track_claude'. "
            f"Current track is '{track_id}'. Portfolios in other tracks bypass the verification stage entirely."
        )

    from core.config import AUTORESEARCH_TRACKS, VERIFIER_ENABLED_OWNER_IDS
    from core.llm.prompts import VERIFIER_SYSTEM_PROMPT

    claude_track_models = list(AUTORESEARCH_TRACKS.get("track_claude", VERIFIER_ENABLED_OWNER_IDS))

    lines = [
        "=== SKEPTICAL VERIFIER SYSTEM SOP (Active for track_claude) ===",
        VERIFIER_SYSTEM_PROMPT,
        "",
        f"=== RECENT VERIFIER-REJECTED TRADES (track_claude: {', '.join(claude_track_models)}) ===",
    ]

    try:
        sb_client = await get_async_supabase_client()
        query = (
            sb_client.table("decisions")
            .select("id, ticker, signal, status, reasoning, model_name, metadata, created_at")
            .eq("status", "REJECTED_VERIFICATION")
            .in_("model_name", claude_track_models)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if ticker:
            query = query.eq("ticker", ticker.upper())

        res = query.execute()
        if inspect.isawaitable(res):
            res = await res
        rows = res.data or []

        if not rows:
            lines.append("No recent verifier rejections recorded. The verifier remains active for track_claude.")
        else:
            for r in rows:
                meta = r.get("metadata")
                if isinstance(meta, str):
                    try:
                        meta = json.loads(meta)
                    except Exception:
                        meta = {}
                elif not isinstance(meta, dict):
                    meta = {}

                reason = meta.get("reason") or meta.get("info") or "No explicit verifier reason recorded"
                agent_thesis = r.get("reasoning", "") or ""
                if len(agent_thesis) > 160:
                    agent_thesis = agent_thesis[:160] + "..."

                lines.append(
                    f"- [{r.get('status')}] {r.get('signal')} {r.get('ticker')} (Model: {r.get('model_name') or 'N/A'})\n"
                    f"  • Verifier Objection: {reason}\n"
                    f"  • Proposed Agent Thesis: {agent_thesis}"
                )
    except Exception as e:
        logger.exception(f"Error retrieving verifier rejections for inspect_verifier_rules_tool: {e}")
        lines.append(f"Notice: Could not load recent rejections from database: {e}")

    lines.extend(
        [
            "",
            "=== STRATEGIC NUDGE FOR AUTORESEARCHER (track_claude) ===",
            "The trading agent in track_claude operates under this skeptical second-step Verifier.",
            "Trades are routinely blocked if they violate the 5 SOP checks above (e.g. chasing recent price spikes >5%, "
            "ignoring DCF intrinsic valuation multiples, or lacking alternative sector plays).",
            "Evolve the trading prompt to instruct the agent to anticipate these hurdles (e.g., check intrinsic valuation "
            "multiples, avoid chasing extended moves, and explore uncrowded alternatives) so high-conviction trades pass verification.",
        ]
    )

    return "\n".join(lines)


async def execute_track_thesis_pillars_tool(
    ticker: str,
    action: str = "get",
    thesis_statement: str | None = None,
    pillars: list[str] | None = None,
    risks: list[str] | None = None,
    disconfirming_factor: str | None = None,
    pillar_impacted: str | None = None,
    price_target: float | None = None,
    stop_loss: float | None = None,
    conviction: str | None = None,
) -> str:
    """Executes the track_thesis_pillars tool to manage multi-day falsifiable investment theses."""
    from tools.thesis_tools import execute_track_thesis_pillars

    try:
        res = await execute_track_thesis_pillars(
            ticker=ticker,
            action=action,
            thesis_statement=thesis_statement,
            pillars=pillars,
            risks=risks,
            disconfirming_factor=disconfirming_factor,
            pillar_impacted=pillar_impacted,
            price_target=price_target,
            stop_loss=stop_loss,
            conviction=conviction,
        )
        return res.get("markdown") or str(res)
    except Exception as e:
        logger.exception("Error executing track_thesis_pillars tool for %s: %s", ticker, e)
        return f"Error executing thesis tracker for '{ticker}': {str(e)}"


async def execute_get_catalyst_radar_tool(
    days_ahead: int = 7,
    include_digesting: bool = True,
    min_velocity: float = 1.2,
    detail: bool = False,
) -> str:
    """Executes catalyst radar retrieval for LLMs."""
    try:
        from analysis.catalyst_radar import fetch_catalyst_radar, format_catalyst_radar_context

        radar_items = fetch_catalyst_radar(
            days_ahead=days_ahead,
            include_digesting=include_digesting,
            min_velocity=min_velocity,
        )
        return format_catalyst_radar_context(radar_items, detail=detail)
    except Exception as e:
        logger.exception("Error executing get_catalyst_radar tool: %s", e)
        return f"Error retrieving catalyst radar: {str(e)}"


async def execute_get_calendar_scenario_analysis_tool(
    timeframe: str = "next_week",
    ticker: str | None = None,
    min_importance: int = 5,
    detail: bool = True,
    include_historical_memories: bool = True,
    ref_date: Any | None = None,
) -> str:
    """Executes upcoming calendar and scenario analysis retrieval for LLMs."""
    try:
        from analysis.calendar_scenarios import (
            execute_get_calendar_scenario_analysis_tool as _exec_cal,
        )

        return await _exec_cal(
            timeframe=timeframe,
            ticker=ticker,
            min_importance=min_importance,
            detail=detail,
            include_historical_memories=include_historical_memories,
            ref_date=ref_date,
        )
    except Exception as e:
        logger.exception("Error executing get_calendar_scenario_analysis tool: %s", e)
        return f"Error retrieving calendar scenario analysis: {str(e)}"


async def execute_get_congress_trades_tool(
    ticker: str | None = None,
    symbol: str | None = None,
    chamber: str | None = None,
    days: int = 45,
    transaction_type: str | None = None,
    limit: int = 20,
) -> str:
    """Executes the get_congress_trades tool to retrieve STOCK Act disclosures."""
    try:
        from tools.congress_tools import handle_get_congress_trades

        sym = ticker or symbol
        return await handle_get_congress_trades(
            symbol=sym,
            chamber=chamber,
            days=days,
            transaction_type=transaction_type,
            limit=limit,
        )
    except Exception as e:
        logger.exception("Error executing get_congress_trades tool: %s", e)
        return f"Error retrieving Congress trading disclosures: {e}"


async def execute_get_insider_trades_tool(
    ticker: str | None = None,
    symbol: str | None = None,
    days: int = 90,
    transaction_type: str = "all",
    limit: int = 15,
) -> str:
    """Executes the get_insider_trades tool to retrieve Form 4 insider disclosures."""
    try:
        from tools.insider_tools import handle_get_insider_trades

        sym = ticker or symbol or ""
        return await handle_get_insider_trades(
            symbol=sym,
            days=days,
            transaction_type=transaction_type,
            limit=limit,
        )
    except Exception as e:
        logger.exception("Error executing get_insider_trades tool: %s", e)
        return f"Error retrieving insider trading disclosures: {e}"


async def execute_get_whale_holdings_tool(
    ticker: str | None = None,
    symbol: str | None = None,
    fund_name: str | None = None,
    limit: int = 15,
) -> str:
    """Executes the get_whale_holdings tool to retrieve 13D/13G and 13F whale data."""
    try:
        from tools.whale_tools import handle_get_whale_holdings

        sym = ticker or symbol
        return await handle_get_whale_holdings(
            ticker=sym,
            fund_name=fund_name,
            limit=limit,
        )
    except Exception as e:
        logger.exception("Error executing get_whale_holdings tool: %s", e)
        return f"Error retrieving whale holdings: {e}"
