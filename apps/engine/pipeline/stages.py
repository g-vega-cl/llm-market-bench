"""Pipeline execution stages for ingestion, analysis, and portfolio snapshotting."""

import asyncio

from analysis.analyze import analyze_chunks
from analysis.pca_utils import update_pca_coordinates
from core.config import logger
from core.db import bulk_upsert_newsletter_snapshots, get_supabase_client, upsert_newsletter_snapshot
from execution.portfolio import Portfolio
from ingest.newsletter import ingest_newsletters
from pipeline.resolver import resolve_dep


async def _stage_ingest_and_snapshot(dry_run: bool = False):
    """Stage 1: Ingest newsletters and save snapshots."""
    log = resolve_dep("logger", logger)
    ingest_fn = resolve_dep("ingest_newsletters", ingest_newsletters)
    get_client_fn = resolve_dep("get_supabase_client", get_supabase_client)
    bulk_upsert_fn = resolve_dep("bulk_upsert_newsletter_snapshots", bulk_upsert_newsletter_snapshots)
    upsert_fn = resolve_dep("upsert_newsletter_snapshot", upsert_newsletter_snapshot)

    log.info("Starting Newsletter Ingestion...")
    data = await ingest_fn()

    sb_client = get_client_fn()
    if not data and dry_run and sb_client:
        log.info(
            "[DRY RUN] No new incoming newsletters; attempting to load recent snapshots from Supabase for dry run..."
        )
        try:
            res = sb_client.table("newsletter_snapshots").select("*").order("received_at", desc=True).limit(5).execute()
            if res.data:
                data = res.data
                log.info(f"[DRY RUN] Loaded {len(data)} recent newsletter snapshots for simulation.")
        except Exception as e:
            log.warning(f"[DRY RUN] Failed to load recent snapshots: {e}")

    if not data:
        log.warning("No new newsletters found to ingest. Skipping snapshotting and analysis.")
        return None, sb_client

    if dry_run:
        log.info(f"[DRY RUN] Skipping database snapshot upserts for {len(data)} items.")
        return data, sb_client

    log.info("Starting Database Snapshotting...")

    saved_count = 0

    try:
        bulk_upsert_fn(sb_client, data)
        saved_count = len(data)
    except Exception:
        log.warning("Bulk upsert failed, falling back to individual upserts.")
        for item in data:
            try:
                upsert_fn(sb_client, item)
                saved_count += 1
            except Exception:
                log.exception(f"Error saving snapshot for {item.get('source_id', 'unknown')}")

    log.info(f"Successfully saved {saved_count}/{len(data)} snapshots to Supabase.")
    return data, sb_client


async def _stage_dust_cleanup(sb_client, dry_run: bool = False):
    """Stage 1.5: Clean dust positions from all active portfolios BEFORE LLM analysis."""
    log = resolve_dep("logger", logger)
    portfolio_cls = resolve_dep("Portfolio", Portfolio)

    if dry_run:
        log.info("[DRY RUN] Skipping pre-analysis dust cleanup portfolio modifications.")
        return

    from analysis.analyze import MODELS
    from execution.market_data import MarketDataManager

    log.info("Starting Pre-Analysis Dust Cleanup...")
    mdm = MarketDataManager()
    total_cleaned = 0
    cleaned_tickers = []

    for config in MODELS:
        model = config["model"]
        try:
            portfolio = portfolio_cls(owner_id=model)
            await portfolio.initialize()

            if not portfolio.positions:
                log.info(f"[{model}] No positions to check.")
                continue

            log.info(f"[{model}] Checking {len(portfolio.positions)} positions for dust...")

            quotes = await mdm.get_quotes(list(portfolio.positions.keys()))
            price_map = {ticker: data.price for ticker, data in quotes.items()}

            if portfolio.metrics:
                threshold = portfolio.metrics.total_equity * 0.10
                log.info(
                    f"[{model}] 10% dust threshold: ${threshold:,.2f} (total equity: ${portfolio.metrics.total_equity:,.2f})"
                )

            before_positions = list(portfolio.positions.keys())
            await portfolio._check_and_sell_dust_positions(price_map)

            for ticker in before_positions:
                if ticker not in portfolio.positions:
                    cleaned_tickers.append((model, ticker))
                    total_cleaned += 1

        except Exception:
            log.exception(f"Dust cleanup failed for {model}")

    log.info(f"Pre-Analysis Dust Cleanup complete. Cleaned {total_cleaned} dust positions: {cleaned_tickers}")


async def _stage_analysis_and_consensus(data, sb_client):
    """Stage 2: Run parallel LLM analysis and event consensus."""
    log = resolve_dep("logger", logger)
    analyze_fn = resolve_dep("analyze_chunks", analyze_chunks)

    log.info("Starting Parallel LLM Analysis...")
    try:
        decisions, macro_events, aggregated_context, uncrowded_context = await analyze_fn(data)
        log.info(f"Analysis complete. Generated {len(decisions)} decisions and {len(macro_events)} raw macro events.")

        if not decisions and not macro_events:
            log.warning("No decisions or events generated from analysis. Check LLM provider connectivity.")

        return decisions, macro_events, aggregated_context, uncrowded_context
    except Exception as e:
        log.error(f"Analysis failed: {e}")
        return [], [], "", ""


async def _stage_snapshots_and_pca(sb_client, dry_run: bool = False):
    """Stage 4: Performance snapshots and PCA updates."""
    log = resolve_dep("logger", logger)
    portfolio_cls = resolve_dep("Portfolio", Portfolio)
    update_pca_fn = resolve_dep("update_pca_coordinates", update_pca_coordinates)

    if dry_run:
        log.info("[DRY RUN] Skipping portfolio daily performance snapshots and PCA updates.")
        return

    log.info("Starting Daily Performance Snapshot...")
    port_res = sb_client.table("portfolios").select("owner_id").execute()
    owners = [p["owner_id"] for p in port_res.data] if port_res.data else []

    if owners:
        from execution.market_data import MarketDataManager

        mdm = MarketDataManager()
        all_tickers = set()
        active_portfolios = []
        open_shorts_by_portfolio: dict[str, list[dict]] = {}

        for owner in owners:
            p = portfolio_cls(owner_id=owner)
            await p.initialize()
            if p.positions:
                all_tickers.update(p.positions.keys())
                active_portfolios.append(p)

            if owner.startswith("sys-sector-ls-") and p.id:
                try:
                    short_res = (
                        sb_client.table("trades")
                        .select("ticker, price, quantity")
                        .eq("portfolio_id", str(p.id))
                        .eq("signal", "SHORT")
                        .is_("realized_pnl", "null")
                        .execute()
                    )
                    shorts = short_res.data or []
                    if shorts:
                        open_shorts_by_portfolio[str(p.id)] = shorts
                        all_tickers.update([s["ticker"] for s in shorts])
                        if p not in active_portfolios:
                            active_portfolios.append(p)
                except Exception as ex:
                    log.warning(f"Could not load open shorts for {owner}: {ex}")

        if all_tickers:
            quotes = await mdm.get_quotes(list(all_tickers))
            price_map = {t: data.price for t, data in quotes.items()}

            async def _update_portfolio(p):
                p.calculate_reg_t_metrics(price_map)
                if p.id and str(p.id) in open_shorts_by_portfolio:
                    shorts = open_shorts_by_portfolio[str(p.id)]
                    short_unrealized = sum(
                        (float(s["price"]) - price_map.get(s["ticker"], float(s["price"]))) * int(s["quantity"])
                        for s in shorts
                    )
                    p.metrics.total_equity += short_unrealized
                    p.metrics.excess_liquidity += short_unrealized

                await p.record_performance_snapshot(price_map)
                await p.save_metrics()

            await asyncio.gather(*[_update_portfolio(p) for p in active_portfolios])

    log.info("Updating PCA coordinates...")
    update_pca_fn(sb_client)
