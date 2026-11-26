"""Tests for the auto-wiki LLM tier chain.

The chain must be fully remote: OpenRouter primary -> OpenRouter free -> the
in-repo free-llm-proxy. A local on-device tier must never come back, because it
requires tens of GB of RAM that contributors do not have and its model store is
empty on a clean machine, so the tier always fails and blocks commits.
"""

import pathlib
import sys

import pytest
import requests

REPO_ROOT = pathlib.Path(__file__).parents[3]
DIFF_SAMPLE = """diff --git a/apps/engine/example.py b/apps/engine/example.py
--- a/apps/engine/example.py
+++ b/apps/engine/example.py
@@ -1,2 +1,3 @@
 def hello():
-    return "hi"
+    return "hello"
"""


def _fake_response(content: str = '{"should_update": false}') -> object:
    class _Resp:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"choices": [{"message": {"content": content}}]}

    return _Resp()


@pytest.fixture
def diff_file(tmp_path) -> pathlib.Path:
    path = tmp_path / "staged.diff"
    path.write_text(DIFF_SAMPLE)
    return path


def test_call_free_proxy_posts_openai_compatible_payload(monkeypatch):
    """Tier 3 must call the free-llm-proxy, not a local on-device server."""
    import apps.engine.auto_wiki as aw

    monkeypatch.setenv("FREE_LLM_PROXY_URL", "https://proxy.test/v1")
    monkeypatch.setenv("FREE_PROXY_MASTER_KEY", "master-key")
    monkeypatch.delenv("WIKI_DOC_PROXY_MODEL", raising=False)

    captured: dict = {}

    def fake_post(url, **kwargs):
        captured.update(url=url, payload=kwargs.get("json"), headers=kwargs.get("headers"))
        return _fake_response()

    monkeypatch.setattr(aw.requests, "post", fake_post)

    result = aw.call_free_proxy("prompt text", "auto-go")

    assert captured["url"] == "https://proxy.test/v1/chat/completions"
    assert captured["payload"]["model"] == "auto-go"
    assert captured["headers"]["Authorization"] == "Bearer master-key"
    assert result == {"should_update": False}


def test_call_free_proxy_defaults_to_auto_go_model(monkeypatch):
    import apps.engine.auto_wiki as aw

    monkeypatch.setenv("FREE_LLM_PROXY_URL", "https://proxy.test/v1")
    monkeypatch.setenv("FREE_PROXY_MASTER_KEY", "master-key")
    monkeypatch.delenv("WIKI_DOC_PROXY_MODEL", raising=False)
    captured: dict = {}

    def fake_post(url, **kwargs):
        captured.update(payload=kwargs.get("json"))
        return _fake_response()

    monkeypatch.setattr(aw.requests, "post", fake_post)
    aw.call_free_proxy("prompt text")

    assert captured["payload"]["model"] == "auto-go"


def test_call_free_proxy_allows_loopback_without_master_key(monkeypatch):
    """A loopback proxy is keyless; a remote one is not."""
    import apps.engine.auto_wiki as aw

    monkeypatch.setenv("FREE_LLM_PROXY_URL", "http://127.0.0.1:8080/v1")
    monkeypatch.delenv("FREE_PROXY_MASTER_KEY", raising=False)
    captured: dict = {}

    def fake_post(url, **kwargs):
        captured.update(headers=kwargs.get("headers"))
        return _fake_response()

    monkeypatch.setattr(aw.requests, "post", fake_post)
    aw.call_free_proxy("prompt text")

    assert captured["headers"]["Authorization"] == "Bearer local"


def test_call_free_proxy_requires_master_key_for_remote_proxy(monkeypatch):
    import apps.engine.auto_wiki as aw

    monkeypatch.setenv("FREE_LLM_PROXY_URL", "https://proxy.test/v1")
    monkeypatch.delenv("FREE_PROXY_MASTER_KEY", raising=False)
    monkeypatch.setattr(
        aw.requests,
        "post",
        lambda *a, **k: pytest.fail("must not hit the network without a master key"),
    )

    with pytest.raises(RuntimeError, match="FREE_PROXY_MASTER_KEY"):
        aw.call_free_proxy("prompt text")


def test_call_openrouter_raises_runtime_error_on_error_body_without_choices(monkeypatch):
    """An out-of-credit 200 with {"error": ...} must not crash the tier chain.

    `resp.json()["choices"]` raised KeyError here, and main() only catches
    RequestException / JSONDecodeError / RuntimeError — so the whole run died
    before the free backup and the proxy were ever tried.
    """
    import apps.engine.auto_wiki as aw

    class _ErrorResp:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "error": {"code": 402, "message": "Insufficient credits"},
            }

    monkeypatch.setattr(aw.requests, "post", lambda *a, **k: _ErrorResp())

    with pytest.raises(RuntimeError, match="Insufficient credits"):
        aw.call_openrouter("prompt text", "some/model", "or-key")


def test_main_falls_back_to_free_proxy_when_openrouter_fails(monkeypatch, diff_file):
    """Both OpenRouter tiers failing must route to the free-llm-proxy, then succeed."""
    import apps.engine.auto_wiki as aw

    calls: list[str] = []

    def failing_openrouter(prompt, model, api_key):
        calls.append(f"openrouter:{model}")
        raise requests.RequestException("503 upstream")

    def fake_proxy(prompt, model="auto-go"):
        calls.append(f"proxy:{model}")
        return {"should_update": False}

    monkeypatch.setattr(aw, "get_api_key", lambda: "or-key")
    monkeypatch.setattr(aw, "call_openrouter", failing_openrouter)
    monkeypatch.setattr(aw, "call_free_proxy", fake_proxy)
    monkeypatch.setattr(sys, "argv", ["auto_wiki.py", "--diff-file", str(diff_file)])

    with pytest.raises(SystemExit) as exc:
        aw.main()

    assert exc.value.code == 0
    assert calls[-1] == "proxy:auto-go", calls
    assert all(c.startswith("openrouter:") for c in calls[:-1]), calls


def test_main_blocks_commit_when_all_tiers_fail(monkeypatch, diff_file):
    import apps.engine.auto_wiki as aw

    def failing_openrouter(prompt, model, api_key):
        raise requests.RequestException("503 upstream")

    def failing_proxy(prompt, model="auto-go"):
        raise requests.RequestException("proxy down")

    monkeypatch.setattr(aw, "get_api_key", lambda: "or-key")
    monkeypatch.setattr(aw, "call_openrouter", failing_openrouter)
    monkeypatch.setattr(aw, "call_free_proxy", failing_proxy)
    monkeypatch.setattr(sys, "argv", ["auto_wiki.py", "--diff-file", str(diff_file)])

    with pytest.raises(SystemExit) as exc:
        aw.main()

    assert exc.value.code == 1


def test_no_local_on_device_llm_references_remain():
    """The on-device tier is gone from both the script and its shell wrapper."""
    sources = {
        "apps/engine/auto_wiki.py": (REPO_ROOT / "apps/engine/auto_wiki.py").read_text(),
        "scripts/auto-wiki.sh": (REPO_ROOT / "scripts/auto-wiki.sh").read_text(),
    }
    for name, text in sources.items():
        assert "ollama" not in text.lower(), f"{name} still references the removed on-device tier"
        assert "11434" not in text, f"{name} still targets the removed on-device port"


def test_post_with_wall_clock_aborts_hung_request(monkeypatch):
    """A stalled HTTP request must abort at the wall-clock deadline and raise requests.Timeout."""
    import threading

    import apps.engine.auto_wiki as aw

    release = threading.Event()

    def stalled_post(*args, **kwargs):
        release.wait(timeout=5.0)
        return _fake_response()

    monkeypatch.setattr(aw.requests, "post", stalled_post)

    try:
        with pytest.raises(requests.Timeout, match="wall-clock deadline"):
            aw._post_with_wall_clock(
                "https://openrouter.ai/api/v1/chat/completions",
                payload={},
                headers={},
                timeout_s=0.05,
            )
    finally:
        release.set()
