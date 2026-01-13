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
        return [], []

    # 1. Filter malformed chunks and aggregate historical context
    valid_chunks = [
        c for c in chunks 
        if c.get("source_id") and c.get("content")
    ]
    
    if len(valid_chunks) < len(chunks):
        logger.warning(f"Skipped {len(chunks) - len(valid_chunks)} malformed chunks.")

    if not valid_chunks:
        logger.warning("No valid chunks to analyze after filtering.")
        return [], []

    queries = [chunk["content"] for chunk in valid_chunks]
    
    if queries:
        context_results = retrieve_context_batch(queries)
        aggregated_context = "\n".join([c for c in context_results if c])
    else:
        aggregated_context = ""

    tasks = []

    # 2. Create one analysis task per model (Batch Mode)
    for config in MODELS:
        provider = config["provider"]
        model = config["model"]

        tasks.append(llm.analyze_with_provider(
            provider=provider,
            model_name=model,
            chunks=valid_chunks,
            context=aggregated_context
        ))

    logger.info(
        f"Starting {len(tasks)} batch analysis tasks across "
        f"{len(chunks)} chunks and {len(MODELS)} models."
    )

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
    return valid_decisions, valid_events
