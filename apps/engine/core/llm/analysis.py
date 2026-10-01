"""Core LLM analysis logic and orchestrator for trading decisions."""

import logging
from typing import Any

from core.llm import clients as clients
from core.llm.analysis_pipeline import prompt_assembly, response_parsing, validation
from core.llm.analysis_pipeline.prompt_assembly import (
    _MAJOR_INDICES as _MAJOR_INDICES,
)
from core.llm.analysis_pipeline.prompt_assembly import (
    _TICKER_FALSE_POSITIVES as _TICKER_FALSE_POSITIVES,
)
from core.llm.analysis_pipeline.prompt_assembly import (
    extract_held_tickers as _extract_held_tickers,
)
from core.llm.analysis_pipeline.prompt_assembly import (
    extract_tickers_from_chunks as _extract_tickers_from_chunks,
)
from core.llm.analysis_pipeline.prompt_assembly import (
    flatten_messages_for_minimax as _flatten_messages_for_minimax,
)
from core.llm.analysis_pipeline.prompt_assembly import (
    safe_deepcopy as safe_deepcopy,
)
from core.llm.analysis_pipeline.response_parsing import (
    repair_json_string as _repair_json_string,
)
from core.llm.analysis_pipeline.response_parsing import (
    try_parse_decisions_response as _try_parse_decisions_response,
)
from core.llm.analysis_pipeline.response_parsing import (
    try_parse_response as _try_parse_response,
)
from core.llm.analysis_pipeline.validation import (
    get_history_tool_calls_diagnostic as _get_history_tool_calls_diagnostic,
)
from core.llm.analysis_pipeline.validation import (
    scan_history_for_tools as _scan_history_for_tools,
)
from core.llm.logger import log_reasoning_trace as log_reasoning_trace
from core.llm.prompt_factory import PromptFactory as PromptFactory
from core.models import DecisionsResponse

__all__ = [
    "analyze_with_provider",
    "safe_deepcopy",
    "_repair_json_string",
    "_try_parse_response",
    "_try_parse_decisions_response",
    "_scan_history_for_tools",
    "_get_history_tool_calls_diagnostic",
    "_extract_tickers_from_chunks",
    "_extract_held_tickers",
    "_flatten_messages_for_minimax",
    "_TICKER_FALSE_POSITIVES",
    "_MAJOR_INDICES",
    "clients",
    "PromptFactory",
    "log_reasoning_trace",
]

logger = logging.getLogger("engine")


async def _execute_provider_tool_loop(
    raw_client: Any,
    provider: str,
    model_name: str,
    messages: list,
    override_tools: list | None,
    enable_web_search: bool,
) -> None:
    """Delegate tool execution loop to provider-specific handlers."""
    if provider == "openai":
        from .handlers import openai

        await openai.run_tool_loop(
            raw_client,
            model_name,
            messages,
            provider,
            override_tools=override_tools,
            enable_web_search=enable_web_search,
        )
    elif provider == "deepseek":
        from .handlers import deepseek

        await deepseek.run_tool_loop(
            raw_client,
            model_name,
            messages,
            provider,
            override_tools=override_tools,
            enable_web_search=enable_web_search,
        )
    elif provider == "anthropic":
        from .handlers import anthropic

        await anthropic.run_tool_loop(
            raw_client,
            model_name,
            messages,
            override_tools=override_tools,
            enable_web_search=enable_web_search,
        )
    elif provider == "gemini":
        from .handlers import gemini

        await gemini.run_tool_loop(
            raw_client,
            model_name,
            messages,
            override_tools=override_tools,
            enable_google_search=enable_web_search,
        )
    elif provider == "minimax":
        from .handlers import anthropic

        await anthropic.run_tool_loop(
            raw_client,
            model_name,
            messages,
            override_tools=override_tools,
            enable_web_search=False,
        )


async def analyze_with_provider(
    provider: str,
    model_name: str,
    chunks: list[dict],
    context: str = "",
    portfolio_context: str = "",
    current_day_info: str = "No date context available.",
    calendar_knowledge: str = "",
    macro_context: str = "",
    summaries: dict | None = None,
    market_data_block: str = "",
    response_model: Any = None,
    prompt_type: str = "analysis",
    consensus_context: str = "",
) -> Any:
    """Analyze a batch of newsletter chunks using the specified provider."""
    if response_model is None:
        response_model = DecisionsResponse

    factory = clients.CLIENT_FACTORIES.get(provider)
    if factory is None:
        raise ValueError(f"Unknown provider: {provider}")

    client = factory()

    from core.llm import tools

    token_summaries = tools.active_news_summaries.set(summaries)
    token_chunks = tools.active_news_chunks.set(chunks)

    try:
        # 1. Resolve experiment tools and web search configuration
        override_tools, exp_web_search = await prompt_assembly.resolve_experiment_tools(model_name, prompt_type)
        enable_web_search = prompt_assembly.resolve_web_search_flag(provider, override_tools, exp_web_search)

        # 2. Assemble prompt messages
        messages = await prompt_assembly.assemble_analysis_messages(
            provider=provider,
            model_name=model_name,
            chunks=chunks,
            context=context,
            portfolio_context=portfolio_context,
            current_day_info=current_day_info,
            calendar_knowledge=calendar_knowledge,
            macro_context=macro_context,
            summaries=summaries,
            market_data_block=market_data_block,
            prompt_type=prompt_type,
            consensus_context=consensus_context,
            enable_web_search=enable_web_search,
        )

        # 3. Execute initial provider tool loop
        raw_client = client.client
        await _execute_provider_tool_loop(
            raw_client=raw_client,
            provider=provider,
            model_name=model_name,
            messages=messages,
            override_tools=override_tools,
            enable_web_search=enable_web_search,
        )

        # Preserve unflattened snapshot for verification before formatting mutations
        unflattened_messages = safe_deepcopy(messages)

        # 4. Final structured extraction using Instructor
        logger.debug("Executing final extraction for %s/%s", provider, model_name)
        extraction_messages = prompt_assembly.prepare_messages_for_provider(messages, provider, model_name)
        schema_hint = prompt_assembly.build_schema_hint(response_model)
        final_args = prompt_assembly.build_provider_extraction_args(
            provider=provider,
            model_name=model_name,
            messages=extraction_messages,
            response_model=response_model,
        )

        # Retry predicate catching tool-mode and validation errors
        def _is_retryable_error(error_str: str) -> bool:
            return (
                "validation error" in error_str
                or "input should be a valid" in error_str
                or "list_type" in error_str
                or "no tool calls" in error_str
                or "function call found" in error_str
            )

        wrapper = await response_parsing.extract_structured_response(
            client=client,
            final_args=final_args,
            provider=provider,
            model_name=model_name,
            response_model=response_model,
            schema_hint=schema_hint,
            messages=extraction_messages,
            is_retryable_error=_is_retryable_error,
        )
        final_resp = response_parsing.aggregate_response_blocks(wrapper, response_model)

        logger.debug(
            "[%s/%s] Instructor extraction complete: %d decisions, %d macro_events",
            provider,
            model_name,
            len(getattr(final_resp, "decisions", [])),
            len(getattr(final_resp, "macro_events", [])),
        )

        # 5. Tool enforcement and retry loop if mandatory quantity tools were omitted
        missing_tool_decisions = validation.detect_missing_tool_decisions(final_resp, unflattened_messages)
        if missing_tool_decisions:
            try:
                serialized_resp = final_resp.model_dump_json(indent=2)
            except Exception:
                serialized_resp = str(final_resp)
            unflattened_messages.append({"role": "assistant", "content": serialized_resp})
            unflattened_messages.append(validation.build_tool_correction_message(missing_tool_decisions))

            logger.warning(
                "[%s/%s] Missing tool calls detected for decisions: %s. Retrying tool loop once...",
                provider,
                model_name,
                [f"{d.signal} {d.ticker}" for d in missing_tool_decisions],
            )

            await _execute_provider_tool_loop(
                raw_client=raw_client,
                provider=provider,
                model_name=model_name,
                messages=unflattened_messages,
                override_tools=override_tools,
                enable_web_search=enable_web_search if provider != "minimax" else False,
            )

            retry_messages = prompt_assembly.prepare_messages_for_provider(unflattened_messages, provider, model_name)
            final_args_retry = prompt_assembly.build_provider_extraction_args(
                provider=provider,
                model_name=model_name,
                messages=retry_messages,
                response_model=response_model,
            )
            wrapper_retry = await response_parsing.extract_structured_response(
                client=client,
                final_args=final_args_retry,
                provider=provider,
                model_name=model_name,
                response_model=response_model,
                schema_hint=schema_hint,
                messages=retry_messages,
            )
            final_resp = response_parsing.aggregate_response_blocks(wrapper_retry, response_model)
            messages = unflattened_messages

            logger.info(
                "[%s/%s] Retry extraction complete: %d decisions, %d macro_events",
                provider,
                model_name,
                len(getattr(final_resp, "decisions", [])),
                len(getattr(final_resp, "macro_events", [])),
            )

        # 6. Hard tool enforcement and pre-analysis portfolio ownership validation
        validation.enforce_tool_call_history(final_resp, unflattened_messages, provider, model_name)
        validation.validate_portfolio_holdings(final_resp, portfolio_context, provider, model_name)

        # 7. Attribution trace attachment and reasoning trace logging
        validation.attach_attribution_trace(final_resp, chunks, unflattened_messages)

        await log_reasoning_trace(
            task_type="MACRO_EXTRACTION" if prompt_type == "macro" else "INGESTION",
            model_provider=provider,
            model_name=model_name,
            prompt=messages,
            response=final_resp,
            metadata={
                "chunk_ids": [c.get("source_id") for c in chunks],
                "portfolio_status": "injected" if portfolio_context else "none",
            },
        )

        return final_resp

    except Exception as e:
        logger.exception("Error analyzing batch with %s/%s: %s", provider, model_name, e)
        raise
    finally:
        tools.active_news_summaries.reset(token_summaries)
        tools.active_news_chunks.reset(token_chunks)
        await clients.close_client(client, provider)
