import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add apps/engine to path
sys.path.append(os.path.join(os.getcwd(), "apps", "engine"))

from memory.store import retrieve_context_batch

class TestMemoryRAG(unittest.IsolatedAsyncioTestCase):
    async def test_retrieve_context_batch_combined(self):
        print("\n--- Testing retrieve_context_batch (Combined Memories & Decisions) ---")
        
        mock_supabase = MagicMock()
        
        # Mock embeddings
        mock_embeddings = [[0.1] * 768]
        
        # Mock match_memories response
        mock_mem_data = [
            {"content": "Oil prices surged due to geopolitics", "similarity": 0.9}
        ]
        
        # Mock match_decisions response
        mock_dec_data = [
            {"ticker": "XOM", "signal": "BUY", "reasoning": "High oil prices benefit energy sector", "similarity": 0.85}
        ]
        
        def rpc_side_effect(name, params):
            rpc_mock = MagicMock()
            if name == "match_memories":
                rpc_mock.execute.return_value.data = mock_mem_data
            elif name == "match_decisions":
                rpc_mock.execute.return_value.data = mock_dec_data
            return rpc_mock

        mock_supabase.rpc.side_effect = rpc_side_effect
        
        with patch('memory.store.get_supabase_client', return_value=mock_supabase), \
             patch('memory.store.get_embeddings_batch', return_value=mock_embeddings):
            
            results = retrieve_context_batch(["Test query"], limit=3)
            
            print(f"Results: {results}")
            
            self.assertEqual(len(results), 1)
            context = results[0]
            
            # Check if both are present
            self.assertIn("[PAST REASONING (HISTORICAL)]", context)
            self.assertIn("Oil prices surged", context)
            self.assertIn("[PAST REASONING (HISTORICAL)]", context)
            self.assertIn("XOM BUY", context)
            self.assertIn("High oil prices benefit energy sector", context)
            
            print("✅ TEST PASSED: retrieve_context_batch correctly combines memories and decisions.")

if __name__ == "__main__":
    unittest.main()
