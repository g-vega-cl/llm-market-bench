"""Logging utility for LLM reasoning traces."""

import logging
from typing import Any, List, Optional
from datetime import datetime, UTC

from core.db import get_supabase_client
from core.config import logger as pipeline_logger

logger = logging.getLogger("engine.llm_logger")

async def log_reasoning_trace(
    task_type: str,
    model_provider: str,
    model_name: str,
    prompt: List[dict],
    response: Any,
    metadata: Optional[dict] = None
) -> None:
    """Asynchronously logs an LLM reasoning trace to Supabase.
    
    Args:
        task_type: The category of the LLM task (e.g. 'INGESTION', 'VERIFICATION').
        model_provider: The LLM provider (openai, anthropic, etc).
        model_name: The specific model used.
        prompt: The full list of messages sent to the model.
        response: The structured or raw response received.
        metadata: Additional context like ticker, source_id, etc.
    """
    try:
        # Prepare the payload
        # We handle Pydantic models by converting them to dict
        processed_response = response
        if hasattr(response, "model_dump"):
            processed_response = response.model_dump()
        elif hasattr(response, "dict"):
            processed_response = response.dict()

        # Ensure prompt is serializable
        def sterilize_data(obj):
            if isinstance(obj, dict):
                return {k: sterilize_data(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [sterilize_data(i) for i in obj]
            elif hasattr(obj, "model_dump"):
                return sterilize_data(obj.model_dump())
            elif hasattr(obj, "dict"):
                return sterilize_data(obj.dict())
            elif hasattr(obj, "__dict__"):
                # Handle generic objects by taking their dict representation
                return {k: sterilize_data(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
            elif hasattr(obj, "role") and hasattr(obj, "parts"):
                # Handle Google GenAI Content objects explicitly if needed, but the logic above should cover most
                return str(obj)
            elif isinstance(obj, (str, int, float, bool, type(None))):
                return obj
            else:
                return str(obj)

        serializable_prompt = sterilize_data(prompt)

        payload = {
            "task_type": task_type,
            "model_provider": model_provider,
            "model_name": model_name,
            "prompt": serializable_prompt,
            "response": processed_response,
            "metadata": metadata or {},
            "created_at": datetime.now(UTC).isoformat()
        }

        # Initialize Supabase inside the call to avoid stale connections 
        # or use a singleton if appropriate. For simplicity, we get a new client.
        client = get_supabase_client()
        
        # We don't want to block the main pipeline indefinitely, 
        # but we want to ensure the log is attempted.
        client.table("llm_reasoning_logs").insert(payload).execute()
        
    except Exception as e:
        # We log the error but don't re-raise to avoid crashing the main pipeline
        pipeline_logger.error(f"Failed to log reasoning trace for {task_type}: {e}")
