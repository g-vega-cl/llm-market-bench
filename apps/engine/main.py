"""Entry point for the AI Wall Street Engine.

This module provides the CLI interface for running the daily pipeline,
including newsletter ingestion, database snapshotting, and LLM analysis.
"""

import argparse
import asyncio

from analyze import analyze_chunks
from consensus import process_consensus
from analysis.momentum import analyze_momentum, decay_stale_concepts
from analysis.contrarian import run_contrarian_analysis
from core.llm.verification import verify_trading_decision
from attribution.service import save_decision
from core.config import COMMAND_INGEST, COMMAND_POST_ANALYSIS, COMMAND_GOVERNMENT, COMMAND_CALENDAR, COMMAND_CAUSE_AND_EFFECT, logger
from core.db import get_supabase_client, upsert_newsletter_snapshot
from execution.validation import validate_decision, validate_semantic_overlap, ValidationStatus
from execution.portfolio import Portfolio
from ingest.newsletter import ingest_newsletters
from ingest.government import run_government_pipeline
from ingest.calendar import run_calendar_pipeline
from memory.store import add_memory
from analysis.post_analysis import perform_post_analysis
from analysis.pca_utils import update_pca_coordinates
from analysis.cause_and_effect_analysis import perform_cause_and_effect_analysis


async def _stage_ingest_and_snapshot():
    """Stage 1: Ingest newsletters and save snapshots."""
    logger.info("Starting Newsletter Ingestion...")
    data = await ingest_newsletters()

    if not data:
        logger.warning("No new newsletters found to ingest. Skipping snapshotting and analysis.")
        return None, None

    logger.info(f"Successfully ingested {len(data)} newsletters.")
    logger.info("Starting Database Snapshotting...")
    
    sb_client = get_supabase_client()
    saved_count = 0
    for item in data:
        try:
            upsert_newsletter_snapshot(sb_client, item)
            saved_count += 1
        except Exception as e:
            logger.error(f"Error saving snapshot for {item.get('source_id', 'unknown')}: {e}")

    logger.info(f"Successfully saved {saved_count} snapshots to Supabase.")
    return data, sb_client


async def _stage_analysis_and_consensus(data, sb_client):
    """Stage 2: Run parallel LLM analysis and event consensus."""
    logger.info("Starting Parallel LLM Analysis...")
    try:
        # Note: analyze_chunks now handles fetching government and lesson context
        decisions, macro_events, aggregated_context, uncrowded_context = await analyze_chunks(data)
        logger.info(f"Analysis complete. Generated {len(decisions)} decisions and {len(macro_events)} raw macro events.")

        if not decisions and not macro_events:
            logger.warning("No decisions or events generated from analysis. Check LLM provider connectivity.")
        
        # --- Event Consensus Protocol ---
        logger.info("Running Event Consensus Protocol...")
        consensus_events = await process_consensus(macro_events)
        logger.info(f"Consensus protocol finished. Promoted {len(consensus_events)} events to memory.")

        # --- Trend & Concept Momentum Analysis ---
        logger.info("Starting Trend & Concept Momentum Analysis...")
        await analyze_momentum(sb_client, consensus_events)

        # --- Decay ---
        await decay_stale_concepts(sb_client)
        from memory.store import decay_memories
        decay_memories(sb_client)

        return decisions, macro_events, aggregated_context, uncrowded_context
    except Exception as e:
        logger.error(f"Analysis or Consensus failed: {e}")
        return [], [], "", ""


async def _stage_decision_processing(
    decisions, macro_events, data, aggregated_context, uncrowded_context, sb_client
):
    """Stage 3: Decision attribution, validation, and execution."""
    # --- Contrarian Analysis (Phase 2.5) ---
    logger.info("Starting Contrarian Agent Analysis...")
    contrarian_decisions, contrarian_events = await run_contrarian_analysis(
        data, decisions, context=aggregated_context
    )
    decisions.extend(contrarian_decisions)
    macro_events.extend(contrarian_events)

    saved_decisions = 0
    rejected_decisions = 0
    actionable_decisions = []
    
    for d in decisions:
        try:
            # --- Pre-Market Validation ---
            d.ticker = d.ticker.upper()
            validation = await validate_decision(d.ticker, getattr(d, "price", None))
            
            if validation.status != ValidationStatus.PASSED:
                logger.warning(f"[{d.ticker}] REJECTED (Market Guardrails): {validation.reason}")
                save_decision(sb_client, d, status=validation.status.value, metadata={"reason": validation.reason})
                rejected_decisions += 1
                continue

            # --- Semantic Overlap ---
            overlap_reason = await validate_semantic_overlap(d.ticker, d.reasoning)
            if overlap_reason:
                logger.warning(f"[{d.ticker}] REJECTED (Redundancy): {overlap_reason}")
                save_decision(sb_client, d, status=ValidationStatus.REJECTED_REDUNDANCY.value, metadata={"reason": overlap_reason})
                rejected_decisions += 1
                continue

            # --- Execution Logic ---
            status = "VALIDATED"
            meta = {"info": "Validation Passed (No Trade)"}
            trade_id = None
            
            if d.signal.upper() in ["BUY", "SELL"]:
                portfolio = Portfolio(owner_id=d.model_name)
                await portfolio.initialize()
                
                # --- SELL Guardrails ---
                if d.signal.upper() == "SELL":
                    if d.ticker not in portfolio.positions:
                        logger.warning(f"[{d.ticker}] REJECTED (Ownership): SELL signal for unheld ticker.")
                        save_decision(sb_client, d, status="REJECTED_OWNERSHIP", metadata={"reason": "Ticker not held."})
                        rejected_decisions += 1
                        continue
                    if not getattr(d, "sell_tool_called", False):
                        logger.warning(f"[{d.ticker}] REJECTED (Tool Usage): SELL without sell tool.")
                        save_decision(sb_client, d, status="REJECTED_TOOL_USAGE", metadata={"reason": "Sell tool must be called."})
                        rejected_decisions += 1
                        continue

                exec_price = validation.market_price or d.price
                if not exec_price or exec_price <= 0:
                    logger.error(f"[{d.ticker}] No valid price.")
                    rejected_decisions += 1
                    continue

                # Fetch market data for verification
                all_pos_tickers = list(portfolio.positions.keys())
                if d.ticker not in all_pos_tickers:
                    all_pos_tickers.append(d.ticker)
                
                from execution.market_data import MarketDataManager
                mdm = MarketDataManager()
                p_map = {t: (await mdm.get_quote(t)).price for t in all_pos_tickers if await mdm.get_quote(t)}

                verification = None
                qty = 0

                if d.signal.upper() == "BUY":
                    if not portfolio.metrics:
                        portfolio.calculate_reg_t_metrics(p_map)
                    
                    # --- Skeptical Verification ---
                    logger.info(f"[{d.ticker}] Verifying...")
                    # Search for contrarian thoughts on this ticker
                    contrarian_text = "\n".join([f"- {c.model_name}: {c.reasoning}" for c in contrarian_decisions if c.ticker == d.ticker])

                    verification = await verify_trading_decision(
                        decision=d,
                        portfolio_context=await portfolio.get_portfolio_summary(p_map),
                        aggregated_context=aggregated_context,
                        contrarian_context=contrarian_text,
                        uncrowded_context=uncrowded_context
                    )
                    
                    if verification.status == "REJECTED_VERIFICATION":
                        logger.warning(f"[{d.ticker}] REJECTED (Verification): {verification.verification_reasoning}")
                        save_decision(sb_client, d, status="REJECTED_VERIFICATION", metadata={"reason": verification.verification_reasoning})
                        rejected_decisions += 1
                        continue
                    
                    meta.update({
                        "verification_reasoning": verification.verification_reasoning,
                        "verification_confidence": verification.confidence_score,
                        "suggested_alternative": verification.alternative_ticker
                    })

                    bp = portfolio.metrics.buying_power if portfolio.metrics else 0
                    total_equity = portfolio.metrics.total_equity if portfolio.metrics else 0
                    from core.config import MIN_TRADE_VALUE
                    
                    alloc_pct = d.allocation_percentage or 5
                    min_buy_threshold = max(MIN_TRADE_VALUE, 0.10 * max(bp, total_equity))
                    usd_to_spend = (alloc_pct / 100.0) * bp
                    
                    if usd_to_spend < min_buy_threshold and bp >= min_buy_threshold:
                        usd_to_spend = min_buy_threshold
                        
                    qty = int(usd_to_spend / exec_price)
                    if qty * exec_price < min_buy_threshold and (qty + 1) * exec_price <= bp:
                        qty += 1

                    validation_res = portfolio.validate_trade(d.ticker, qty, exec_price, d.signal)
                    if not validation_res.passed:
                        logger.warning(f"[{d.ticker}] REJECTED (Margin): {validation_res.reason}")
                        save_decision(sb_client, d, status="REJECTED_MARGIN", metadata={"reason": validation_res.reason})
                        rejected_decisions += 1
                        continue

                elif d.signal.upper() == "SELL":
                    qty = getattr(d, "quantity", None) or int((d.allocation_percentage or 0 / 100.0) * portfolio.positions.get(d.ticker).quantity)
                    if not portfolio.metrics:
                        portfolio.calculate_reg_t_metrics(p_map)
                    
                    validation_res = portfolio.validate_trade(d.ticker, qty, exec_price, d.signal, is_sell_tool_used=getattr(d, "sell_tool_called", False))
                    if not validation_res.passed:
                        logger.warning(f"[{d.ticker}] REJECTED (Margin): {validation_res.reason}")
                        save_decision(sb_client, d, status="REJECTED_MARGIN", metadata={"reason": validation_res.reason})
                        rejected_decisions += 1
                        continue
                
                if qty <= 0:
                    qty = getattr(d, "quantity", 0) or 1
                if qty <= 0:
                    rejected_decisions += 1
                    continue

                if verification and verification.status == "ADJUSTED_ALLOCATION" and verification.adjusted_quantity:
                    qty = verification.adjusted_quantity
                        
                trade_id = await portfolio.execute_trade(d.ticker, qty, exec_price, d.signal)
                if trade_id:
                    status = "EXECUTED"
                    meta = {"trade_id": str(trade_id), "info": f"Executed {d.signal} {qty} @ ${exec_price:.2f}"}
                else:
                    status = "ERROR_EXECUTION"
                    meta = {"info": "Execution Failed"}

            save_decision(sb_client, d, status=status, metadata=meta, trade_id=str(trade_id) if trade_id else None)
            if status in ["EXECUTED", "VALIDATED"]:
                actionable_decisions.append(d)
            saved_decisions += 1
            logger.info(f"[{d.ticker}] {d.signal}: Saved attribution.")
        except Exception as e:
            logger.error(f"Failed to process decision for {d.ticker}: {e}")

    logger.info(f"Processing complete: {saved_decisions} saved, {rejected_decisions} rejected.")


async def _stage_snapshots_and_pca(sb_client):
    """Stage 4: Performance snapshots and PCA updates."""
    logger.info("Starting Daily Performance Snapshot...")
    port_res = sb_client.table("portfolios").select("owner_id").execute()
    owners = [p["owner_id"] for p in port_res.data] if port_res.data else []
    
    if owners:
        from execution.market_data import MarketDataManager
        mdm = MarketDataManager()
        all_tickers = set()
        portfolios = []
        for owner in owners:
            p = Portfolio(owner_id=owner)
            await p.initialize()
            all_tickers.update(p.positions.keys())
            portfolios.append(p)
        
        price_map = {t: (await mdm.get_quote(t)).price for t in all_tickers if await mdm.get_quote(t)}
        for p in portfolios:
            await p.record_performance_snapshot(price_map)
            await p.save_metrics()

    logger.info("Updating PCA coordinates...")
    update_pca_coordinates(sb_client)


async def run_ingest(force: bool = False):
    """Runs the full ingestion and analysis pipeline."""
    from core.utils import is_market_open_with_logging
    if not await is_market_open_with_logging(force):
        return

    # 1. Ingest & Snapshot
    data, sb_client = await _stage_ingest_and_snapshot()
    if not data:
        return

    try:
        # 2. Analysis & Consensus
        decisions, macro_events, agg_ctx, uncrowded_ctx = await _stage_analysis_and_consensus(data, sb_client)
        
        # 3. Decision Processing & Execution
        await _stage_decision_processing(decisions, macro_events, data, agg_ctx, uncrowded_ctx, sb_client)

        # 4. Snapshots & Cleanup
        await _stage_snapshots_and_pca(sb_client)

    finally:
        from execution.providers.factory import get_active_provider_class
        await get_active_provider_class().disconnect_all()


async def run_post_analysis():
    """Runs the post-analysis for historical trades."""
    try:
        await perform_post_analysis(windows=[5, 14, 30])
    finally:
        # --- Provider Cleanup ---
        from execution.providers.factory import get_active_provider_class
        provider_cls = get_active_provider_class()
        await provider_cls.disconnect_all()


async def run_cause_and_effect():
    """Runs the cause-and-effect analysis for market events."""
    try:
        await perform_cause_and_effect_analysis()
    finally:
        # --- Provider Cleanup ---
        from execution.providers.factory import get_active_provider_class
        provider_cls = get_active_provider_class()
        await provider_cls.disconnect_all()


def main():
    """Main entry point for the AI Wall Street Engine CLI."""
    parser = argparse.ArgumentParser(description="AI Wall Street Engine")
    parser.add_argument(
        "command",
        choices=[COMMAND_INGEST, COMMAND_POST_ANALYSIS, COMMAND_GOVERNMENT, COMMAND_CALENDAR, COMMAND_CAUSE_AND_EFFECT],
        help="Action to perform"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force ingestion even outside market hours"
    )

    args = parser.parse_args()

    if args.command == COMMAND_INGEST:
        asyncio.run(run_ingest(force=args.force))
    elif args.command == COMMAND_POST_ANALYSIS:
        asyncio.run(run_post_analysis())
    elif args.command == COMMAND_GOVERNMENT:
        asyncio.run(run_government_pipeline())
    elif args.command == COMMAND_CALENDAR:
        asyncio.run(run_calendar_pipeline())
    elif args.command == COMMAND_CAUSE_AND_EFFECT:
        asyncio.run(run_cause_and_effect())


if __name__ == "__main__":
    main()
