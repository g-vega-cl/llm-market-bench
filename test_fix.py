from unittest.mock import patch

def test_something():
    with patch("apps.engine.memory.store.add_memory") as mock_add_memory:
        mock_add_memory.return_value = "uuid-consolidated"
        # We need to run the async test... wait, let's just edit the test_memory_consolidation.py directly
