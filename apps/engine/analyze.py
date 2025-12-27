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
from core.models import DecisionObject
from memory.store import retrieve_context_batch

logger = logging.getLogger("engine")

# Configuration for models to use
MODELS = [
    {"provider": "openai", "model": OPENAI_MODEL},
    {"provider": "anthropic", "model": ANTHROPIC_MODEL},
    {"provider": "gemini", "model": GEMINI_MODEL},
    {"provider": "deepseek", "model": DEEPSEEK_MODEL},
]


async def analyze_chunks(chunks: list[dict]) -> list[DecisionObject]:
    """Orchestrate the parallel analysis of newsletter chunks using multiple LLMs.

    Args:
        chunks: List of newsletter chunk dictionaries, each containing
            'source_id' and 'content' keys.

    Returns:
        List of DecisionObject instances from successful analyses.
        Failed analyses are logged but do not halt the pipeline.
    """
    if not chunks:
        logger.warning("No chunks to analyze.")
        return []

    # 1. Filter malformed chunks and aggregate historical context
    valid_chunks = [
        c for c in chunks 
        if c.get("source_id") and c.get("content")
    ]
    
    if len(valid_chunks) < len(chunks):
        logger.warning(f"Skipped {len(chunks) - len(valid_chunks)} malformed chunks.")

    if not valid_chunks:
        logger.warning("No valid chunks to analyze after filtering.")
        return []

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
    
    # 4. Process results
    for i, res in enumerate(results):
        config = MODELS[i]
        
        if isinstance(res, Exception):
            logger.error(f"Batch analysis task failed for {config['provider']}: {res}")
        elif isinstance(res, list):
            # Inspect specifically for lists of DecisionObjects
            for decision in res:
                if isinstance(decision, DecisionObject):
                    # Ensure model metadata is attached for attribution
                    decision.model_provider = config["provider"]
                    decision.model_name = config["model"]
                    valid_decisions.append(decision)
                else:
                    logger.warning(f"Unexpected item in response from {config['provider']}: {type(decision)}")

    logger.info(f"Completed analysis. Generated {len(valid_decisions)} decisions from batch processing.")
    return valid_decisions
