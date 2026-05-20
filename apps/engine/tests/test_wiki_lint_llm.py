import json
from unittest.mock import MagicMock, patch

import pytest
import requests
from apps.engine.wiki_lint_llm import call_openrouter


def test_call_openrouter_none_content_handled():
    """
    Verify that None content results in a RequestException instead of AttributeError.
    """
    mock_response = MagicMock()
    mock_response.json.return_value = {"choices": [{"message": {"content": None}, "finish_reason": "refusal"}]}
    mock_response.raise_for_status.return_value = None

    with patch("requests.post", return_value=mock_response):
        with pytest.raises(requests.RequestException) as excinfo:
            call_openrouter("fake content", "fake-model", "fake-key")

        assert "OpenRouter returned empty content. Finish reason: refusal" in str(excinfo.value)


def test_call_openrouter_empty_choices_handled():
    """
    Verify that empty choices results in a RequestException instead of IndexError.
    """
    mock_response = MagicMock()
    mock_response.json.return_value = {"choices": []}
    mock_response.raise_for_status.return_value = None

    with patch("requests.post", return_value=mock_response):
        with pytest.raises(requests.RequestException) as excinfo:
            call_openrouter("fake content", "fake-model", "fake-key")

        assert "OpenRouter returned no choices" in str(excinfo.value)


def test_call_openrouter_api_error_handled():
    """
    Verify that OpenRouter 'error' field is handled.
    """
    mock_response = MagicMock()
    mock_response.json.return_value = {"error": {"message": "Model not found"}}
    mock_response.raise_for_status.return_value = None

    with patch("requests.post", return_value=mock_response):
        with pytest.raises(requests.RequestException) as excinfo:
            call_openrouter("fake content", "fake-model", "fake-key")

        assert "OpenRouter API error: Model not found" in str(excinfo.value)


def test_call_openrouter_success():
    """
    Verify successful parsing.
    """
    mock_response = MagicMock()
    mock_response.json.return_value = {"choices": [{"message": {"content": '{"findings": [], "summary": "OK"}'}}]}
    mock_response.raise_for_status.return_value = None

    with patch("requests.post", return_value=mock_response):
        result = call_openrouter("fake content", "fake-model", "fake-key")
        assert result["summary"] == "OK"


def test_call_openrouter_truncated_json():
    """
    Verify that truncated JSON results in a JSONDecodeError and logs the raw content.
    """
    mock_response = MagicMock()
    # Truncated JSON
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {"content": '{"findings": [{"severity": "high", "description": "truncated...'},
                "finish_reason": "length",
            }
        ]
    }
    mock_response.raise_for_status.return_value = None

    with patch("requests.post", return_value=mock_response):
        with pytest.raises(json.JSONDecodeError):
            call_openrouter("fake content", "fake-model", "fake-key")
