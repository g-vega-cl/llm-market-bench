"""Tests for FMP provider error handling and logging."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from execution.providers.fmp import FMPProvider


class TestFMPErrorLogging:
    """Tests for FMP error logging behavior."""

    @pytest.fixture
    def fmp_provider(self):
        """Create FMPProvider instance with API key set."""
        with patch("execution.providers.fmp.FMP_API_KEY", "test_api_key"):
            provider = FMPProvider()
            return provider

    @pytest.mark.asyncio
    async def test_httpx_status_error_logs_response_body(self, fmp_provider, caplog):
        """Test that HTTPStatusError logs the response body when available."""
        import logging

        caplog.set_level(logging.DEBUG)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error Details"
        mock_response.url = "https://financialmodelingprep.com/stable/quote?symbol=TEST"

        error = httpx.HTTPStatusError("Server Error", request=MagicMock(), response=mock_response)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=error)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await fmp_provider.get_ticker_data("TEST")

        assert result is None

        # HTTP status errors are logged at ERROR level (not retried like generic exceptions)
        error_logs = [c.message for c in caplog.records if c.levelno == logging.ERROR]
        assert len(error_logs) > 0, "Expected error log"
        assert any("500" in msg and "Internal Server Error Details" in msg for msg in error_logs), (
            f"Expected status code and response body in error message, got: {error_logs}"
        )

    @pytest.mark.asyncio
    async def test_empty_response_error_logs_repr(self, fmp_provider, caplog):
        """Test that empty error messages include repr() fallback in retry attempts."""
        import logging

        caplog.set_level(logging.DEBUG)

        class EmptyStrError(Exception):
            def __str__(self):
                return ""

        error = EmptyStrError("test error")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=error)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await fmp_provider.get_ticker_data("TEST")

        assert result is None

        # With retries, per-attempt errors are logged at WARNING level with repr fallback
        warning_logs = [c.message for c in caplog.records if c.levelno == logging.WARNING]
        assert len(warning_logs) > 0, "Expected warning log from retry attempt"
        assert any("EmptyStrError" in msg for msg in warning_logs), (
            f"Expected repr in warning message, got: {warning_logs}"
        )

    @pytest.mark.asyncio
    async def test_402_error_is_logged_as_api_quota(self, fmp_provider, caplog):
        """Test that 402 errors are logged specifically as API quota exceeded."""
        import logging

        caplog.set_level(logging.ERROR)

        mock_response = MagicMock()
        mock_response.status_code = 402
        mock_response.url = "https://financialmodelingprep.com/stable/quote?symbol=TEST"
        mock_response.text = ""

        error = httpx.HTTPStatusError("Payment Required", request=MagicMock(), response=mock_response)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=error)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await fmp_provider.get_ticker_data("TEST")

        assert result is None

        # Check that 402 was logged as quota exceeded
        error_logs = [c.message for c in caplog.records if c.levelno >= logging.ERROR]
        assert any("Quota" in msg or "402" in msg for msg in error_logs), (
            f"Expected quota error message, got: {error_logs}"
        )


class TestFMPErrorLoggingEdgeCases:
    """Edge case tests for FMP error logging."""

    @pytest.mark.asyncio
    async def test_generic_exception_logs_str_and_repr(self, caplog):
        """Test that generic exceptions include both str and repr in retry warning logs."""
        import logging

        caplog.set_level(logging.DEBUG)

        with patch("execution.providers.fmp.FMP_API_KEY", "test_api_key"):
            provider = FMPProvider()

        class CustomError(Exception):
            def __str__(self):
                return "custom error message"

        error = CustomError()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=error)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await provider.get_ticker_data("TEST")

        assert result is None

        # With retries, per-attempt errors are logged at WARNING level
        warning_logs = [c.message for c in caplog.records if c.levelno == logging.WARNING]
        assert any("custom error message" in msg for msg in warning_logs), (
            f"Expected str error in warning message, got: {warning_logs}"
        )
