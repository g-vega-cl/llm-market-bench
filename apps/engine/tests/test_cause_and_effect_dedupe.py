
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
from datetime import datetime, timezone, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

# Mocking the imports before they happen in cause_and_effect_analysis
with patch("apps.engine.core.db.get_supabase_client") as mock_db, \
     patch("apps.engine.core.llm.get_gemini_client") as mock_gemini, \
     patch("apps.engine.execution.market_data.MarketDataManager") as mock_mdm:
    
    from apps.engine.analysis.cause_and_effect_analysis import perform_cause_and_effect_analysis

@pytest.mark.asyncio
async def test_cause_and_effect_semantic_dedupe():
    """Verify that semantically similar events are skipped if already analyzed."""
    
    mock_sb = MagicMock()
    mock_gemini_client = MagicMock()
    
    # 1. Setup mock events
    # Event A (Already has analysis)
    # Event B (Very similar to A, should be skipped)
    event_a = {
        "id": "uuid-a",
        "content": "A liquidity crisis in private credit is unfolding.",
        "created_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        "metadata": {}
    }
    event_b = {
        "id": "uuid-b",
        "content": "Private credit liquidity is tightening significantly.",
        "created_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        "metadata": {}
    }
    
    # Mock supabase response for events
    mock_sb.table.return_value.select.return_value.filter.return_value.filter.return_value.execute.return_value.data = [event_a, event_b]
    
    # Mock exact check for event_a (exists) and event_b (not exists)
    def mock_filter(col, op, val):
        mock_exec = MagicMock()
        if col == "event_id" and val == "uuid-a":
            mock_exec.execute.return_value.data = [{"id": "ce-a"}]
        else:
            mock_exec.execute.return_value.data = []
        return mock_exec

    mock_sb.table.return_value.select.return_value.filter.side_effect = mock_filter

    with patch("apps.engine.analysis.cause_and_effect_analysis.get_supabase_client", return_value=mock_sb), \
         patch("apps.engine.analysis.cause_and_effect_analysis.get_gemini_client", return_value=mock_gemini_client), \
         patch("apps.engine.analysis.cause_and_effect_analysis.MarketDataManager") as mock_mdm_cls, \
         patch("apps.engine.analysis.cause_and_effect_analysis.find_similar_memory") as mock_find:
        
        # Mock MarketDataManager
        mock_mdm_instance = AsyncMock()
        mock_mdm_cls.return_value = mock_mdm_instance
        mock_mdm_instance.get_history.return_value = [{"price": 100, "fetched_at": "now"}, {"price": 90, "fetched_at": "then"}]
        
        # Scenario: Event B is semantically similar to Event A
        # When processing Event B, find_similar_memory returns uuid-a
        def mock_find_sim(content, threshold, hours):
            if threshold == 0.85 and "Private credit liquidity" in content:
                return "uuid-a"
            return None
        
        mock_find.side_effect = mock_find_sim
        
        # Mock the second check (if uuid-a has analysis)
        # We need mock_sb.table("cause_and_effect").select("id").filter("event_id", "eq", "uuid-a") to return data
        # Which is already handled by our side_effect above.
        
        # Final Step: Run analysis
        await perform_cause_and_effect_analysis()
        
        # VERIFICATION:
        # 1. Event A should be skipped because of exact ID check (existing.data).
        # 2. Event B should be skipped because it's semantically similar to A, and A has analysis.
        
        # Gemini create should NEVER be called in this scenario
        assert mock_gemini_client.chat.completions.create.call_count == 0
        print("\nTest Passed: Semantic deduplication skipped redundant analysis.")

@pytest.mark.asyncio
async def test_cause_and_effect_expanded_tickers():
    """Verify that LLM ticker suggestion trigger expanded ticker extraction."""
    
    mock_sb = MagicMock()
    mock_gemini_client = MagicMock()
    
    # Event with "Private Credit" theme
    event = {
        "id": "uuid-c",
        "content": "A major shift is happening in private credit markets.",
        "created_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        "metadata": {}
    }
    
    mock_sb.table.return_value.select.return_value.filter.return_value.filter.return_value.execute.return_value.data = [event]
    
    # Mock exact check (does not exist)
    mock_sb.table.return_value.select.return_value.filter.return_value.execute.return_value.data = []

    with patch("apps.engine.analysis.cause_and_effect_analysis.get_supabase_client", return_value=mock_sb), \
         patch("apps.engine.analysis.cause_and_effect_analysis.get_gemini_client", return_value=mock_gemini_client), \
         patch("apps.engine.analysis.cause_and_effect_analysis.MarketDataManager") as mock_mdm_cls, \
         patch("apps.engine.analysis.cause_and_effect_analysis.find_similar_memory", return_value=None), \
         patch("apps.engine.analysis.cause_and_effect_analysis.extract_related_tickers") as mock_extract:
        
        mock_mdm_instance = AsyncMock()
        mock_mdm_cls.return_value = mock_mdm_instance
        mock_mdm_instance.get_history.return_value = [{"price": 100, "fetched_at": "now"}, {"price": 90, "fetched_at": "then"}]
        
        # Mock LLM suggestions
        mock_extract.return_value = ["OWL", "JPM"]
        
        # Mock Gemini response for the final analysis
        mock_resp = MagicMock()
        mock_resp.analysis = "Detailed analysis"
        mock_resp.market_outcome = "Outcome"
        mock_resp.confidence = 90
        mock_resp.tags = ["tag"]
        mock_gemini_client.chat.completions.create.return_value = mock_resp
        
        await perform_cause_and_effect_analysis()
        
        # VERIFICATION:
        # Check that get_history was called with expected tickers
        called_tickers = [call.args[0] for call in mock_mdm_instance.get_history.call_args_list]
        
        assert "OWL" in called_tickers
        assert "JPM" in called_tickers
        assert "SPY" in called_tickers
        assert "QQQ" in called_tickers
        
        print("\nTest Passed: LLM-based ticker extraction correctly identified private credit tickers.")

if __name__ == "__main__":
    asyncio.run(test_cause_and_effect_semantic_dedupe())
