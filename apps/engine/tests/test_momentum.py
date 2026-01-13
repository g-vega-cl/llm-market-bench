"""Tests for Trend & Concept Momentum Analysis."""

import pytest
from unittest.mock import MagicMock, patch
from analysis.momentum import calculate_velocity, update_concept_metrics, analyze_momentum

@pytest.fixture
def mock_supabase():
    """Fixture for a mocked Supabase client."""
    client = MagicMock()
    
    # Mock chain for select().eq().execute()
    table_mock = MagicMock()
    client.table.return_value = table_mock
    
    select_mock = MagicMock()
    table_mock.select.return_value = select_mock
    
    eq_mock = MagicMock()
    select_mock.eq.return_value = eq_mock
    
    execute_select_mock = MagicMock()
    eq_mock.execute.return_value = execute_select_mock
    
    # Mock chain for update().eq().execute()
    update_mock = MagicMock()
    table_mock.update.return_value = update_mock
    
    eq_update_mock = MagicMock()
    update_mock.eq.return_value = eq_update_mock
    
    execute_update_mock = MagicMock()
    eq_update_mock.execute.return_value = execute_update_mock
    
    # Mock chain for insert().execute()
    insert_mock = MagicMock()
    table_mock.insert.return_value = insert_mock
    
    execute_insert_mock = MagicMock()
    insert_mock.execute.return_value = execute_insert_mock
    
    # Mock RPC
    rpc_chain_mock = MagicMock()
    client.rpc.return_value = rpc_chain_mock
    
    execute_rpc_mock = MagicMock()
    rpc_chain_mock.execute.return_value = execute_rpc_mock
    
    return client

def test_calculate_velocity_no_mentions(mock_supabase):
    """Test velocity calculation when no mentions are found."""
    # Mock RPC to return no data for both calls
    mock_supabase.rpc().execute.return_value.data = []
    
    velocity = calculate_velocity(mock_supabase, [0.1]*768)
    
    # recent_count = 0
    # avg_baseline = 0.1 (floor)
    # velocity = 0 / 0.1 = 0.0
    assert velocity == 0.0

def test_calculate_velocity_with_mentions(mock_supabase):
    """Test velocity calculation with simulated mentions."""
    # First call (recent): 2 mentions
    recent_res = MagicMock()
    recent_res.data = [{"id": 1}, {"id": 2}]
    
    # Second call (total 8d): 9 mentions (implies 7 in baseline)
    baseline_res = MagicMock()
    baseline_res.data = [{"id": i} for i in range(1, 10)]
    
    # Set side effect for the two sequential RPC calls
    mock_supabase.rpc().execute.side_effect = [recent_res, baseline_res]
    
    velocity = calculate_velocity(mock_supabase, [0.1]*768)
    
    # recent_count = 2
    # total_8d = 9
    # baseline_count = 9 - 2 = 7
    # avg_baseline = 7 / 7 = 1.0
    # velocity = 2 / 1.0 = 2.0
    assert velocity == 2.0

def test_update_concept_metrics_new_record(mock_supabase):
    """Test updating metrics for a brand new concept."""
    # Mock select to return no existing record
    mock_supabase.table().select().eq().execute.return_value.data = []
    
    update_concept_metrics(mock_supabase, "AI Boom", [0.1]*768, 3.5)
    
    # Should call insert
    mock_supabase.table().insert.assert_called_once()
    args, _ = mock_supabase.table().insert.call_args
    payload = args[0]
    assert payload["concept_name"] == "AI Boom"
    assert payload["velocity_score"] == 3.5
    assert payload["mention_count"] == 1

def test_update_concept_metrics_existing_record(mock_supabase):
    """Test updating metrics for an existing concept."""
    # Mock select to return existing record
    mock_supabase.table().select().eq().execute.return_value.data = [
        {"id": "uuid-123", "mention_count": 10}
    ]
    
    update_concept_metrics(mock_supabase, "AI Boom", [0.1]*768, 5.0)
    
    # Should call update instead of insert
    mock_supabase.table().update.assert_called_once()
    args, _ = mock_supabase.table().update.call_args
    payload = args[0]
    assert payload["mention_count"] == 11
    assert payload["velocity_score"] == 5.0
    
    # Verify it filtered by the correct ID
    mock_supabase.table().update().eq.assert_called_once_with("id", "uuid-123")

@pytest.mark.asyncio
async def test_analyze_momentum(mock_supabase):
    """Test the high-level analyze_momentum orchestrator."""
    consensus_events = [
        {"event_name": "Event A", "impact": "BULLISH"},
        {"event_name": "Event B", "impact": "BEARISH"}
    ]
    
    mock_embeddings = [[0.1]*768, [0.2]*768]
    
    with patch("analysis.momentum.get_embeddings_batch", return_value=mock_embeddings):
        with patch("analysis.momentum.calculate_velocity", return_value=1.5) as mock_calc:
            with patch("analysis.momentum.update_concept_metrics") as mock_update:
                await analyze_momentum(mock_supabase, consensus_events)
                
                assert mock_calc.call_count == 2
                assert mock_update.call_count == 2
                
                # Check first call
                first_call_args = mock_update.call_args_list[0][0]
                assert first_call_args[1] == "Event A"
                assert first_call_args[2] == mock_embeddings[0]
                assert first_call_args[3] == 1.5
