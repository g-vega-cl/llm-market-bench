"""Tests for core.audit.analyzer module."""

import pytest
import json
from unittest.mock import AsyncMock, patch


class TestAnalyzeLogBlob:
    """Tests for the analyze_log_blob function."""

    @pytest.fixture
    def mock_deepseek_response(self):
        """Sample valid DeepSeek response."""
        return json.dumps([
            {
                "title": "Connection Timeout",
                "severity": "HIGH",
                "suggestion": "Increase timeout threshold or check network connectivity"
            },
            {
                "title": "Missing Configuration",
                "severity": "MEDIUM",
                "suggestion": "Add the missing config file to the deployment"
            }
        ])

    def test_configure_sets_api_key(self):
        """Verify configure function sets the API key."""
        from core.audit.analyzer import configure

        configure("test-key-123")
        from core.audit import analyzer
        assert analyzer.DEEPSEEK_API_KEY == "test-key-123"

    @pytest.mark.asyncio
    async def test_analyze_log_blob_parses_valid_json(self, mock_deepseek_response):
        """Verify valid JSON response is parsed correctly."""
        from core.audit.analyzer import analyze_log_blob, configure

        configure("test-key")

        with patch("core.audit.analyzer.AsyncOpenAI") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.chat.completions.create = AsyncMock(
                return_value=AsyncMock(
                    choices=[
                        AsyncMock(
                            message=AsyncMock(content=mock_deepseek_response)
                        )
                    ]
                )
            )
            mock_client.return_value = mock_instance

            result = await analyze_log_blob("test log blob")

            assert result is not None
            parsed = json.loads(result)
            assert len(parsed) == 2
            assert parsed[0]["title"] == "Connection Timeout"

    @pytest.mark.asyncio
    async def test_analyze_log_blob_handles_markdown_json(self):
        """Verify JSON wrapped in markdown code blocks is handled."""
        from core.audit.analyzer import analyze_log_blob, configure

        configure("test-key")

        markdown_json = '''```json
[
  {"title": "Error 1", "severity": "HIGH", "suggestion": "Fix it"}
]
```'''

        with patch("core.audit.analyzer.AsyncOpenAI") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.chat.completions.create = AsyncMock(
                return_value=AsyncMock(
                    choices=[
                        AsyncMock(message=AsyncMock(content=markdown_json))
                    ]
                )
            )
            mock_client.return_value = mock_instance

            result = await analyze_log_blob("test")

            assert result is not None
            parsed = json.loads(result)
            assert len(parsed) == 1

    @pytest.mark.asyncio
    async def test_analyze_log_blob_truncates_long_input(self):
        """Verify long log blobs are truncated to fit context window."""
        from core.audit.analyzer import analyze_log_blob, configure

        configure("test-key")

        long_blob = "x" * 50000
        expected_truncated = "x" * 32000

        with patch("core.audit.analyzer.AsyncOpenAI") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.chat.completions.create = AsyncMock(
                return_value=AsyncMock(
                    choices=[
                        AsyncMock(message=AsyncMock(content="[]"))
                    ]
                )
            )
            mock_client.return_value = mock_instance

            await analyze_log_blob(long_blob)

            call_args = mock_instance.chat.completions.create.call_args
            messages = call_args.kwargs["messages"]
            assert len(messages[0]["content"]) <= 35000
            assert expected_truncated in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_analyze_log_blob_handles_malformed_json(self):
        """Verify malformed JSON falls back gracefully."""
        from core.audit.analyzer import analyze_log_blob, configure

        configure("test-key")

        with patch("core.audit.analyzer.AsyncOpenAI") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.chat.completions.create = AsyncMock(
                return_value=AsyncMock(
                    choices=[
                        AsyncMock(message=AsyncMock(content="This is not valid JSON"))
                    ]
                )
            )
            mock_client.return_value = mock_instance

            result = await analyze_log_blob("test")

            assert result is not None
            assert "Raw analysis" in result

    @pytest.mark.asyncio
    async def test_analyze_log_blob_handles_api_error(self):
        """Verify API errors are handled gracefully."""
        from core.audit.analyzer import analyze_log_blob, configure

        configure("test-key")

        with patch("core.audit.analyzer.AsyncOpenAI") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.chat.completions.create = AsyncMock(
                side_effect=Exception("API Error")
            )
            mock_client.return_value = mock_instance

            result = await analyze_log_blob("test")

            assert result is None

    @pytest.mark.asyncio
    async def test_analyze_log_blob_no_api_key(self):
        """Verify behavior when API key is not configured."""
        from core.audit.analyzer import analyze_log_blob

        result = await analyze_log_blob("test log")
        assert result is None
