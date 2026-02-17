"""Logging utility for LLM reasoning traces."""

import logging
from typing import Any, List, Optional
from datetime import datetime

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
        serializable_prompt = []
        for m in prompt:
            if isinstance(m, dict):
                serializable_prompt.append(m)
            elif hasattr(m, "role") and hasattr(m, "parts"):
                # Handle Google GenAI Content objects
                parts = []
                for part in m.parts:
                    if hasattr(part, "text") and part.text:
                        parts.append({"text": part.text})
                    elif hasattr(part, "function_call") and part.function_call:
                        parts.append({
                            "function_call": {
                                "name": part.function_call.name,
                                "args": part.function_call.args
                            }
                        })
                    elif hasattr(part, "function_response") and part.function_response:
                        parts.append({
                            "function_response": {
                                "name": part.function_response.name,
                                "response": part.function_response.response
                            }
                        })
                    elif hasattr(part, "thought") and part.thought:
                        parts.append({"thought": part.thought})
                serializable_prompt.append({"role": m.role, "parts": parts})
            else:
                # Fallback for other complex objects
                serializable_prompt.append({"role": getattr(m, "role", "unknown"), "content": str(m)})

        payload = {
            "task_type": task_type,
            "model_provider": model_provider,
            "model_name": model_name,
            "prompt": serializable_prompt,
            "response": processed_response,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat()
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
