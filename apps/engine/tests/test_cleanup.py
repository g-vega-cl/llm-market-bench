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
    mock_in.lt.return_value = mock_lt
    mock_lt.execute.return_value = MagicMock() # Final result doesn't matter for this test
    
    with patch("core.cleanup.get_supabase_client", return_value=mock_client):
        await run_cleanup()
    
    # Verify ingestion_logs cleanup
    mock_client.table.assert_any_call("ingestion_logs")
    # Verify system_audits cleanup
    mock_client.table.assert_any_call("system_audits")
    # Verify market_feeling cleanup
    mock_client.table.assert_any_call("market_feeling")
    
    # Check that delete was called at least 3 times
    assert mock_table.delete.call_count == 3
