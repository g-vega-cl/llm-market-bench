"""Tests for core.db module."""

from unittest.mock import MagicMock, patch

import pytest

from core.db import (
    SUPABASE_RETRIES,
    get_async_supabase_client,
    get_supabase_client,
    is_transient_supabase_error,
    with_retry,
)


class TestSupabaseClients:
    """Tests for Supabase client creation and configuration."""

    def test_get_supabase_client_missing_config(self):
        with patch("core.db.SUPABASE_URL", ""), patch("core.db.SUPABASE_SERVICE_ROLE_KEY", ""):
            with patch("core.db._supabase_client", None):
                with pytest.raises(ValueError) as exc_info:
                    get_supabase_client()
                assert "Supabase configuration missing" in str(exc_info.value)

    def test_get_supabase_client_missing_url_only(self):
        with patch("core.db.SUPABASE_URL", ""), patch("core.db.SUPABASE_SERVICE_ROLE_KEY", "key"):
            with patch("core.db._supabase_client", None):
                with pytest.raises(ValueError) as exc_info:
                    get_supabase_client()
                assert "Supabase configuration missing" in str(exc_info.value)

    def test_get_supabase_client_missing_key_only(self):
        with patch("core.db.SUPABASE_URL", "url"), patch("core.db.SUPABASE_SERVICE_ROLE_KEY", ""):
            with patch("core.db._supabase_client", None):
                with pytest.raises(ValueError) as exc_info:
                    get_supabase_client()
                assert "Supabase configuration missing" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_async_supabase_client_missing_config(self):
        with patch("core.db.SUPABASE_URL", ""), patch("core.db.SUPABASE_SERVICE_ROLE_KEY", ""):
            with patch("core.db._supabase_async_client", None):
                with pytest.raises(ValueError) as exc_info:
                    await get_async_supabase_client()
                assert "Supabase configuration missing" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_async_supabase_client_missing_url_only(self):
        with patch("core.db.SUPABASE_URL", ""), patch("core.db.SUPABASE_SERVICE_ROLE_KEY", "key"):
            with patch("core.db._supabase_async_client", None):
                with pytest.raises(ValueError) as exc_info:
                    await get_async_supabase_client()
                assert "Supabase configuration missing" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_async_supabase_client_missing_key_only(self):
        with patch("core.db.SUPABASE_URL", "url"), patch("core.db.SUPABASE_SERVICE_ROLE_KEY", ""):
            with patch("core.db._supabase_async_client", None):
                with pytest.raises(ValueError) as exc_info:
                    await get_async_supabase_client()
                assert "Supabase configuration missing" in str(exc_info.value)


class TestIsTransientSupabaseError:
    """Tests for is_transient_supabase_error function."""

    def test_recognizes_502_bad_gateway(self):
        exc = Exception("502 Bad Gateway")
        assert is_transient_supabase_error(exc) is True

    def test_recognizes_503_service_unavailable(self):
        exc = Exception("503 Service Unavailable")
        assert is_transient_supabase_error(exc) is True

    def test_recognizes_504_gateway_timeout(self):
        exc = Exception("504 Gateway Timeout")
        assert is_transient_supabase_error(exc) is True

    def test_recognizes_429_too_many_requests(self):
        exc = Exception("429 Too Many Requests")
        assert is_transient_supabase_error(exc) is True

    def test_recognizes_bad_gateway_keyword(self):
        exc = Exception("Bad gateway error occurred")
        assert is_transient_supabase_error(exc) is True

    def test_recognizes_connection_error(self):
        exc = Exception("Connection error: refused")
        assert is_transient_supabase_error(exc) is True

    def test_recognizes_timeout(self):
        exc = Exception("Request timed out")
        assert is_transient_supabase_error(exc) is True

    def test_recognizes_network_error(self):
        exc = Exception("Network error occurred")
        assert is_transient_supabase_error(exc) is True

    def test_recognizes_connection_reset(self):
        exc = Exception("Connection reset by peer")
        assert is_transient_supabase_error(exc) is True

    def test_recognizes_connection_refused(self):
        exc = Exception("Connection refused")
        assert is_transient_supabase_error(exc) is True

    def test_rejects_non_transient_errors(self):
        exc = Exception("Invalid query syntax")
        assert is_transient_supabase_error(exc) is False

    def test_rejects_auth_errors(self):
        exc = Exception("401 Unauthorized")
        assert is_transient_supabase_error(exc) is False

    def test_rejects_not_found_errors(self):
        exc = Exception("404 Not Found")
        assert is_transient_supabase_error(exc) is False

    def test_case_insensitive_matching(self):
        exc = Exception("BAD GATEWAY")
        assert is_transient_supabase_error(exc) is True

    def test_handles_postgrest_api_error(self):
        exc = Exception("{'message': 'JSON could not be generated', 'code': 502}")
        assert is_transient_supabase_error(exc) is True


class TestWithRetry:
    """Tests for with_retry function."""

    def test_succeeds_on_first_attempt(self):
        operation = MagicMock(return_value="success")
        result = with_retry(operation, "test_op")
        assert result == "success"
        operation.assert_called_once()

    def test_retries_on_transient_error(self):
        operation = MagicMock(side_effect=[Exception("502 Bad Gateway"), "success"])
        with patch("time.sleep") as mock_sleep:
            result = with_retry(operation, "test_op")
        assert result == "success"
        assert operation.call_count == 2
        mock_sleep.assert_called_once_with(1)

    def test_exponential_backoff_increases(self):
        operation = MagicMock(side_effect=[Exception("502 Bad Gateway"), Exception("502 Bad Gateway"), "success"])
        with patch("time.sleep") as mock_sleep:
            result = with_retry(operation, "test_op")
        assert result == "success"
        assert operation.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)

    def test_raises_non_transient_error_immediately(self):
        operation = MagicMock(side_effect=Exception("Invalid query syntax"))
        with pytest.raises(Exception) as exc_info:
            with_retry(operation, "test_op")
        assert str(exc_info.value) == "Invalid query syntax"
        operation.assert_called_once()

    def test_exhausts_retries_and_raises(self):
        operation = MagicMock(side_effect=Exception("502 Bad Gateway"))
        with patch("time.sleep"), pytest.raises(Exception) as exc_info:
            with_retry(operation, "test_op")
        assert "502 Bad Gateway" in str(exc_info.value)
        assert operation.call_count == SUPABASE_RETRIES

    def test_uses_correct_retry_count(self):
        operation = MagicMock(side_effect=RuntimeError("502 Bad Gateway"))
        with patch("time.sleep"), pytest.raises(RuntimeError):
            with_retry(operation, "test_op")
        assert operation.call_count == 3
