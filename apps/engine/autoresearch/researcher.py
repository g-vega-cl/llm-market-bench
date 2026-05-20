"""Auto-research LLM interface.

Calls DeepSeek v4 Pro (configurable via AUTORESEARCH_MODEL) to evaluate
trading performance and propose prompt improvements. Uses Instructor
for structured output, following the same pattern as verification.py.
"""

import asyncio
import copy
import logging
from pathlib import Path

from pydantic import BaseModel, Field

from core.config import AUTORESEARCH_MODEL
from core.llm import get_deepseek_client

logger = logging.getLogger("engine")

_PROGRAM_PATH = Path(__file__).parent / "program.md"


def _load_research_program() -> str:
    """Read program.md lazily so import doesn't fail if the file is missing."""
    return _PROGRAM_PATH.read_text()


class PromptResearchResult(BaseModel):
    new_prompt_text: str = Field(..., description="The complete modified prompt text")
    change_description: str = Field(..., description="One sentence explaining what was changed and why")
    experiment_type: str = Field(..., description="'incremental' or 'radical'")
    research_reasoning: str = Field(..., description="Detailed reasoning for this change")
    confidence: int = Field(ge=0, le=100, description="Confidence in this change (0-100)")


async def run_research(report: str) -> PromptResearchResult | None:
    """Run the auto-research evaluation and return proposed prompt changes.

    Args:
        report: The formatted report with all metrics, samples, and context.

    Returns:
        A PromptResearchResult with the new prompt and reasoning, or None on failure.
    """
    client = get_deepseek_client()
    provider = "deepseek"

    try:
        messages = [
            {"role": "system", "content": _load_research_program()},
            {"role": "user", "content": report},
        ]

        create_args = {
            "model": AUTORESEARCH_MODEL,
            "response_model": PromptResearchResult,
            "messages": messages,
            "max_retries": 2,
        }

        wrapper = None
        last_error = None
        instructor_messages = list(messages)

        for attempt in range(3):
            try:
                resp_awaitable = client.chat.completions.create(**create_args)
                if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
                    wrapper = await resp_awaitable
                else:
                    wrapper = resp_awaitable

                if wrapper is not None:
                    break

                attempt_num = attempt + 1
                logger.warning(
                    "[%s/%s] Auto-research empty response (attempt %d/3). Retrying...",
                    provider,
                    AUTORESEARCH_MODEL,
                    attempt_num,
                )
                instructor_messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your response was empty. You MUST output a valid JSON object with "
                            "new_prompt_text, change_description, experiment_type, research_reasoning, "
                            "and confidence fields. No other text."
                        ),
                    }
                )
                create_args["messages"] = copy.deepcopy(instructor_messages)
            except Exception as e:
                last_error = e
                attempt_num = attempt + 1
                error_str = str(e).lower()
                if "validation error" in error_str or "input should be a valid" in error_str:
                    logger.warning(
                        "[%s/%s] Auto-research validation error (attempt %d/3): %s",
                        provider,
                        AUTORESEARCH_MODEL,
                        attempt_num,
                        str(e)[:200],
                    )
                    instructor_messages.append(
                        {
                            "role": "user",
                            "content": (
                                "Your response must be valid JSON matching the schema exactly. "
                                "Ensure new_prompt_text is the complete prompt, experiment_type is "
                                "'incremental' or 'radical', and confidence is 0-100."
                            ),
                        }
                    )
                    create_args["messages"] = copy.deepcopy(instructor_messages)
                else:
                    logger.error(
                        "[%s/%s] Auto-research non-retryable error: %s",
                        provider,
                        AUTORESEARCH_MODEL,
                        str(e),
                    )
                    raise

        if wrapper is None:
            logger.error(
                "[%s/%s] All auto-research attempts failed. Last error: %s",
                provider,
                AUTORESEARCH_MODEL,
                last_error or "empty response",
            )
            return None

        return wrapper

    except Exception as e:
        logger.error("Auto-research failed: %s", e)
        return None
