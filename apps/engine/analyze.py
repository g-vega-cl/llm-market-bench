
import asyncio
import logging
from apps.engine.core import llm
from apps.engine.core.models import DecisionObject

logger = logging.getLogger("engine")

# Configuration for models to use
MODELS = [
    {"provider": "openai", "model": llm.config.OPENAI_MODEL},
    {"provider": "anthropic", "model": llm.config.ANTHROPIC_MODEL},
    {"provider": "gemini", "model": llm.config.GEMINI_MODEL},
    {"provider": "deepseek", "model": llm.config.DEEPSEEK_MODEL},
]

async def analyze_chunks(chunks: list[dict]) -> list[DecisionObject]:
    """
    Orchestrate the parallel analysis of newsletter chunks using multiple LLMs.
    
    Args:
        chunks: List of dicts with 'source_id' and 'text'.
        
    Returns:
        List of DecisionObject instances (one per model per chunk).
    """
    tasks = []
    
    for chunk in chunks:
        source_id = chunk.get("source_id")
        text = chunk.get("content")
        
        if not source_id or not text:
            logger.warning(f"Skipping malformed chunk: {chunk.keys()}")
            continue
            
        for config in MODELS:
            provider = config["provider"]
            model = config["model"]
            
            # Create async task for each model/chunk combo
            task = llm.analyze_with_provider(
                provider=provider,
                model_name=model,
                text=text,
                source_id=source_id
            )
            tasks.append(task)

    if not tasks:
        logger.warning("No analysis tasks created.")
        return []

    logger.info(f"Starting {len(tasks)} analysis tasks across {len(chunks)} chunks and {len(MODELS)} models.")
    
    # Run all tasks in parallel
    # return_exceptions=True allows some to fail without crashing the whole batch
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid_decisions = []
    for res in results:
        if isinstance(res, Exception):
            logger.error(f"Analysis task failed: {res}")
            # Optionally retry or ignore
        elif isinstance(res, DecisionObject):
            valid_decisions.append(res)
            
    logger.info(f"Completed analysis. {len(valid_decisions)}/{len(tasks)} successful.")
    return valid_decisions
