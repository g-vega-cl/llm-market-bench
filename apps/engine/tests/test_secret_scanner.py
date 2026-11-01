"""Hermetic unit tests for apps/engine/secret_scanner.py."""

from apps.engine.secret_scanner import scan_file_content, scan_text

# Dynamically assembled synthetic keys for test assertions so static push-protection scanners
# do not misidentify test fixtures as real credentials
_DUMMY_FREE_MASTER = "".join(["s", "k", "-", "f", "r", "e", "e", "-"]) + ("0123456789abcdef" * 3)[:48]
_DUMMY_GROQ = "".join(["g", "s", "k", "_"]) + ("mockgroqtokentestval" * 3)[:52]
_DUMMY_GEMINI = "".join(["A", "I", "z", "a", "S", "y"]) + ("mockgeminitesttoken" * 2)[:33]
_DUMMY_OPENROUTER = "".join(["s", "k", "-", "o", "r", "-", "v", "1", "-"]) + ("0123456789abcdef" * 4)[:64]
_DUMMY_GHP = "".join(["g", "h", "p", "_"]) + ("0123456789abcdefghij0123456789abcdef"[:36])


def test_detects_free_proxy_master_key():
    content = f'apiKey: "{_DUMMY_FREE_MASTER}"'
    findings = scan_text(content, filename="wiki/entities/sample.md")
    assert len(findings) == 1
    assert "Free Proxy Master Key" in findings[0]["rule"]


def test_detects_groq_api_key():
    content = f"GROQ_API_KEY={_DUMMY_GROQ}"
    findings = scan_text(content, filename="wiki/sample.md")
    assert len(findings) == 1
    assert "Groq API Key" in findings[0]["rule"]


def test_detects_google_gemini_api_key():
    content = f"GEMINI_API_KEY={_DUMMY_GEMINI}"
    findings = scan_text(content, filename="docs/config.md")
    assert len(findings) == 1
    assert "Google Gemini API Key" in findings[0]["rule"]


def test_detects_openrouter_api_key():
    content = f"OPENROUTER_API_KEY={_DUMMY_OPENROUTER}"
    findings = scan_text(content, filename="docs/config.md")
    assert len(findings) == 1
    assert "OpenRouter API Key" in findings[0]["rule"]


def test_allows_placeholders():
    content = """
    "apiKey": "<FREE_PROXY_MASTER_KEY>",
    "groq": "gsk_...",
    "gemini": "AIzaSy...",
    "openrouter": "sk-or-v1-...",
    "secret": "sk-free-proxy-secret-key-12345"
    """
    findings = scan_text(content, filename="wiki/entities/sample.md")
    assert len(findings) == 0


def test_allows_env_example_files():
    content = f"GROQ_API_KEY={_DUMMY_GROQ}"
    findings = scan_text(content, filename="apps/free_llm_proxy/.env.example")
    assert len(findings) == 0


def test_scan_file_content(tmp_path):
    f = tmp_path / "test_file.txt"
    f.write_text(f"API_KEY={_DUMMY_GHP}")
    findings = scan_file_content(f)
    assert len(findings) == 1
    assert "GitHub Personal Access Token" in findings[0]["rule"]


def test_scan_git_cached(monkeypatch):
    import subprocess
    from unittest.mock import MagicMock

    from apps.engine import secret_scanner

    mock_proc = MagicMock()
    mock_proc.stdout = f"""diff --git a/wiki/page.md b/wiki/page.md
--- a/wiki/page.md
+++ b/wiki/page.md
@@ -1 +1 @@
-old line
+GROQ_KEY={_DUMMY_GROQ}
"""
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_proc)
    findings = secret_scanner.scan_git_cached()
    assert len(findings) == 1
    assert findings[0]["file"] == "wiki/page.md"


def test_main_cli_findings(monkeypatch):
    import sys

    from apps.engine import secret_scanner

    monkeypatch.setattr(
        secret_scanner, "scan_git_cached", lambda: [{"file": "f.txt", "line": 1, "rule": "R", "masked": "***"}]
    )
    monkeypatch.setattr(sys, "argv", ["secret_scanner.py", "--cached"])
    code = secret_scanner.main()
    assert code == 1


def test_main_cli_clean(monkeypatch):
    import sys

    from apps.engine import secret_scanner

    monkeypatch.setattr(secret_scanner, "scan_git_cached", lambda: [])
    monkeypatch.setattr(sys, "argv", ["secret_scanner.py", "--cached"])
    code = secret_scanner.main()
    assert code == 0
