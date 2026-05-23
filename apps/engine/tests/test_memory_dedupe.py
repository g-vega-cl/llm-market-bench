import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from apps.engine.memory.store import add_memory, find_similar_memory


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


@pytest.fixture
def mock_cosine():
    # We patch 'analysis.consensus.cosine_similarity' because store.py imports it as 'from consensus ...'
    # and sys.path in the test makes 'consensus' a top-level module.
    # We accept either path to be safe, but 'consensus' is likely the active one.
    try:
        target = "analysis.consensus.cosine_similarity"
        with patch(target) as mock:
            yield mock
    except ImportError:
        target = "apps.engine.analysis.consensus.cosine_similarity"
        with patch(target) as mock:
            yield mock


def test_find_similar_memory_no_embedding(mock_embedding, mock_supabase):
    mock_embedding.return_value = None
    result = find_similar_memory("test content")
    assert result is None


def test_find_similar_memory_no_recent_memories(mock_embedding, mock_supabase):
    # Setup mock response for empty DB result
    mock_supabase.table.return_value.select.return_value.filter.return_value.filter.return_value.execute.return_value.data = []

    result = find_similar_memory("test content")
    assert result is None


def test_find_similar_memory_match_found(mock_embedding, mock_supabase, mock_cosine):
    # Setup mock DB response
    mock_row = {"id": "existing-uuid", "embedding": "[0.1, 0.2, 0.3]", "content": "similar content"}
    mock_supabase.table.return_value.select.return_value.filter.return_value.filter.return_value.execute.return_value.data = [
        mock_row
    ]

    # Setup high similarity
    mock_cosine.return_value = 0.95

    result = find_similar_memory("test content", threshold=0.90)
    assert result == "existing-uuid"


def test_find_similar_memory_no_match_found(mock_embedding, mock_supabase, mock_cosine):
    # Setup mock DB response
    mock_row = {"id": "existing-uuid", "embedding": "[0.1, 0.2, 0.3]", "content": "different content"}
    mock_supabase.table.return_value.select.return_value.filter.return_value.filter.return_value.execute.return_value.data = [
        mock_row
    ]

    # Setup low similarity
    mock_cosine.return_value = 0.50

    result = find_similar_memory("test content", threshold=0.90)
    assert result is None


def test_add_memory_duplicates_blocked(mock_embedding, mock_supabase):
    # Mock find_similar_memory to return a match
    with patch("apps.engine.memory.store.find_similar_memory") as mock_find:
        mock_find.return_value = "existing-uuid"

        # Mock the update call execution
        mock_update_chain = mock_supabase.table.return_value.update.return_value.eq.return_value.execute
        mock_update_chain.return_value = MagicMock(data=[{"id": "existing-uuid"}])

        result = add_memory("test content", check_similarity=True)

        assert result == "existing-uuid"
        # Verify DB update was called
        mock_supabase.table.return_value.update.assert_called_once()
        # Verify DB insert was NOT called
        mock_supabase.table.return_value.insert.assert_not_called()


def test_add_memory_unique_inserted(mock_embedding, mock_supabase):
    # Mock find_similar_memory to return None (no match)
    with patch("apps.engine.memory.store.find_similar_memory") as mock_find:
        mock_find.return_value = None

        # Mock insert response
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": "new-uuid"}]

        result = add_memory("test content", check_similarity=True)

        assert result == "new-uuid"
        # Verify DB insert WAS called
        mock_supabase.table.return_value.insert.assert_called_once()
