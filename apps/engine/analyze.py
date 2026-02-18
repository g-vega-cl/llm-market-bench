"""Parallel LLM analysis orchestrator.

This module orchestrates the parallel analysis of newsletter chunks using
multiple LLM providers (OpenAI, Claude, Gemini, DeepSeek).
"""

import asyncio
import logging

from core import llm
from core.config import (
    OPENAI_MODEL,
    ANTHROPIC_MODEL,
    GEMINI_MODEL,
    DEEPSEEK_MODEL,
)
from core.models import DecisionObject, MacroEvent
from execution.portfolio import Portfolio
from execution.market_data import MarketDataManager
from memory.store import retrieve_context_batch

logger = logging.getLogger("engine")

# Configuration for models to use
MODELS = [
    {"provider": "openai", "model": OPENAI_MODEL},
    {"provider": "anthropic", "model": ANTHROPIC_MODEL},
    {"provider": "gemini", "model": GEMINI_MODEL},
    {"provider": "deepseek", "model": DEEPSEEK_MODEL},
]


async def analyze_chunks(chunks: list[dict]) -> tuple[list[DecisionObject], list[MacroEvent]]:
    """Orchestrate the parallel analysis of newsletter chunks using multiple LLMs.

    Args:
        chunks: List of newsletter chunk dictionaries, each containing
            'source_id' and 'content' keys.

    Returns:
        Tuple of (list of DecisionObject, list of MacroEvent).
        Failed analyses are logged but do not halt the pipeline.
    """
    if not chunks:
        logger.warning("No chunks to analyze.")
        return [], [], ""

    # 1. Filter malformed chunks and aggregate historical context
    valid_chunks = [
        c for c in chunks 
        if c.get("source_id") and c.get("content")
    ]
    
    if len(valid_chunks) < len(chunks):
        logger.warning(f"Skipped {len(chunks) - len(valid_chunks)} malformed chunks.")

    if not valid_chunks:
        logger.warning("No valid chunks to analyze after filtering.")
        return [], [], ""

    queries = [chunk["content"] for chunk in valid_chunks]
    
    if queries:
        # 1. Generate embeddings once
        from memory.embeddings import get_embeddings_batch
        embeddings = get_embeddings_batch(queries)

        # 2. We retrieve standard context AND specifically look for government incentives & lessons
        # using the same embeddings to save API calls
        context_results = retrieve_context_batch(queries, embeddings=embeddings)

        # Explicitly fetch recent government incentives to ensure they are present
        gov_context = retrieve_context_batch(queries, limit=2, memory_types=["GOVERNMENT_INCENTIVE"], embeddings=embeddings)
        lesson_context = retrieve_context_batch(queries, limit=2, memory_types=["LESSON_LEARNED"], embeddings=embeddings)

        all_contexts = context_results + gov_context + lesson_context
        aggregated_context = "\n".join(list(set([c for c in all_contexts if c])))
    else:
        aggregated_context = ""

    tasks = []

    # 2. Create one analysis task per model (Batch Mode)
    for config in MODELS:
        provider = config["provider"]
        model = config["model"]

        # Initialize Portfolio & Context
        portfolio = Portfolio(owner_id=model)  # Using model name as owner_id
        await portfolio.initialize()
        
        # Get current prices for portfolio holdings
        # Note: In a real scenario, we'd batch fetch these. 
        # For now, we can rely on MarketDataManager's caching if we had a list of tickers.
        # But we need specific current prices to calculate equity.
        market_data = MarketDataManager()
        current_prices = {}
        for ticker in portfolio.positions.keys():
            quote = await market_data.get_quote(ticker)
            if quote:
                current_prices[ticker] = quote.price

        # Update metrics and save
        portfolio.calculate_reg_t_metrics(current_prices)
        await portfolio.save_metrics()
        
        portfolio_ctx = portfolio.get_portfolio_summary(current_prices)

        tasks.append(llm.analyze_with_provider(
            provider=provider,
            model_name=model,
            chunks=valid_chunks,
            context=aggregated_context,
            portfolio_context=portfolio_ctx
        ))

    logger.info(
        f"Starting {len(tasks)} batch analysis tasks across "
        f"{len(chunks)} chunks and {len(MODELS)} models."
    )

    try:
        # 3. Run all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_decisions = []
        valid_events = []
        
        # 4. Process results
        for i, res in enumerate(results):
            config = MODELS[i]
            
            if isinstance(res, Exception):
                logger.error(f"Batch analysis task failed for {config['provider']}: {res}")
            else:
                # res is a DecisionsResponse object
                # Process decisions
                for decision in res.decisions:
                    decision.model_provider = config["provider"]
                    decision.model_name = config["model"]
                    
                    # Backfill price if missing but ticker is present
                    if decision.ticker and (decision.price is None or decision.price <= 0):
                        try:
                            logger.info(f"[{config['model']}] Price missing for {decision.ticker}. Backfilling from market data...")
                            mdm = MarketDataManager()
                            quote = await mdm.get_quote(decision.ticker)
                            if quote and quote.exists:
                                decision.price = quote.price
                                logger.info(f"[{config['model']}] Backfilled {decision.ticker} price: ${decision.price:.2f}")
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
            f"and {len(valid_events)} macro events from batch processing."
        )
        return valid_decisions, valid_events, aggregated_context
    finally:
        from execution.providers.factory import get_active_provider_class
        provider_cls = get_active_provider_class()
        await provider_cls.disconnect_all()
