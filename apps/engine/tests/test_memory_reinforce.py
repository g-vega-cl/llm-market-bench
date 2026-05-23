"""Tests for memory reinforcement (duplicate bumping)."""

from unittest.mock import MagicMock, patch

import pytest
from apps.engine.memory.store import add_memory


@pytest.fixture
def mock_supabase():
    with patch("apps.engine.memory.store.get_supabase_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_embedding():
    with patch("apps.engine.memory.store.get_embedding") as mock:
        mock.return_value = [0.1, 0.2, 0.3]
        yield mock


def test_add_memory_reinforces_and_bumps_duplicate(mock_embedding, mock_supabase):
    # Mock find_similar_memory to find an existing duplicate
    with patch("apps.engine.memory.store.find_similar_memory") as mock_find:
        mock_find.return_value = "existing-uuid"

        # Mock the update call execution
        mock_update_chain = mock_supabase.table.return_value.update.return_value.eq.return_value.execute
        mock_update_chain.return_value = MagicMock(data=[{"id": "existing-uuid"}])

        # Attempt to add a duplicate memory with check_similarity=True
        result = add_memory("duplicate memory content", check_similarity=True)

        # 1. It should return the existing memory's ID
        assert result == "existing-uuid"

        # 2. It should perform an update to reset relevance_score and created_at
        mock_supabase.table.assert_called_with("memories")
        mock_supabase.table.return_value.update.assert_called_once()

        # Check that the update payload resets relevance_score and updates created_at
        update_args = mock_supabase.table.return_value.update.call_args[0][0]
        assert update_args["relevance_score"] == 1.0
        assert "created_at" in update_args

        # 3. It should NOT call insert
        mock_supabase.table.return_value.insert.assert_not_called()
