"""Tests for portfolio reset state script."""

from unittest.mock import MagicMock, patch

import pytest

from scripts.reset_state import reset_database


@pytest.mark.asyncio
async def test_reset_database_llm_only():
    """Verify that reset_database(llm_only=True) only resets non-system LLM portfolios to $10k cash/BP."""
    mock_supabase = MagicMock()

    # Mock portfolios
    mock_portfolios = [
        {"id": "uuid-llm-1", "owner_id": "claude-haiku-5-5"},
        {"id": "uuid-llm-2", "owner_id": "gpt-5.6-luna"},
        {"id": "uuid-sys-1", "owner_id": "sys-sector-ls-consensus"},
    ]
    mock_supabase.table.return_value.select.return_value.execute.return_value = MagicMock(data=mock_portfolios)

    with patch("scripts.reset_state.get_supabase_client", return_value=mock_supabase):
        await reset_database(llm_only=True)

        # Check table calls
        update_calls = mock_supabase.table("portfolios").update.call_args_list
        # Should only be called for 2 LLM portfolios, not sys-sector-ls-consensus
        assert len(update_calls) == 2

        payload = update_calls[0][0][0]
        assert payload["cash_balance"] == 10000.00
        assert payload["buying_power"] == 10000.00  # Cash-only! Not 40k!
        assert payload["total_equity"] == 10000.00
        assert payload["maintenance_margin"] == 0.0
