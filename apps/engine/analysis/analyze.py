"""Parallel LLM analysis orchestrator.

This module orchestrates the parallel analysis of newsletter chunks using
multiple LLM providers (OpenAI, Claude, Gemini, DeepSeek).
"""

import asyncio
import logging

from core import llm
from core.config import ANTHROPIC_MODEL, DEEPSEEK_MODEL, GEMINI_MODEL, OPENAI_MODEL, logger
from core.db import get_supabase_client
from core.models import DecisionObject, MacroEvent
from execution.market_data import MarketDataManager
from execution.portfolio import Portfolio
from memory.store import get_top_trending_concepts, retrieve_top_memories

logger = logging.getLogger("engine")

# Configuration for models to use
MODELS = [
    {"provider": "openai", "model": OPENAI_MODEL},
    {"provider": "anthropic", "model": ANTHROPIC_MODEL},
    {"provider": "gemini", "model": GEMINI_MODEL},
    {"provider": "deepseek", "model": DEEPSEEK_MODEL},
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


async def analyze_chunks(chunks: list[dict]) -> tuple[list[DecisionObject], list[MacroEvent], str, str]:
    """Orchestrate the parallel analysis of newsletter chunks using multiple LLMs.

    Args:
        chunks: List of newsletter chunk dictionaries, each containing
            'source_id' and 'content' keys.

    Returns:
        Tuple of (list of DecisionObject, list of MacroEvent, str (aggregated_context), str (uncrowded_context)).
        Failed analyses are logged but do not halt the pipeline.
    """
    if not chunks:
        logger.warning("No chunks to analyze.")
        return [], [], "", ""

    # 1. Filter malformed chunks and aggregate historical context
    valid_chunks = [
        c for c in chunks 
        if c.get("source_id") and c.get("content")
    ]
    
    if len(valid_chunks) < len(chunks):
        logger.warning(f"Skipped {len(chunks) - len(valid_chunks)} malformed chunks.")

    if not valid_chunks:
        logger.warning("No valid chunks to analyze after filtering.")
        return [], [], "", ""

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
        uncrowded_context = ""
    else:
        aggregated_context = ""
        uncrowded_context = ""

    # 1. Initialize all portfolios and fetch prices in parallel for all models
    portfolios = {}
    all_tickers = set()
    for config in MODELS:
        model = config["model"]
        portfolio = Portfolio(owner_id=model)
        await portfolio.initialize()
        portfolios[model] = portfolio
        all_tickers.update(portfolio.positions.keys())
    
    # 2. Batch fetch prices for all unique holdings
    market_data = MarketDataManager()
    
    from core.macro_tracker import get_global_macro_context
    macro_context_str = await get_global_macro_context(market_data)
    
    price_map = {}
    if all_tickers:
        logger.info(f"Fetching current prices for {len(all_tickers)} unique portfolio tickers in parallel...")
        quotes = await market_data.get_quotes(list(all_tickers))
        price_map = {ticker: data.price for ticker, data in quotes.items()}
    
    tasks = []
    task_configs = [] # NEW: Keep track of which model is associated with each task
    for config in MODELS:
        provider = config["provider"]
        model = config["model"]

        # Use pre-initialized portfolio and pre-fetched prices
        portfolio = portfolios[model]
        portfolio.calculate_reg_t_metrics(price_map)
        await portfolio.save_metrics()
        
        portfolio_ctx = await portfolio.get_portfolio_summary(price_map)

        # Idempotency Filter: Skip chunks that this model has already analyzed
        # We check the decisions table for (source_id, model_name)
        chunks_to_analyze = []
        try:
            sb_client = get_supabase_client()
            source_ids = [c["source_id"] for c in valid_chunks]
            
            # Query for existing decisions for this model and these source_ids
            existing_res = sb_client.table("decisions").select("source_id").eq("model_name", model).in_("source_id", source_ids).execute()
            
            analyzed_ids = set([r["source_id"] for r in existing_res.data or []])
            chunks_to_analyze = [c for c in valid_chunks if c["source_id"] not in analyzed_ids]
            
            if len(chunks_to_analyze) < len(valid_chunks):
                logger.info(f"[{model}] Skipping {len(valid_chunks) - len(chunks_to_analyze)} chunks already analyzed.")
                
        except Exception as filter_err:
            logger.error(f"Error filtering idempotent chunks for {model}: {filter_err}")
            chunks_to_analyze = valid_chunks # Fallback to all if DB fails

        if not chunks_to_analyze:
            logger.info(f"[{model}] All chunks already analyzed. Skipping analysis task.")
            continue

        import calendar
        from datetime import datetime
        
        now = datetime.now()
        day_info = f"Today is {now.strftime('%A, %B %d, %Y')}."
        
        # Check Month Boundaries (ToM)
        last_day = calendar.monthrange(now.year, now.month)[1]
        days_to_end = last_day - now.day
        if now.day in [1, 2, 3]:
            day_info += f" We are in the Turn of the Month (ToM) window (Day {now.day})."
        elif days_to_end == 0:
            day_info += " Today is the LAST trading day of the month (ToM Start)."
        else:
            day_info += f" {days_to_end} days until month-end."
            
        # Check Payday Anomaly
        if now.day == 15:
            day_info += " Today is mid-month (Payday Anomaly)."
        elif now.day == 14:
            day_info += " Tomorrow is mid-month payday."
            
        from core.llm.prompts import CALENDAR_STRATEGY_KNOWLEDGE
        
        # --- Chunk Batching (Best Practice) ---
        # We split news chunks into batches of 20 to ensure:
        # 1. Output Token Safety: Prevents exceeding the 16k output limit (esp. Claude-Haiku 4.5).
        # 2. Reasoning Quality: Models perform better when focused on 10 stories vs 50+.
        # 3. Parallelism: Multiple smaller calls finish faster than one giant call.
        BATCH_SIZE = 20
        for i in range(0, len(chunks_to_analyze), BATCH_SIZE):
            batch = chunks_to_analyze[i:i + BATCH_SIZE]
            
            # Store metadata about the chunk list to reconstruct results later
            tasks.append(llm.analyze_with_provider(
                provider=provider,
                model_name=model,
                chunks=batch,
                context=aggregated_context,
                portfolio_context=portfolio_ctx,
                current_day_info=day_info,
                calendar_knowledge=CALENDAR_STRATEGY_KNOWLEDGE,
                macro_context=macro_context_str
            ))
            task_configs.append(config) # Track this task's model info

    logger.info(
        f"Starting {len(tasks)} parallel model calls (batched) across "
        f"{len(chunks)} original chunks and {len(MODELS)} models."
    )

    try:
        # 3. Run all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_decisions = []
        valid_events = []
        
        # 4. Process results
        for i, res in enumerate(results):
            config = task_configs[i] # Use the tracked config for this specific task

            if isinstance(res, Exception):
                logger.error(f"Batch analysis task failed for {config['provider']} ({config['model']}): {res}")
            else:
                # res is a DecisionsResponse object
                # Process decisions
                for j, decision in enumerate(res.decisions):
                    decision.model_provider = config["provider"]
                    decision.model_name = config["model"]
                    # original_index preserves the order within the task batch results
                    # and implicitly the batch sequence. Since each model's batches
                    # are generated in order, this number remains unique and stable per model.
                    decision.original_index = (i * 1000) + j

                    # Backfill injected_market_price if missing but ticker is present
                    if decision.ticker and (getattr(decision, "injected_market_price", None) is None):
                        try:
                            logger.info(f"[{config['model']}] Price missing for {decision.ticker}. Backfilling from market data...")
                            mdm = MarketDataManager()
                            quote = await mdm.get_quote(decision.ticker)
                            if quote and quote.exists:
                                decision.injected_market_price = quote.price
                                logger.info(f"[{config['model']}] Backfilled {decision.ticker} price: ${decision.injected_market_price:.2f}")
                        except Exception as bp_err:
                            logger.warning(f"Failed to backfill price for {decision.ticker}: {bp_err}")

                    valid_decisions.append(decision)
                
                # Process macro events
                for event in res.macro_events:
                    event.model_provider = config["provider"]
                    event.model_name = config["model"]
                    valid_events.append(event)

        # Check for total or partial LLM failures
        if not valid_decisions and not valid_events:
            exception_count = sum(1 for r in results if isinstance(r, Exception))
            if exception_count == len(MODELS):
                logger.error(
                    f"CRITICAL: All {len(MODELS)} LLM providers failed. "
                    f"No decisions or events generated. Pipeline continuing but data is incomplete."
                )
            elif exception_count > 0:
                logger.warning(
                    f"{exception_count}/{len(MODELS)} LLM providers failed. "
                    f"No results generated from successful providers."
                )

        logger.info(
            f"Completed analysis. Generated {len(valid_decisions)} decisions "
            f"and {len(valid_events)} macro events from {len(results)} batched calls."
        )
        return valid_decisions, valid_events, aggregated_context, uncrowded_context
    finally:
        from execution.providers.factory import get_active_provider_class
        provider_cls = get_active_provider_class()
        await provider_cls.disconnect_all()


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

    valid_chunks = [
        c for c in chunks 
        if c.get("source_id") and c.get("content")
    ]
    
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
        uncrowded_context = ""
    else:
        aggregated_context = ""
        uncrowded_context = ""

    portfolios = {}
    all_tickers = set()
    for config in MODELS:
        model = config["model"]
        portfolio = Portfolio(owner_id=model)
        await portfolio.initialize()
        portfolios[model] = portfolio
        all_tickers.update(portfolio.positions.keys())
    
    market_data = MarketDataManager()
    
    from core.macro_tracker import get_global_macro_context
    macro_context_str = await get_global_macro_context(market_data)
    
    price_map = {}
    if all_tickers:
        logger.info(f"Fetching current prices for {len(all_tickers)} unique portfolio tickers in parallel...")
        quotes = await market_data.get_quotes(list(all_tickers))
        price_map = {ticker: data.price for ticker, data in quotes.items()}
    
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
            
            existing_res = sb_client.table("decisions").select("source_id").eq("model_name", model).in_("source_id", source_ids).execute()
            
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
        from datetime import datetime
        
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
            batch = chunks_to_analyze[i:i + BATCH_SIZE]
            
            tasks.append(llm.analyze_with_provider(
                provider=provider,
                model_name=model,
                chunks=batch,
                context=aggregated_context,
                portfolio_context=portfolio_ctx,
                current_day_info=day_info,
                calendar_knowledge=CALENDAR_STRATEGY_KNOWLEDGE,
                macro_context=macro_context_str
            ))
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
