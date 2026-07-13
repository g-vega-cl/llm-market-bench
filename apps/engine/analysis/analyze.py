"""Parallel LLM analysis orchestrator.

This module orchestrates the parallel analysis of newsletter chunks using
multiple LLM providers (OpenAI, Claude, Gemini, DeepSeek).
"""

import asyncio
from datetime import datetime

from core import llm
from core.config import ANTHROPIC_MODEL, DEEPSEEK_MODEL, GEMINI_MODEL, MINIMAX_MODEL, OPENAI_MODEL, logger
from core.db import get_supabase_client
from core.models import DecisionObject, MacroEvent
from execution.market_data import MarketDataManager
from execution.portfolio import Portfolio
from memory.store import get_top_trending_concepts, retrieve_top_memories

# Configuration for models to use
MODELS = [
    {"provider": "openai", "model": OPENAI_MODEL},
    {"provider": "anthropic", "model": ANTHROPIC_MODEL},
    {"provider": "gemini", "model": GEMINI_MODEL},
    {"provider": "deepseek", "model": DEEPSEEK_MODEL},
    {"provider": "minimax", "model": MINIMAX_MODEL},
]


def _process_single_result(res, config, task_index):
    """Process a single model result and return decisions and events.

    Args:
        res: The result from analyze_with_provider (DecisionsResponse or Exception)
        config: The model config dict
        task_index: The index of this task for ordering

    Returns:
        Tuple of (list of DecisionObject, list of MacroEvent) - may be empty if failed
    """
    if isinstance(res, Exception):
        logger.error(f"Batch analysis task failed for {config['provider']} ({config['model']}): {res}")
        return [], []

    valid_decisions = []
    valid_events = []

    for j, decision in enumerate(res.decisions):
        decision.model_provider = config["provider"]
        decision.model_name = config["model"]
        decision.original_index = (task_index * 1000) + j
        valid_decisions.append(decision)

    for event in res.macro_events:
        event.model_provider = config["provider"]
        event.model_name = config["model"]
        valid_events.append(event)

    return valid_decisions, valid_events


async def analyze_macro_events(chunks: list[dict]) -> list[MacroEvent]:
    """Pass 1: Run parallel LLM analysis to extract macro events from newsletters/news chunks."""
    if not chunks:
        logger.warning("No chunks for macro analysis.")
        return []

    valid_chunks = [c for c in chunks if c.get("source_id") and c.get("content")]
    if not valid_chunks:
        logger.warning("No valid chunks for macro analysis.")
        return []

    from zoneinfo import ZoneInfo

    from core.models import MacroEventsResponse

    now = datetime.now(ZoneInfo("America/New_York"))
    day_info = f"Today is {now.strftime('%A, %B %d, %Y')}."

    tasks = []
    task_configs = []
    BATCH_SIZE = 20
    for config in MODELS:
        provider = config["provider"]
        model = config["model"]

        for i in range(0, len(valid_chunks), BATCH_SIZE):
            batch = valid_chunks[i : i + BATCH_SIZE]
            tasks.append(
                llm.analyze_with_provider(
                    provider=provider,
                    model_name=model,
                    chunks=batch,
                    current_day_info=day_info,
                    prompt_type="macro",
                    response_model=MacroEventsResponse,
                )
            )
            task_configs.append(config)

    logger.info(f"Starting {len(tasks)} parallel macro event extraction calls across {len(MODELS)} models...")
    results = await asyncio.gather(*tasks, return_exceptions=True)

    valid_events = []
    for i, res in enumerate(results):
        config = task_configs[i]
        if isinstance(res, Exception):
            logger.error(
                f"Batch analysis task failed for {config['provider']} ({config['model']}): {res}", exc_info=res
            )
        else:
            for event in getattr(res, "macro_events", []):
                event.model_provider = config["provider"]
                event.model_name = config["model"]
                valid_events.append(event)

    return valid_events


async def analyze_trading_decisions(
    chunks: list[dict], consensus_events: list[dict], sb_client
) -> tuple[list[DecisionObject], str]:
    """Pass 2: Run parallel LLM analysis to make trading decisions, using consensus context."""
    if not chunks:
        logger.warning("No chunks for trading analysis.")
        return [], ""

    valid_chunks = [c for c in chunks if c.get("source_id") and c.get("content")]
    if not valid_chunks:
        logger.warning("No valid chunks for trading analysis.")
        return [], ""

    # Build consensus events context block
    c_lines = ["=== SYNTHESIZED TODAY'S MACRO CONSENSUS EVENTS ==="]
    if consensus_events:
        for idx, event in enumerate(consensus_events):
            if hasattr(event, "event_name"):
                name = event.event_name
                summary = event.reasoning
                scenarios = getattr(event, "scenario_analysis", None)
            else:
                name = event.get("event_name", "Unknown Event")
                summary = event.get("summary", "No summary")
                scenarios = event.get("scenarios")
            c_lines.append(f"{idx + 1}. {name}")
            c_lines.append(f"   Summary: {summary}")
            if scenarios:
                c_lines.append(f"   Scenarios & Trading Plans: {scenarios}")
    else:
        c_lines.append("No consensus events promoted for today's session.")
    consensus_context_str = "\n".join(c_lines)

    # 1. Retrieve RAG and trending context
    [chunk["content"] for chunk in valid_chunks]
    historical_context = retrieve_top_memories(limit=5)
    trending_concepts = get_top_trending_concepts(limit=5)
    aggregated_context = historical_context
    if trending_concepts:
        if aggregated_context:
            aggregated_context += f"\n\n{trending_concepts}"
        else:
            aggregated_context = trending_concepts
    uncrowded_context = ""

    # Pre-filter newsletter summaries menu
    from .pre_filter import summarize_newsletters

    summaries = await summarize_newsletters(valid_chunks)

    # 2. Portfolios and holdings
    portfolios = {}
    all_holdings = set()
    for config in MODELS:
        model = config["model"]
        portfolio = Portfolio(owner_id=model)
        await portfolio.initialize()
        portfolios[model] = portfolio
        all_holdings.update(portfolio.positions.keys())

    # 3. Extract news tickers + holdings + major indices
    from core.llm.analysis import _extract_tickers_from_chunks

    all_tickers = _extract_tickers_from_chunks(valid_chunks, list(all_holdings))

    # 4. Fetch quotes & verified market data block
    market_data = MarketDataManager()
    from core.macro_tracker import get_global_macro_context

    macro_context_str = await get_global_macro_context(market_data)

    price_map = {}
    quotes = {}
    if all_tickers:
        logger.info(f"Fetching current prices for {len(all_tickers)} unique tickers in parallel...")
        quotes = await market_data.get_quotes(list(all_tickers))
        price_map = {ticker: data.price for ticker, data in quotes.items()}

    mkt_lines = ["=== VERIFIED MARKET DATA ==="]
    for t in sorted(all_tickers):
        q = quotes.get(t)
        if q and q.exists:
            mkt_lines.append(f"  {t:<6} ${q.price:.2f}  Market Cap: ${q.market_cap / 1e9:.2f}B  Status: VALID")
    mkt_lines.append("GROUND RULES: Trades execute at market price at settlement. Do NOT produce price fields.")
    market_data_block = "\n".join(mkt_lines)

    # 5. Calendar dates context
    import calendar

    from core.llm.prompts import CALENDAR_STRATEGY_KNOWLEDGE
    from core.models import TradingDecisionsResponse

    now = datetime.now()
    day_info = f"Today is {now.strftime('%A, %B %d, %Y')}."
    last_day = calendar.monthrange(now.year, now.month)[1]
    days_to_end = last_day - now.day
    if now.day in [1, 2, 3]:
        day_info += f" We are in the Turn of the Month (ToM) window (Day {now.day})."
    elif days_to_end == 0:
        day_info += " Today is the LAST trading day of the month (ToM Start)."
    else:
        day_info += f" {days_to_end} days until month-end."

    if now.day == 15:
        day_info += " Today is mid-month (Payday Anomaly)."
    elif now.day == 14:
        day_info += " Tomorrow is mid-month payday."

    # 6. Construct tasks for trading pass
    tasks = []
    task_configs = []
    for config in MODELS:
        provider = config["provider"]
        model = config["model"]

        portfolio = portfolios[model]
        portfolio.calculate_reg_t_metrics(price_map)
        await portfolio.save_metrics()
        portfolio_ctx = await portfolio.get_portfolio_summary(price_map)

        # Idempotency Filter
        chunks_to_analyze = []
        try:
            source_ids = [c["source_id"] for c in valid_chunks]
            existing_res = (
                sb_client.table("decisions")
                .select("source_id")
                .eq("model_name", model)
                .in_("source_id", source_ids)
                .execute()
            )
            analyzed_ids = set([r["source_id"] for r in existing_res.data or []])
            chunks_to_analyze = [c for c in valid_chunks if c["source_id"] not in analyzed_ids]
            if len(chunks_to_analyze) < len(valid_chunks):
                logger.info(f"[{model}] Skipping {len(valid_chunks) - len(chunks_to_analyze)} chunks already analyzed.")
        except Exception:
            logger.exception(f"Error filtering idempotent chunks for {model}")
            chunks_to_analyze = valid_chunks

        if not chunks_to_analyze:
            logger.info(f"[{model}] All chunks already analyzed. Skipping analysis task.")
            continue

        BATCH_SIZE = 20
        for i in range(0, len(chunks_to_analyze), BATCH_SIZE):
            batch = chunks_to_analyze[i : i + BATCH_SIZE]
            tasks.append(
                llm.analyze_with_provider(
                    provider=provider,
                    model_name=model,
                    chunks=batch,
                    context=aggregated_context,
                    portfolio_context=portfolio_ctx,
                    current_day_info=day_info,
                    calendar_knowledge=CALENDAR_STRATEGY_KNOWLEDGE,
                    macro_context=macro_context_str,
                    summaries=summaries,
                    market_data_block=market_data_block,
                    response_model=TradingDecisionsResponse,
                    prompt_type="analysis",
                    consensus_context=consensus_context_str,
                )
            )
            task_configs.append(config)

    logger.info(f"Starting {len(tasks)} parallel trading analysis calls...")
    results = await asyncio.gather(*tasks, return_exceptions=True)

    valid_decisions = []
    for i, res in enumerate(results):
        config = task_configs[i]
        if isinstance(res, Exception):
            logger.error(
                f"Batch analysis task failed for {config['provider']} ({config['model']}): {res}", exc_info=res
            )
        else:
            for j, decision in enumerate(res.decisions):
                decision.model_provider = config["provider"]
                decision.model_name = config["model"]
                decision.original_index = (i * 1000) + j

                # Stamp injected_market_price
                if decision.ticker and (getattr(decision, "injected_market_price", None) is None):
                    ticker = decision.ticker.upper()
                    if ticker in price_map:
                        decision.injected_market_price = price_map[ticker]
                    else:
                        try:
                            logger.info(
                                f"[{config['model']}] Price missing for {ticker} (tool-called). Backfilling from market data..."
                            )
                            mdm = MarketDataManager()
                            quote = await mdm.get_quote(ticker)
                            if quote and quote.exists:
                                decision.injected_market_price = quote.price
                        except Exception as bp_err:
                            logger.warning(f"Failed to backfill price for {ticker}: {bp_err}")

                valid_decisions.append(decision)

    return valid_decisions, uncrowded_context


async def analyze_chunks(chunks: list[dict]) -> tuple[list[DecisionObject], list[MacroEvent], str, str]:
    """Legacy combined analysis orchestrator. Decouples internally to maintain backward compatibility."""
    logger.info("Executing legacy analyze_chunks via decoupled sequential pipelines...")
    sb_client = get_supabase_client()
    macro_events = await analyze_macro_events(chunks)

    from analysis.consensus import process_consensus

    consensus_events = await process_consensus(macro_events)

    decisions, uncrowded_ctx = await analyze_trading_decisions(chunks, consensus_events, sb_client)

    # Retrieve RAG context as aggregated context to match legacy return
    [c for c in chunks if c.get("source_id") and c.get("content")]
    historical_context = retrieve_top_memories(limit=5)
    trending_concepts = get_top_trending_concepts(limit=5)
    aggregated_context = historical_context
    if trending_concepts:
        if aggregated_context:
            aggregated_context += f"\n\n{trending_concepts}"
        else:
            aggregated_context = trending_concepts

    return decisions, macro_events, aggregated_context, uncrowded_ctx


async def analyze_chunks_streaming(chunks: list[dict]):
    """Streaming version of analyze_chunks that yields results as each model completes.

    This is an async generator that yields (decisions, events, config) tuples
    as each model finishes analysis, allowing decision execution to start
    before all models have completed.

    Args:
        chunks: List of newsletter chunk dictionaries, each containing
            'source_id' and 'content' keys.

    Yields:
        Tuple of (list of DecisionObject, list of MacroEvent, config dict)
        for each model as it completes. Multiple yields per model are possible
        if a model has multiple batches.
    """
    if not chunks:
        logger.warning("No chunks to analyze.")
        return

    valid_chunks = [c for c in chunks if c.get("source_id") and c.get("content")]

    # Pre-filter newsletters to generate a concise summary menu
    from .pre_filter import summarize_newsletters

    summaries = await summarize_newsletters(valid_chunks)

    if len(valid_chunks) < len(chunks):
        logger.warning(f"Skipped {len(chunks) - len(valid_chunks)} malformed chunks.")

    if not valid_chunks:
        logger.warning("No valid chunks to analyze after filtering.")
        return

    queries = [chunk["content"] for chunk in valid_chunks]

    if queries:
        historical_context = retrieve_top_memories(limit=5)
        trending_concepts = get_top_trending_concepts(limit=5)
        aggregated_context = historical_context
        if trending_concepts:
            if aggregated_context:
                aggregated_context += f"\n\n{trending_concepts}"
            else:
                aggregated_context = trending_concepts
    else:
        aggregated_context = ""

    # 1. Initialize all portfolios and collect holdings
    portfolios = {}
    all_holdings = set()
    for config in MODELS:
        model = config["model"]
        portfolio = Portfolio(owner_id=model)
        await portfolio.initialize()
        portfolios[model] = portfolio
        all_holdings.update(portfolio.positions.keys())

    # 2. Extract news tickers + holdings + major indices
    from core.llm.analysis import _extract_tickers_from_chunks

    all_tickers = _extract_tickers_from_chunks(valid_chunks, list(all_holdings))

    # 3. Batch fetch prices for all unique tickers in parallel
    market_data = MarketDataManager()

    from core.macro_tracker import get_global_macro_context

    macro_context_str = await get_global_macro_context(market_data)

    price_map = {}
    quotes = {}
    if all_tickers:
        logger.info(f"Fetching current prices for {len(all_tickers)} unique tickers in parallel...")
        quotes = await market_data.get_quotes(list(all_tickers))
        price_map = {ticker: data.price for ticker, data in quotes.items()}

    # 4. Construct the common verified market data block for injected context
    mkt_lines = ["=== VERIFIED MARKET DATA ==="]
    for t in sorted(all_tickers):
        q = quotes.get(t)
        if q and q.exists:
            mkt_lines.append(f"  {t:<6} ${q.price:.2f}  Market Cap: ${q.market_cap / 1e9:.2f}B  Status: VALID")
    mkt_lines.append("GROUND RULES: Trades execute at market price at settlement. Do NOT produce price fields.")
    market_data_block = "\n".join(mkt_lines)

    tasks = []
    task_configs = []

    for config in MODELS:
        provider = config["provider"]
        model = config["model"]

        portfolio = portfolios[model]
        portfolio.calculate_reg_t_metrics(price_map)
        await portfolio.save_metrics()

        portfolio_ctx = await portfolio.get_portfolio_summary(price_map)

        chunks_to_analyze = []
        try:
            sb_client = get_supabase_client()
            source_ids = [c["source_id"] for c in valid_chunks]

            existing_res = (
                sb_client.table("decisions")
                .select("source_id")
                .eq("model_name", model)
                .in_("source_id", source_ids)
                .execute()
            )

            analyzed_ids = set([r["source_id"] for r in existing_res.data or []])
            chunks_to_analyze = [c for c in valid_chunks if c["source_id"] not in analyzed_ids]

            if len(chunks_to_analyze) < len(valid_chunks):
                logger.info(f"[{model}] Skipping {len(valid_chunks) - len(chunks_to_analyze)} chunks already analyzed.")

        except Exception as filter_err:
            logger.error(f"Error filtering idempotent chunks for {model}: {filter_err}")
            chunks_to_analyze = valid_chunks

        if not chunks_to_analyze:
            logger.info(f"[{model}] All chunks already analyzed. Skipping analysis task.")
            continue

        import calendar

        now = datetime.now()
        day_info = f"Today is {now.strftime('%A, %B %d, %Y')}."

        last_day = calendar.monthrange(now.year, now.month)[1]
        days_to_end = last_day - now.day
        if now.day in [1, 2, 3]:
            day_info += f" We are in the Turn of the Month (ToM) window (Day {now.day})."
        elif days_to_end == 0:
            day_info += " Today is the LAST trading day of the month (ToM Start)."
        else:
            day_info += f" {days_to_end} days until month-end."

        if now.day == 15:
            day_info += " Today is mid-month (Payday Anomaly)."
        elif now.day == 14:
            day_info += " Tomorrow is mid-month payday."

        from core.llm.prompts import CALENDAR_STRATEGY_KNOWLEDGE

        BATCH_SIZE = 20
        for i in range(0, len(chunks_to_analyze), BATCH_SIZE):
            batch = chunks_to_analyze[i : i + BATCH_SIZE]

            tasks.append(
                llm.analyze_with_provider(
                    provider=provider,
                    model_name=model,
                    chunks=batch,
                    context=aggregated_context,
                    portfolio_context=portfolio_ctx,
                    current_day_info=day_info,
                    calendar_knowledge=CALENDAR_STRATEGY_KNOWLEDGE,
                    macro_context=macro_context_str,
                    summaries=summaries,
                    market_data_block=market_data_block,
                )
            )
            task_configs.append(config)

    logger.info(
        f"Starting {len(tasks)} parallel model calls (batched) across "
        f"{len(valid_chunks)} original chunks and {len(MODELS)} models."
    )

    try:
        # Create task futures with their metadata bundled
        futures_with_meta = []
        for i, t in enumerate(tasks):
            future = asyncio.create_task(t)
            futures_with_meta.append((future, i, task_configs[i]))

        # Wait for all to complete
        pending = set(f for f, _, _ in futures_with_meta)

        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

            for future in done:
                # Find the metadata for this future
                for f, idx, cfg in futures_with_meta:
                    if f == future:
                        try:
                            res = await future
                            decisions, events = _process_single_result(res, cfg, idx)

                            if decisions or events:
                                logger.info(
                                    f"[{cfg['model']}] Model completed. "
                                    f"Generated {len(decisions)} decisions and {len(events)} events."
                                )
                                yield (decisions, events, cfg)

                        except Exception as e:
                            logger.error(f"Error processing result for {cfg['model']}: {e}")
                            yield ([], [], cfg)
                        break

    finally:
        from execution.providers.factory import get_active_provider_class

        provider_cls = get_active_provider_class()
        await provider_cls.disconnect_all()
