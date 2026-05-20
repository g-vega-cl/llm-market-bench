from unittest.mock import MagicMock, patch

import pytest

import memory.embeddings
from memory.embeddings import get_client, get_embeddings_batch


@pytest.fixture(autouse=True)
def reset_client():
    """Reset the cached client before each test."""
    memory.embeddings._client = None
    yield


def test_get_client_missing_key():
    """Test that get_client raises ValueError when API key is missing."""
    with patch("core.config.GEMINI_API_KEY", None), pytest.raises(ValueError, match="GEMINI_API_KEY is not set"):
        get_client()


def test_get_client_success():
    """Test that get_client creates and caches the client."""
    mock_client = MagicMock()
    with (
        patch("core.config.GEMINI_API_KEY", "fake-key"),
        patch("google.genai.Client", return_value=mock_client) as mock_genai,
    ):
        client1 = get_client()
        client2 = get_client()

        assert client1 == mock_client
        assert client2 == mock_client
        assert mock_genai.call_count == 1


def test_get_embeddings_batch_missing_key():
    """Test that get_embeddings_batch returns empty list and logs error when key is missing."""
    with patch("core.config.GEMINI_API_KEY", None):
        results = get_embeddings_batch(["test"])
        assert results == []


def test_get_embeddings_batch_success():
    """Test successful batch embedding."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_embedding = MagicMock()
    mock_embedding.values = [0.1, 0.2, 0.3]
    mock_response.embeddings = [mock_embedding]
    mock_client.models.embed_content.return_value = mock_response

    with patch("core.config.GEMINI_API_KEY", "fake-key"), patch("google.genai.Client", return_value=mock_client):
        results = get_embeddings_batch(["test text"])
        assert results == [[0.1, 0.2, 0.3]]
        mock_client.models.embed_content.assert_called_once()


def test_get_embeddings_batch_api_error():
    """Test that get_embeddings_batch handles API errors gracefully."""
    mock_client = MagicMock()
    mock_client.models.embed_content.side_effect = Exception("API Error")

    with patch("core.config.GEMINI_API_KEY", "fake-key"), patch("google.genai.Client", return_value=mock_client):
        results = get_embeddings_batch(["test text"])
        assert results == []
