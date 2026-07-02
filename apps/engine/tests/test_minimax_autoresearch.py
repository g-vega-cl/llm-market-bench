import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

# Ensure engine path is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from core.llm.prompt_factory import PromptFactory


@pytest.mark.asyncio
async def test_minimax_autoresearch_active_prompt_loading():
    """Verify that PromptFactory loads the active database prompt for MiniMax-M3

    when it is configured in the auto-research experiment group. Also checks
    that the MiniMax-specific tool nudge is prepended.
    """
    mock_active_prompt = "=== MUTABLE ACTIVE PROMPT ===\nRule 1: Custom auto-research rule."

    with (
        patch(
            "autoresearch.prompt_store.get_active_prompt",
            new_callable=AsyncMock,
            return_value=mock_active_prompt,
        ) as mock_get_prompt,
        patch(
            "attribution.service.get_active_ledger_xml",
            new_callable=AsyncMock,
            return_value="",
        ),
        patch("core.db.get_async_supabase_client", new_callable=AsyncMock),
    ):
        messages = await PromptFactory.build_analysis_messages(
            provider="minimax",
            owner_id="MiniMax-M3",
            news_content="Apple reports earnings.",
            portfolio_context="Cash: $10,000",
            current_day_info="Monday",
            calendar_knowledge="",
            macro_context="",
            context="No context",
            min_trade_value=1000.0,
            held_tickers_list=[],
        )

        # Get system prompt from the built messages
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")

        # Assert MiniMax specific nudge is present
        assert "=== SYSTEM PROTOCOL: MANDATORY TOOL USE FOR MINIMAX ===" in system_msg

        # Assert the active prompt content from DB is present
        assert "Rule 1: Custom auto-research rule." in system_msg
        assert mock_get_prompt.called
