"""Tests for Trend & Concept Momentum Analysis."""

from unittest.mock import MagicMock, patch

import pytest

from analysis.momentum import analyze_momentum, calculate_velocity, update_concept_metrics


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
    # First call (recent 7 days): 14 mentions
    recent_res = MagicMock()
    recent_res.data = [{"id": i} for i in range(1, 15)]
    
    # Second call (total 37 days): 44 mentions (implies 30 in baseline)
    baseline_res = MagicMock()
    baseline_res.data = [{"id": i} for i in range(1, 45)]
    
    # Set side effect for the two sequential RPC calls
    mock_supabase.rpc().execute.side_effect = [recent_res, baseline_res]
    
    velocity = calculate_velocity(mock_supabase, [0.1]*768)
    
    # recent_count = 14 -> avg_recent = 2.0, intensity = ln(14+1)+1 approx 3.708
    # total_37d = 44
    # baseline_count = 44 - 14 = 30
    # avg_baseline = 30 / 30 = 1.0
    # velocity (momentum) = 3.708 * 2.0 = 7.416
    assert abs(velocity - 7.416) < 0.001

def test_update_concept_metrics_new_record(mock_supabase):
    """Test updating metrics for a brand new concept."""
    # RPC 1 (match_concepts): No match
    # RPC 2 (90d mentions): 0
    mock_supabase.rpc().execute.return_value.data = []
    
    update_concept_metrics(mock_supabase, "AI Boom", [0.1]*768, 3.5)
    
    # Payload check
    mock_supabase.table().insert.assert_called_once()
    payload = mock_supabase.table().insert.call_args[0][0]
    assert payload["concept_name"] == "AI Boom"
    assert payload["velocity_score"] == 3.5

def test_update_concept_metrics_semantic_merge(mock_supabase):
    """Test updating metrics with a semantic match (merging)."""
    # RPC 1 (match_concepts): Match
    match_res = MagicMock()
    match_res.data = [{"id": "uuid-999", "concept_name": "AI Surge", "mention_count": 5, "similarity": 0.95}]
    
    # RPC 2 (90d mentions): 10
    history_res = MagicMock()
    history_res.data = [{"id": i} for i in range(10)]
    
    mock_supabase.rpc.side_effect = [
        MagicMock(execute=MagicMock(return_value=match_res)),
        MagicMock(execute=MagicMock(return_value=history_res))
    ]
    
    update_concept_metrics(mock_supabase, "AI Boom", [0.1]*768, 4.0)
    
    # Check update call on the table mock
    mock_supabase.table.return_value.update.assert_called_once()
    mock_supabase.table.return_value.update.return_value.eq.assert_called_once_with("id", "uuid-999")
    
    payload = mock_supabase.table.return_value.update.call_args[0][0]
    assert payload["mention_count"] == 6
    assert payload["velocity_score"] == 4.0

@pytest.mark.asyncio
async def test_analyze_momentum(mock_supabase):
    """Test the high-level analyze_momentum orchestrator."""
    consensus_events = [
        {"event_name": "Event A", "impact": "BULLISH"}
    ]
    
    mock_embeddings = [[0.1]*768]
    
    # Reset mock after setup to get clean call count
    mock_supabase.rpc.reset_mock()
    
    # Configure RPC to return empty data for all calls
    res = MagicMock()
    res.data = []
    mock_supabase.rpc.return_value.execute.return_value = res
    
    with patch("analysis.momentum.get_embeddings_batch", return_value=mock_embeddings):
        await analyze_momentum(mock_supabase, consensus_events)
        # 1 concept * (2 velocity calls + 2 update calls) = 4 RPC calls total
        # Velocity calls: 1 for recent 7d, 1 for baseline 37d
        # Update calls: 1 for match_concepts, 1 for 90d mentions
        assert mock_supabase.rpc.call_count == 4
