"""Hermetic tests for the Antigravity PreToolUse safety gate hook script."""

import io
import json
from pathlib import Path

from agent_pre_tool_gate import evaluate_command, main

REPO_ROOT = Path(__file__).resolve().parents[3]
GATE_SCRIPT = REPO_ROOT / "apps" / "engine" / "agent_pre_tool_gate.py"
HOOKS_JSON = REPO_ROOT / ".agents" / "hooks.json"


def _run_gate_main(monkeypatch, capsys, command_line: str) -> dict:
    payload = {
        "hookEventName": "PreToolUse",
        "toolCall": {
            "id": "toolu_test",
            "name": "run_command",
            "args": {"CommandLine": command_line},
        },
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    main()
    captured = capsys.readouterr()
    return json.loads(captured.out)


def test_hooks_json_configured():
    """Verify .agents/hooks.json exists and registers PreToolUse on run_command."""
    assert HOOKS_JSON.is_file(), ".agents/hooks.json must exist"
    assert GATE_SCRIPT.is_file(), "apps/engine/agent_pre_tool_gate.py must exist"
    config = json.loads(HOOKS_JSON.read_text())
    assert "agent-safety-gate" in config
    pre_tool = config["agent-safety-gate"]["PreToolUse"]
    assert any(group.get("matcher") == "run_command" for group in pre_tool)


def test_blocks_blanket_git_staging(monkeypatch, capsys):
    """Blanket git staging commands and flag/multiline variations must be denied."""
    for forbidden in [
        "git add -A",
        "git add .",
        "git add ./",
        "git add -- .",
        "git add -f .",
        "git add -v -A",
        "git add -u",
        "git -C apps/engine add .",
        "git commit -a -m 'fix: test'",
        "git commit -m 'fix: test' -a",
        "git commit -m 'fix: test' --all",
        "git commit -am 'fix: test'",
        "cd apps/engine && git add .",
        "git status --short\ngit add .",
    ]:
        res = _run_gate_main(monkeypatch, capsys, forbidden)
        assert res["decision"] == "deny", f"Expected deny for: {forbidden}"
        assert "Targeted Git Staging" in res["reason"]


def test_allows_targeted_git_staging(monkeypatch, capsys):
    """Explicit file staging and normal git inspection must be allowed."""
    for allowed in [
        "",
        "git add GEMINI.md apps/engine/wiki_lint.py",
        "git add .agents/hooks.json",
        "git status --short",
        "git diff --cached --stat",
        "git commit -m 'feat(wiki): compact GEMINI.md and block git add -a' -m '- Remove duplicate sections'",
    ]:
        res = _run_gate_main(monkeypatch, capsys, allowed)
        assert res["decision"] == "allow", f"Expected allow for: {allowed}"


def test_blocks_multiline_python_c(monkeypatch, capsys):
    """Multiline inline python -c commands (with or without extra flags) must be denied."""
    for multiline_cmd in [
        './apps/engine/.venv/bin/python3 -c "import sys\nprint(sys.version)"',
        'python3 -u -B -c "import os\nprint(os.getcwd())"',
    ]:
        res = _run_gate_main(monkeypatch, capsys, multiline_cmd)
        assert res["decision"] == "deny", f"Expected deny for: {multiline_cmd}"
        assert "scratch" in res["reason"].lower()


def test_blocks_raw_dotenv_dump():
    """Direct shell dumps, redirects, or sourcing of .env files must be denied."""
    for dotenv_cmd in [
        "cat .env",
        "cat apps/engine/.env",
        "cat .env.local",
        "cat .env.production",
        "grep SUPABASE apps/engine/.env",
        "rg API_KEY .env",
        "source .env",
        ". apps/engine/.env",
        "cat < .env",
    ]:
        decision, _ = evaluate_command(dotenv_cmd)
        assert decision == "deny", f"Expected deny for: {dotenv_cmd}"


def test_allows_dotenv_example_and_grep_patterns_and_non_dict_json(monkeypatch, capsys):
    """Reading .env.example, grepping for '.env' in .gitignore, or non-dict JSON must allow."""
    for safe_cmd in [
        "cat apps/engine/.env.example",
        "cat .env.template",
        "grep .env .gitignore",
        "git status | grep .env",
        "./apps/engine/.venv/bin/ruff check apps/engine/",
        "./apps/engine/.venv/bin/python3 apps/engine/wiki_lint.py",
    ]:
        decision, _ = evaluate_command(safe_cmd)
        assert decision == "allow", f"Expected allow for: {safe_cmd}"

    for odd_stdin in ["{not-valid-json", "null", "[]", '"string"', "123"]:
        monkeypatch.setattr("sys.stdin", io.StringIO(odd_stdin))
        main()
        captured = capsys.readouterr()
        assert json.loads(captured.out)["decision"] == "allow"
