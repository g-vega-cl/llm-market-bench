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

from core.config import AUTORESEARCH_MODEL, AUTORESEARCH_TRACK_MODELS
from core.llm.clients import (
    get_anthropic_client,
    get_deepseek_client,
    get_gemini_client,
    get_minimax_client,
    get_openai_client,
)

logger = logging.getLogger("engine")

_PROGRAM_PATH = Path(__file__).parent / "program.md"


def _load_research_program() -> str:
    """Read program.md lazily so import doesn't fail if the file is missing."""
    return _PROGRAM_PATH.read_text()


def _get_client_and_provider_for_model(model_name: str):
    """Resolve instructor client factory and provider name for a given model."""
    name_lower = model_name.lower()
    if "minimax" in name_lower:
        return get_minimax_client(), "minimax"
    elif "deepseek" in name_lower:
        return get_deepseek_client(), "deepseek"
    elif "gpt" in name_lower or "openai" in name_lower:
        return get_openai_client(), "openai"
    elif "claude" in name_lower or "anthropic" in name_lower:
        return get_anthropic_client(), "anthropic"
    elif "gemini" in name_lower:
        return get_gemini_client(), "gemini"
    else:
        return get_deepseek_client(), "deepseek"


class PromptResearchResult(BaseModel):
    new_prompt_text: str = Field(..., description="The complete modified prompt text")
    selected_tools: list[str] = Field(
        ...,
        description=(
            "List of allowed tool names for the trading agent, chosen from: "
            "'get_stock_quote', 'get_price_history', 'get_position_pnl', 'get_volatility_metrics', "
            "'get_sector_alternatives', 'search_related_tickers', 'run_stock_screener', "
            "'find_uncorrelated_assets', 'get_key_metrics', 'get_market_health_barometer', "
            "'get_earnings_history', 'search_prediction_markets', 'get_prediction_market_odds', "
            "'audit_financial_valuation', 'fetch_newsletter_content', 'search_past_memories', "
            "'get_thematic_flows', 'add_thematic_flow', "
            "'get_portfolio_ledger', 'get_todays_news_menu', 'get_market_feeling', "
            "'get_global_macro_context', 'get_volatility_index_details', 'get_verifier_rejections'. "
            "Do NOT include execution tools ('calculate_buy_quantity', 'calculate_sell_quantity') "
            "as they are automatically force-injected by the system."
        ),
    )
    selected_prompt_blocks: list[str] = Field(
        default_factory=list,
        description=(
            "List of modular prompt block IDs to enable for the trading agent, chosen from: "
            "'let_winners_run', 'cut_losers_fast', 'catalyst_expiry_timer', 'five_whys_causal', 'mece_risk_partition'."
        ),
    )
    change_description: str = Field(..., description="One sentence explaining what was changed and why")
    experiment_type: str = Field(..., description="'incremental' or 'radical'")
    research_reasoning: str = Field(..., description="Detailed reasoning for this change")
    confidence: int = Field(ge=0, le=100, description="Confidence in this change (0-100)")


async def run_research(
    report: str,
    current_prompt: str | None = None,
    cold_start: bool = False,
    baseline_prompt: str | None = None,
    track_id: str = "track_default",
    model_name: str | None = None,
) -> PromptResearchResult | None:
    """Run the auto-research evaluation and return proposed prompt changes.

    Args:
        report: The formatted report with all metrics, samples, and context.
        current_prompt: Optional current system prompt text.
        cold_start: If True, instructs the meta-researcher to ignore prior prompt history and build from scratch.
        baseline_prompt: Optional baseline mutable strategy text to ensure new_prompt_text is not a duplicate.
        track_id: The research track ID being evaluated.
        model_name: Optional explicit model override for the meta-researcher.

    Returns:
        A PromptResearchResult with the new prompt and reasoning, or None on failure.
    """
    if model_name is None:
        model_name = AUTORESEARCH_TRACK_MODELS.get(track_id, AUTORESEARCH_MODEL)

    client, provider = _get_client_and_provider_for_model(model_name)

    # Perform DB search pre-query to enrich autoresearcher context with empirical trade postmortems
    try:
        from autoresearch.tools import query_trade_postmortems

        db_context = await query_trade_postmortems(track_id=track_id, limit=5)
        if db_context:
            report += f"\n\n{db_context}"
    except Exception as e:
        logger.warning("Failed to pre-query DB trade postmortems for autoresearcher: %s", e)

    system_program = _load_research_program()
    user_content = report

    if cold_start:
        system_program += (
            "\n\n=== COLD START RESET ===\n"
            "This cycle is a COLD START RESET to avoid local optima. "
            "Ignore the previous system prompt strategy. "
            "Generate a novel, high-conviction trading strategy prompt from scratch."
        )

    try:
        messages = [
            {"role": "system", "content": system_program},
            {"role": "user", "content": user_content},
        ]

        create_args = {
            "model": model_name,
            "response_model": PromptResearchResult,
            "messages": messages,
            "max_tokens": 64000,
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
                    # Check if proposed prompt is identical to baseline
                    if baseline_prompt and wrapper.new_prompt_text.strip() == baseline_prompt.strip():
                        attempt_num = attempt + 1
                        logger.warning(
                            "[%s/%s] Auto-research proposed prompt identical to baseline (attempt %d/3). Retrying...",
                            provider,
                            model_name,
                            attempt_num,
                        )
                        instructor_messages.append(
                            {
                                "role": "user",
                                "content": (
                                    "Your proposed new_prompt_text is 100% identical to the Baseline Prompt. "
                                    "You MUST propose a NEW modification or refined strategy built on top of the baseline, "
                                    "or a RADICAL alternative. Do NOT return identical text to the baseline."
                                ),
                            }
                        )
                        create_args["messages"] = copy.deepcopy(instructor_messages)
                        wrapper = None
                        continue

                    break

                attempt_num = attempt + 1
                logger.warning(
                    "[%s/%s] Auto-research empty response (attempt %d/3). Retrying...",
                    provider,
                    model_name,
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
                        model_name,
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
                        model_name,
                        str(e),
                    )
                    raise

        if wrapper is None:
            logger.error(
                "[%s/%s] All auto-research attempts failed. Last error: %s",
                provider,
                model_name,
                last_error or "empty response or duplicate baseline",
            )
            return None

        return wrapper

    except Exception as e:
        logger.error("Auto-research failed: %s", e)
        return None
