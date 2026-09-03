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


def test_call_openrouter_reasoning_exhausted_handled():
    """
    Verify that empty content due to reasoning token exhaustion has a descriptive error.
    """
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": None,
                    "reasoning": "Thinking about all 100 wiki files in depth...",
                },
                "finish_reason": "length",
            }
        ]
    }
    mock_response.raise_for_status.return_value = None

    with patch("requests.post", return_value=mock_response):
        with pytest.raises(requests.RequestException) as excinfo:
            call_openrouter("fake content", "fake-model", "fake-key")

        assert "token limit was exhausted during reasoning" in str(excinfo.value)


def test_call_openrouter_http_error_extracts_message():
    """
    Verify that HTTP 4xx/5xx errors extract and surface OpenRouter's error message.
    """
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status_code = 400
    mock_response.json.return_value = {"error": {"message": "Invalid reasoning effort: low"}}
    mock_response.raise_for_status.side_effect = requests.HTTPError("400 Client Error: Bad Request")

    with patch("requests.post", return_value=mock_response):
        with pytest.raises(requests.RequestException) as excinfo:
            call_openrouter("fake content", "deepseek/deepseek-v4-flash", "fake-key")

        assert "Invalid reasoning effort: low" in str(excinfo.value)
        assert "400" in str(excinfo.value)


def test_call_openrouter_payload_settings():
    """
    Verify that payload includes increased max_tokens and reasoning controls without invalid effort.
    """
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {"choices": [{"message": {"content": '{"findings": [], "summary": "OK"}'}}]}
    mock_response.raise_for_status.return_value = None

    with patch("requests.post", return_value=mock_response) as mock_post:
        call_openrouter("fake content", "fake-model", "fake-key")
        assert mock_post.called
        payload = mock_post.call_args[1]["json"]
        assert payload["max_tokens"] >= 8192
        assert "reasoning" in payload
        assert "effort" not in payload["reasoning"]
        assert payload["reasoning"].get("max_tokens") == 4096


def test_get_recent_commits():
    from apps.engine.wiki_lint_llm import get_recent_commits

    mock_log = (
        "COMMIT:abc1234 feat(engine): update predictor\n"
        "apps/engine/tasks/daily_predictor.py\n"
        "wiki/entities/daily-market-predictor.md\n"
        "\n"
        "COMMIT:def5678 fix(config): fix tool config\n"
        "packages/config/tools.json\n"
    )

    with patch("subprocess.check_output", return_value=mock_log):
        summary, changed_files = get_recent_commits(days=7)
        assert "feat(engine): update predictor" in summary
        assert "apps/engine/tasks/daily_predictor.py" in changed_files
        assert "packages/config/tools.json" in changed_files
        # wiki/ files should be excluded from changed code files
        assert "wiki/entities/daily-market-predictor.md" not in changed_files


def test_find_matching_wiki_pages(tmp_path):
    from apps.engine.wiki_lint_llm import find_matching_wiki_pages

    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    page1 = wiki_dir / "predictor.md"
    page1.write_text("Documents `apps/engine/tasks/daily_predictor.py`.")
    page2 = wiki_dir / "unrelated.md"
    page2.write_text("Documents something else.")

    changed_files = {"apps/engine/tasks/daily_predictor.py"}
    matched = find_matching_wiki_pages(changed_files, wiki_dir=wiki_dir)

    assert "predictor.md" in matched
    assert "unrelated.md" not in matched
