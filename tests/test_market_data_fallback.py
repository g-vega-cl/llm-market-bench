import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from apps.engine.execution.market_data import MarketDataManager
from apps.engine.execution.providers.base import TickerData

class TestMarketDataFallback(unittest.IsolatedAsyncioTestCase):
    async def test_fallback_logic(self):
        print("\n--- Testing MarketDataManager Fallback Logic ---")
        
        # Mock Supabase Client
        mock_supabase = MagicMock()
        
        # Mock Cache Miss (First check)
        # _get_from_cache returns None
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        
        # Mock Price History (Fallback check)
        # When querying 'price_history', return a record
        def table_side_effect(table_name):
            query_mock = MagicMock()
            if table_name == "market_data_cache":
                # Cache miss
                query_mock.select.return_value.eq.return_value.execute.return_value.data = []
            elif table_name == "price_history":
                # History hit
                query_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [{
                    "ticker": "NVDA",
                    "price": 950.0,
                    "market_cap": 2000000000000,
                    "fetched_at": "2025-01-01T00:00:00+00:00"
                }]
            else:
                 query_mock.insert.return_value.execute.return_value = None
                 query_mock.upsert.return_value.execute.return_value = None
            return query_mock

        mock_supabase.table.side_effect = table_side_effect

        # Mock Provider to FAIL (trigger backoff)
        mock_provider = AsyncMock()
        mock_provider.get_ticker_data.side_effect = Exception("API Down")

        # Patch dependencies
        with patch('apps.engine.execution.market_data.get_supabase_client', return_value=mock_supabase), \
             patch('apps.engine.execution.market_data.get_financial_provider', return_value=mock_provider):
            
            mdm = MarketDataManager()
            
            # --- EXECUTE ---
            # This should try provider 3 times (fail) then use history.
            result = await mdm.get_quote("NVDA")
            
            # --- ASSERT ---
            self.assertIsNotNone(result, "Should return a result from fallback.")
            self.assertEqual(result.price, 950.0, "Should use the historical price ($950).")
            self.assertEqual(mock_provider.get_ticker_data.call_count, 3, "Should have retried 3 times.")
            
            print("✅ TEST PASSED: Retried 3 times and fell back to history.")

if __name__ == "__main__":
    unittest.main()
