
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


@pytest.mark.asyncio
async def test_cause_and_effect_includes_dates_in_market_performance():
    """Verify that market_performance text includes specific date ranges for stock moves.
    
    This ensures that when the LLM generates cause & effect analysis, it knows
    the timeframe of stock movements (e.g., 'SPY +1.2% (2026-03-27 to 2026-04-10)').
    Without dates, the analysis lacks temporal context for proper causal reasoning.
    """
    
    mock_sb = MagicMock()
    mock_gemini_client = MagicMock()
    
    event = {
        "id": "uuid-date-test",
        "content": "Fed announced rate pause affecting banking sector.",
        "created_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        "metadata": {
            "scenario_analysis": "Banks should benefit from stable yields."
        }
    }
    
    mock_sb.table.return_value.select.return_value.filter.return_value.filter.return_value.execute.return_value.data = [event]
    mock_sb.table.return_value.select.return_value.filter.return_value.execute.return_value.data = []

    with patch("apps.engine.analysis.cause_and_effect_analysis.get_supabase_client", return_value=mock_sb), \
         patch("apps.engine.analysis.cause_and_effect_analysis.get_gemini_client", return_value=mock_gemini_client), \
         patch("apps.engine.analysis.cause_and_effect_analysis.MarketDataManager") as mock_mdm_cls, \
         patch("apps.engine.analysis.cause_and_effect_analysis.find_similar_memory", return_value=None), \
         patch("apps.engine.analysis.cause_and_effect_analysis.extract_related_tickers", return_value=["JPM"]):
        
        mock_mdm_instance = AsyncMock()
        mock_mdm_cls.return_value = mock_mdm_instance
        
        mock_mdm_instance.get_history.return_value = [
            {"price": 210.50, "fetched_at": "2026-04-10"},
            {"price": 205.75, "fetched_at": "2026-04-09"},
            {"price": 202.30, "fetched_at": "2026-04-08"},
            {"price": 198.00, "fetched_at": "2026-04-07"},
            {"price": 195.00, "fetched_at": "2026-04-06"},
            {"price": 192.50, "fetched_at": "2026-04-05"},
            {"price": 190.00, "fetched_at": "2026-04-04"},
            {"price": 188.00, "fetched_at": "2026-04-03"},
            {"price": 186.00, "fetched_at": "2026-04-02"},
            {"price": 184.50, "fetched_at": "2026-04-01"},
            {"price": 183.00, "fetched_at": "2026-03-31"},
            {"price": 181.50, "fetched_at": "2026-03-30"},
            {"price": 180.00, "fetched_at": "2026-03-28"},
            {"price": 179.25, "fetched_at": "2026-03-27"},
        ]
        
        mock_resp = MagicMock()
        mock_resp.analysis = "JPM rallied as banks benefited."
        mock_resp.market_outcome = "JPM up 17.4% over the period."
        mock_resp.confidence = 85
        mock_resp.tags = ["banking", "fed"]
        mock_gemini_client.chat.completions.create.return_value = mock_resp
        
        await perform_cause_and_effect_analysis()
        
        assert mock_gemini_client.chat.completions.create.call_count == 1
        
        call_args = mock_gemini_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages", call_args.args[1] if len(call_args.args) > 1 else [])
        
        user_message = None
        for msg in messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        assert user_message is not None, "No user message found in LLM call"
        
        assert "2026-03-27" in user_message, f"Start date missing from market_performance. Got: {user_message}"
        assert "2026-04-10" in user_message, f"End date missing from market_performance. Got: {user_message}"
        
        assert "17.43%" in user_message, f"Percentage change should be calculated. Got: {user_message}"
        
        print(f"\nTest Passed: Dates included in market_performance text.")


@pytest.mark.asyncio
async def test_cause_and_effect_ticker_cleaning():
    """Verify that malformed tickers from LLM are cleaned before market data lookup.
    
    This tests the fix for LLM output like ['XOM', 'CVX,', 'HAL', 'DAL', ',']
    which should be cleaned to ['XOM', 'CVX', 'HAL', 'DAL'].
    
    Also verifies blacklist filtering on LLM-suggested tickers.
    """
    
    mock_sb = MagicMock()
    mock_gemini_client = MagicMock()
    
    event = {
        "id": "uuid-ticker-clean",
        "content": "Energy sector experiencing volatility due to Strait of Hormuz tensions.",
        "created_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        "metadata": {}
    }
    
    mock_sb.table.return_value.select.return_value.filter.return_value.filter.return_value.execute.return_value.data = [event]
    mock_sb.table.return_value.select.return_value.filter.return_value.execute.return_value.data = []

    with patch("apps.engine.analysis.cause_and_effect_analysis.get_supabase_client", return_value=mock_sb), \
         patch("apps.engine.analysis.cause_and_effect_analysis.get_gemini_client", return_value=mock_gemini_client), \
         patch("apps.engine.analysis.cause_and_effect_analysis.MarketDataManager") as mock_mdm_cls, \
         patch("apps.engine.analysis.cause_and_effect_analysis.find_similar_memory", return_value=None), \
         patch("apps.engine.analysis.cause_and_effect_analysis.extract_related_tickers") as mock_extract:
        
        mock_mdm_instance = AsyncMock()
        mock_mdm_cls.return_value = mock_mdm_instance
        mock_mdm_instance.get_history.return_value = [{"price": 100, "fetched_at": "now"}, {"price": 90, "fetched_at": "then"}]
        
        # Simulate malformed LLM output: trailing commas, empty strings, punctuation
        mock_extract.return_value = ["XOM", "CVX,", "HAL", "DAL", ",", "  SPY  ", "US", "A", "THE"]
        
        mock_resp = MagicMock()
        mock_resp.analysis = "Energy sector analysis"
        mock_resp.market_outcome = "XOM outperformed"
        mock_resp.confidence = 85
        mock_resp.tags = ["energy"]
        mock_gemini_client.chat.completions.create.return_value = mock_resp
        
        await perform_cause_and_effect_analysis()
        
        # VERIFICATION: get_history should be called with CLEANED tickers
        called_tickers = [call.args[0] for call in mock_mdm_instance.get_history.call_args_list]
        
        # Should NOT contain malformed tickers
        assert "CVX," not in called_tickers, f"Trailing comma not stripped: {called_tickers}"
        assert "," not in called_tickers, f"Empty string with comma in ticker list: {called_tickers}"
        assert "  SPY  " not in called_tickers, f"Whitespace not stripped: {called_tickers}"
        
        # Should NOT contain blacklist items (even if LLM suggests them)
        assert "US" not in called_tickers, f"Blacklist ticker 'US' should be filtered: {called_tickers}"
        assert "A" not in called_tickers, f"Blacklist ticker 'A' should be filtered: {called_tickers}"
        assert "THE" not in called_tickers, f"Blacklist ticker 'THE' should be filtered: {called_tickers}"
        
        # Should contain cleaned tickers (some of these may be sliced out due to 5-ticker limit)
        # We verify at least some expected cleaned tickers are present
        cleaned_expected = {"XOM", "CVX", "HAL", "DAL", "SPY"}
        called_set = set(called_tickers)
        assert len(called_set & cleaned_expected) >= 3, f"At least 3 expected cleaned tickers should survive. Got: {called_tickers}"
        
        # Benchmarks should be present
        assert "QQQ" in called_tickers, f"QQQ benchmark should be in list: {called_tickers}"
        assert "SPY" in called_tickers, f"SPY benchmark should be in list: {called_tickers}"
        
        # No empty strings or single characters (other than valid tickers like "X" if it existed)
        assert "" not in called_tickers, f"Empty string should not be in tickers: {called_tickers}"
        
        print(f"\nTest Passed: Ticker cleaning removed malformed entries. Final tickers: {called_tickers}")


if __name__ == "__main__":
    asyncio.run(test_cause_and_effect_semantic_dedupe())
