"""Tests for MiniMax LLM client."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from core.config import MINIMAX_MODEL


class TestMiniMaxClient:
    """Tests for MiniMaxClient class."""

    def test_client_initialization(self):
        """Test that MiniMaxClient initializes correctly."""
        from core.llm.minimax import MiniMaxClient

        client = MiniMaxClient(api_key="test-key-123")
        assert client.api_key == "test-key-123"
        assert client.BASE_URL == "https://api.minimax.io/v1/text/chatcompletion_v2"
        assert client.TIMEOUT == 120.0

    def test_client_requires_api_key(self):
        """Test that MiniMaxClient raises ValueError without API key."""
        from core.llm import minimax

        with patch.object(minimax, "config", MagicMock()):
            minimax.config.MINIMAX_API_KEY = None
            with pytest.raises(ValueError, match="MINIMAX_API_KEY is required"):
                minimax.MiniMaxClient()


class TestMiniMaxChatParsing:
    """Tests for parsing MiniMax chat responses."""

    @pytest.mark.asyncio
    async def test_chat_with_json_response_parses_correctly(self):
        """Test that JSON responses are parsed correctly."""
        from core.llm.minimax import MiniMaxClient

        mock_response_data = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": '{"sentiment_label": "Cautiously Optimistic", "confidence_score": 75}',
                        "role": "assistant",
                    },
                }
            ],
            "model": MINIMAX_MODEL,
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        with patch.object(MiniMaxClient, "_get_client", return_value=mock_client):
            client = MiniMaxClient(api_key="test-key")
            result = await client.chat_with_json_response(
                messages=[{"role": "user", "content": "test"}], temperature=0.4
            )

            assert result["sentiment_label"] == "Cautiously Optimistic"
            assert result["confidence_score"] == 75

    @pytest.mark.asyncio
    async def test_chat_with_json_response_strips_markdown(self):
        """Test that markdown code blocks are stripped before parsing."""
        from core.llm.minimax import MiniMaxClient

        mock_response_data = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": '```json\n{"sentiment_label": "Risk-Off", "confidence_score": 85}\n```',
                        "role": "assistant",
                    },
                }
            ],
            "model": MINIMAX_MODEL,
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        with patch.object(MiniMaxClient, "_get_client", return_value=mock_client):
            client = MiniMaxClient(api_key="test-key")
            result = await client.chat_with_json_response(messages=[{"role": "user", "content": "test"}])

            assert result["sentiment_label"] == "Risk-Off"

    @pytest.mark.asyncio
    async def test_chat_with_json_response_strips_think_tags(self):
        """Test that <think>...</think> blocks are stripped before parsing."""
        from core.llm.minimax import MiniMaxClient

        mock_response_data = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": '<think>\nHere is some internal thinking process...\n</think>\n```json\n{"predicted_sector": "XLE", "confidence": 80.0}\n```',
                        "role": "assistant",
                    },
                }
            ],
            "model": MINIMAX_MODEL,
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        with patch.object(MiniMaxClient, "_get_client", return_value=mock_client):
            client = MiniMaxClient(api_key="test-key")
            result = await client.chat_with_json_response(messages=[{"role": "user", "content": "test"}])

            assert result["predicted_sector"] == "XLE"
            assert result["confidence"] == 80.0

    @pytest.mark.asyncio
    async def test_chat_with_json_response_extracts_inline_json(self):
        """Test that inline JSON surrounded by plain text is extracted properly."""
        from core.llm.minimax import MiniMaxClient

        mock_response_data = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": 'Here is my prediction:\n{"predicted_sector": "XLK", "confidence": 90.0}\nHope this helps!',
                        "role": "assistant",
                    },
                }
            ],
            "model": MINIMAX_MODEL,
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        with patch.object(MiniMaxClient, "_get_client", return_value=mock_client):
            client = MiniMaxClient(api_key="test-key")
            result = await client.chat_with_json_response(messages=[{"role": "user", "content": "test"}])

            assert result["predicted_sector"] == "XLK"
            assert result["confidence"] == 90.0

    @pytest.mark.asyncio
    async def test_chat_with_json_response_parses_yaml_fallback(self):
        """Test that unbracketed YAML response is parsed into dict via fallback."""
        from core.llm.minimax import MiniMaxClient

        yaml_content = (
            "predicted_direction: DOWN\n"
            "confidence: 53\n"
            "expected_return_pct: -0.15\n"
            "rationale: |\n"
            "  Starting from the 50% zero-mean base rate, the evidence tilts modestly bearish.\n"
            "catalysts:\n"
            "  - Prior session weakness\n"
            "  - Yield surge\n"
        )
        mock_response_data = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": yaml_content,
                        "role": "assistant",
                    },
                }
            ],
            "model": MINIMAX_MODEL,
            "usage": {"prompt_tokens": 120, "completion_tokens": 60},
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        with patch.object(MiniMaxClient, "_get_client", return_value=mock_client):
            client = MiniMaxClient(api_key="test-key")
            result = await client.chat_with_json_response(messages=[{"role": "user", "content": "test"}])

            assert result["predicted_direction"] == "DOWN"
            assert result["confidence"] == 53
            assert result["expected_return_pct"] == -0.15
            assert "zero-mean base rate" in result["rationale"]
            assert result["catalysts"] == ["Prior session weakness", "Yield surge"]

    @pytest.mark.asyncio
    async def test_chat_with_json_response_raises_on_invalid_json(self):
        """Test that invalid JSON raises ValueError."""
        from core.llm.minimax import MiniMaxClient

        mock_response_data = {
            "choices": [{"message": {"content": "This is not JSON at all", "role": "assistant"}}],
            "model": MINIMAX_MODEL,
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        with patch.object(MiniMaxClient, "_get_client", return_value=mock_client):
            client = MiniMaxClient(api_key="test-key")
            with pytest.raises(ValueError, match="Invalid JSON response"):
                await client.chat_with_json_response(messages=[{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_chat_returns_processing_time(self):
        """Test that chat returns processing time in milliseconds."""
        from core.llm.minimax import MiniMaxClient

        mock_response_data = {
            "choices": [{"finish_reason": "stop", "message": {"content": "Hello", "role": "assistant"}}],
            "model": MINIMAX_MODEL,
            "usage": {"prompt_tokens": 50, "completion_tokens": 10},
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        with patch.object(MiniMaxClient, "_get_client", return_value=mock_client):
            client = MiniMaxClient(api_key="test-key")
            result = await client.chat(messages=[{"role": "user", "content": "test"}])

            assert "processing_time_ms" in result
            assert result["processing_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_chat_raises_on_http_status_error(self):
        """Test that chat raises httpx.HTTPStatusError on non-200 and logs error body."""
        import httpx

        from core.llm.minimax import MiniMaxClient

        mock_request = httpx.Request("POST", "https://api.minimax.io/v1/text/chatcompletion_v2")
        mock_response = httpx.Response(
            status_code=400,
            json={"error": {"message": "Invalid API Key"}},
            request=mock_request,
        )

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        with (
            patch.object(MiniMaxClient, "_get_client", return_value=mock_client),
            patch("core.llm.minimax.logger") as mock_logger,
        ):
            client = MiniMaxClient(api_key="test-key")
            with pytest.raises(httpx.HTTPStatusError):
                await client.chat(messages=[{"role": "user", "content": "test"}])

            mock_logger.error.assert_called_once_with(
                "MiniMax API HTTP error %d: %s",
                400,
                {"error": {"message": "Invalid API Key"}},
            )

    @pytest.mark.asyncio
    async def test_chat_raises_on_base_resp_error(self):
        """Test that chat raises ValueError on base_resp error."""
        from core.llm.minimax import MiniMaxClient

        mock_response_data = {
            "base_resp": {
                "status_code": 1004,
                "status_msg": "API key invalid",
            }
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        with (
            patch.object(MiniMaxClient, "_get_client", return_value=mock_client),
            patch("core.llm.minimax.logger") as mock_logger,
        ):
            client = MiniMaxClient(api_key="test-key")
            with pytest.raises(ValueError, match="MiniMax API error in base_resp: status_code=1004"):
                await client.chat(messages=[{"role": "user", "content": "test"}])

            mock_logger.error.assert_called_once_with(
                "MiniMax API error in base_resp: status_code=1004, status_msg='API key invalid'"
            )

    @pytest.mark.asyncio
    async def test_chat_raises_on_generic_error_field(self):
        """Test that chat raises ValueError on generic error field in JSON response."""
        from core.llm.minimax import MiniMaxClient

        mock_response_data = {"error": "Quota Exceeded"}

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        with (
            patch.object(MiniMaxClient, "_get_client", return_value=mock_client),
            patch("core.llm.minimax.logger") as mock_logger,
        ):
            client = MiniMaxClient(api_key="test-key")
            with pytest.raises(ValueError, match="MiniMax API error: Quota Exceeded"):
                await client.chat(messages=[{"role": "user", "content": "test"}])

            mock_logger.error.assert_called_once_with("MiniMax API error: Quota Exceeded")

    @pytest.mark.asyncio
    async def test_chat_logs_warning_on_empty_choices(self):
        """Test that chat logs a warning when choices is empty."""
        from core.llm.minimax import MiniMaxClient

        mock_response_data = {
            "choices": [],
            "model": "MiniMax-M3",
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        with (
            patch.object(MiniMaxClient, "_get_client", return_value=mock_client),
            patch("core.llm.minimax.logger") as mock_logger,
        ):
            client = MiniMaxClient(api_key="test-key")
            result = await client.chat(messages=[{"role": "user", "content": "test"}])

            assert result["content"] == ""
            assert result["finish_reason"] is None
            mock_logger.warning.assert_called_once_with(
                "MiniMax API returned response with empty choices. Full response: %s",
                mock_response_data,
            )


class TestMiniMaxContextManager:
    """Tests for MiniMax async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_close(self):
        """Test that context manager properly closes client."""
        from core.llm.minimax import MiniMaxClient

        mock_http_client = MagicMock()
        mock_http_client.is_closed = False
        mock_http_client.aclose = AsyncMock()

        client = MiniMaxClient(api_key="test-key")
        client._client = mock_http_client

        await client.close()

        mock_http_client.aclose.assert_called_once()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_context_manager_with_statement(self):
        """Test that async with statement works correctly."""
        from core.llm.minimax import MiniMaxClient

        with patch.object(MiniMaxClient, "close", new=AsyncMock()) as mock_close:
            async with MiniMaxClient(api_key="test-key") as client:
                assert client.api_key == "test-key"

            mock_close.assert_called_once()
