from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from core.cleanup import run_cleanup


@pytest.mark.asyncio
async def test_run_cleanup_calls_correct_deletes():
    """Verify that run_cleanup calls the expected delete operations on Supabase."""

    # Setup mock client
    mock_client = MagicMock()

    # We need to mock the chain: client.table().delete().lt().execute()
    # and client.table().delete().in_().lt().execute()

    mock_table = MagicMock()
    mock_delete = MagicMock()
    mock_lt = MagicMock()
    mock_in = MagicMock()
    MagicMock()

    mock_client.table.return_value = mock_table
    mock_table.delete.return_value = mock_delete
    mock_delete.lt.return_value = mock_lt
    mock_delete.in_.return_value = mock_in
    mock_delete.eq.return_value = mock_delete
    mock_in.lt.return_value = mock_lt
    mock_lt.execute.return_value = MagicMock()  # Final result doesn't matter for this test

    with patch("core.cleanup.get_supabase_client", return_value=mock_client):
        await run_cleanup()

    # Verify ingestion_logs cleanup
    mock_client.table.assert_any_call("ingestion_logs")
    # Verify system_audits cleanup
    mock_client.table.assert_any_call("system_audits")
    # Verify market_feeling cleanup
    mock_client.table.assert_any_call("market_feeling")
    # Verify memories cleanup
    mock_client.table.assert_any_call("memories")

    # Check that delete was called 4 times
    assert mock_table.delete.call_count == 4

    # Verify that the lt calls were using ISO strings and not raw SQL strings
    for call in mock_lt.call_args_list:
        if call.args:
            assert isinstance(call.args[1], str)
            assert call.args[1] != 'now() - interval "48 hours"'
            assert call.args[1] != 'now() - interval "30 days"'
            assert call.args[1] != 'now() - interval "180 days"'
            # It should be possible to parse it as an ISO string
            try:
                datetime.fromisoformat(call.args[1])
            except ValueError:
                pytest.fail(f"Could not parse string {call.args[1]} as ISO format.")


@pytest.mark.asyncio
async def test_run_cleanup_exception_handling():
    """Verify that run_cleanup logs exceptions via logger.exception and propagates them."""
    mock_client = MagicMock()
    mock_client.table.side_effect = Exception("Supabase DB Connection Failed")

    with (
        patch("core.cleanup.get_supabase_client", return_value=mock_client),
        patch("core.cleanup.logger") as mock_logger,
    ):
        with pytest.raises(Exception, match="Supabase DB Connection Failed"):
            await run_cleanup()

        # Check that the exception traceback was logged exactly once
        mock_logger.exception.assert_called_once_with("Database cleanup failed")

