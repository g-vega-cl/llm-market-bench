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
from memory.store import retrieve_context

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
    tasks = []

    for chunk in chunks:
        source_id = chunk.get("source_id")
        text = chunk.get("content")

        # Retrieve historical context once per chunk
        context = retrieve_context(text)

        for config in MODELS:
            provider = config["provider"]
            model = config["model"]

            tasks.append(llm.analyze_with_provider(
                provider=provider,
                model_name=model,
                text=text,
                source_id=source_id,
                context=context
            ))

    if not tasks:
        logger.warning("No analysis tasks created.")
        return []

    logger.info(
        f"Starting {len(tasks)} analysis tasks across "
        f"{len(chunks)} chunks and {len(MODELS)} models."
    )

    # Run all tasks in parallel, collecting exceptions instead of raising
    results = await asyncio.gather(*tasks, return_exceptions=True)

    valid_decisions = []
    for res in results:
        if isinstance(res, Exception):
            logger.error(f"Analysis task failed: {res}")
        elif isinstance(res, DecisionObject):
            valid_decisions.append(res)

    logger.info(f"Completed analysis. {len(valid_decisions)}/{len(tasks)} successful.")
    return valid_decisions
