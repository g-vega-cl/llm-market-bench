"""Contrarian Agent analysis logic.

This agent analyzes the consensus of other agents and identifies
contrarian opportunities or missed risks.
"""

import asyncio
import logging
from typing import List, Tuple

from core.models import DecisionObject, MacroEvent, DecisionsResponse, ContrarianAgentResponse
from core.llm import get_gemini_client, prompts
from core.config import GEMINI_MODEL, logger
from execution.portfolio import Portfolio
from execution.market_data import MarketDataManager
from memory.store import retrieve_context_batch

async def run_contrarian_analysis(
    chunks: List[dict],
    other_decisions: List[DecisionObject],
    context: str = ""
) -> Tuple[List[DecisionObject], List[MacroEvent]]:
    """Runs the contrarian analysis using Gemini Flash 3.

    Args:
        chunks: The original news chunks.
        other_decisions: Decisions made by the primary LLM agents.
        context: Aggregated historical context.

    Returns:
        A tuple of (decisions, macro_events).
    """
    logger.info("Starting Contrarian Agent analysis...")

    # 1. Initialize Portfolio
    portfolio = Portfolio(owner_id="contrarian_agent")
    await portfolio.initialize()

    market_data = MarketDataManager()
    current_prices = {}
    if portfolio.positions:
        logger.info(f"Fetching current prices for {len(portfolio.positions)} contrarian portfolio tickers in parallel...")
        tickers = list(portfolio.positions.keys())
        price_tasks = [market_data.get_quote(ticker) for ticker in tickers]
        quotes = await asyncio.gather(*price_tasks)
        for quote in quotes:
            if quote:
                current_prices[quote.ticker] = quote.price

    portfolio.calculate_reg_t_metrics(current_prices)
    await portfolio.save_metrics()
    portfolio_ctx = await portfolio.get_portfolio_summary(current_prices)

    # 2. Prepare Context
    if not context:
        queries = [chunk["content"] for chunk in chunks if chunk.get("content")]
        if queries:
            context_results = retrieve_context_batch(queries)
            # Include government incentives and lessons for contrarian as well
            gov_context = retrieve_context_batch(queries, limit=2, memory_types=["GOVERNMENT_INCENTIVE"])
            lesson_context = retrieve_context_batch(queries, limit=2, memory_types=["LESSON_LEARNED"])
            all_contexts = context_results + gov_context + lesson_context
            context = "\n".join(list(set([c for c in all_contexts if c])))
    news_content = "".join([
        f"\n---\nSource ID: {chunk['source_id']}\nContent: {chunk['content']}\n---\n"
        for chunk in chunks
    ])

    decisions_context = ""
    for d in other_decisions:
        decisions_context += (
            f"- [{d.model_name}] {d.ticker}: {d.signal} (Conf: {d.confidence}%)\n"
            f"  Reasoning: {d.reasoning}\n"
        )

    if not decisions_context:
        decisions_context = "No consensus decisions available."

    # 3. Call Gemini Flash 3
    client = get_gemini_client()

    prompt = prompts.CONTRARIAN_USER_PROMPT_TEMPLATE.format(
        news_content=news_content,
        decisions_context=decisions_context,
        context=context,
        portfolio_context=portfolio_ctx
    )

    try:
        from core.models import DecisionsResponse
        from typing import List
        # Use List[DecisionsResponse] to handle Gemini emitting multiple tool call blocks
        # This is expected behavior with instructor.Mode.GENAI_TOOLS and multiple news chunks
        resp_awaitable = client.chat.completions.create(
            model=GEMINI_MODEL,
            response_model=List[DecisionsResponse],
            messages=[
                {"role": "system", "content": prompts.CONTRARIAN_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_retries=2
        )

        if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
            wrapper = await resp_awaitable
        else:
            wrapper = resp_awaitable

        if not wrapper:
             return [], []

        # Aggregate all decisions and macro events from all response blocks
        all_decisions = []
        all_events = []
        for decisions_resp in wrapper:
            all_decisions.extend(decisions_resp.decisions)
            all_events.extend(decisions_resp.macro_events)

        # Inject model info
        for d in all_decisions:
            d.model_provider = "gemini"
            d.model_name = "contrarian_agent"

        for e in all_events:
            e.model_provider = "gemini"
            e.model_name = "contrarian_agent"

        logger.info(f"Contrarian analysis complete. Generated {len(all_decisions)} decisions from {len(wrapper)} response blocks.")
        return all_decisions, all_events

    except Exception as e:
        logger.error(f"Contrarian analysis failed: {e}")
        return [], []
