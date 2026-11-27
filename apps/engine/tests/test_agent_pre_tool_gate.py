"""Hermetic tests for the multi-CLI PreToolUse safety gate and Fedora persistence scripts."""

import io
import json
from pathlib import Path

from agent_pre_tool_gate import evaluate_command, main

REPO_ROOT = Path(__file__).resolve().parents[3]
GATE_SCRIPT = REPO_ROOT / "apps" / "engine" / "agent_pre_tool_gate.py"
HOOKS_JSON = REPO_ROOT / ".agents" / "hooks.json"
PI_EXTENSION = REPO_ROOT / ".pi" / "extensions" / "bench-gate.ts"


def _run_gate_main(monkeypatch, capsys, payload_obj: dict | str) -> dict:
    raw = payload_obj if isinstance(payload_obj, str) else json.dumps(payload_obj)
    monkeypatch.setattr("sys.stdin", io.StringIO(raw))
    main()
    captured = capsys.readouterr()
    return json.loads(captured.out)


def _agy_payload(command_line: str | None) -> dict:
    return {
        "hookEventName": "PreToolUse",
        "toolCall": {
            "id": "toolu_test",
            "name": "run_command",
            "args": {"CommandLine": command_line},
        },
    }


def test_hooks_and_pi_extension_configured():
    """Verify .agents/hooks.json and .pi/extensions/bench-gate.ts exist and reference the gate."""
    assert HOOKS_JSON.is_file(), ".agents/hooks.json must exist"
    assert GATE_SCRIPT.is_file(), "apps/engine/agent_pre_tool_gate.py must exist"
    assert PI_EXTENSION.is_file(), ".pi/extensions/bench-gate.ts must exist"

    config = json.loads(HOOKS_JSON.read_text())
    assert "agent-safety-gate" in config
    pre_tool = config["agent-safety-gate"]["PreToolUse"]
    assert any("run_command" in group.get("matcher", "") for group in pre_tool)
    ext_text = PI_EXTENSION.read_text()
    assert "agent_pre_tool_gate.py" in ext_text
    assert "realpathSync" in ext_text


def test_blocks_blanket_git_staging_including_subshells_env_and_quotes(monkeypatch, capsys):
    """Blanket git staging commands across subshells, env prefixes, global flags, and quotes must be denied."""
    for forbidden in [
        "git add -A",
        "git add .",
        'git add "."',
        'git add "-A"',
        "git add ./",
        "git add -- .",
        "git add -f .",
        "git add -v -A",
        "git add -u",
        "git -C apps/engine add .",
        "git --no-pager add .",
        "(cd apps/engine && git add .)",
        "/usr/bin/git add .",
        "SEQUENTIAL=1 git commit -am 'fix: test'",
        "git commit -a -m 'fix: test'",
        "git commit -m 'fix: test' -a",
        "git commit -m 'fix: test' --all",
        "cd apps/engine && git add .",
        "git status --short\ngit add .",
    ]:
        res = _run_gate_main(monkeypatch, capsys, _agy_payload(forbidden))
        assert res["decision"] == "deny", f"Expected deny for: {forbidden}"
        assert "Targeted Git Staging" in res["reason"]


def test_blocks_no_verify_and_force_push_variants():
    """Hook bypasses and force pushes across subshells, env vars, git -c, and quotes must be denied."""
    for forbidden in [
        "git commit --no-verify -m 'chore: skip'",
        'git commit "--no-verify" -m "chore: skip"',
        "SEQUENTIAL=1 git commit --no-verify -m 'chore: skip'",
        "git commit -n -m 'chore: skip'",
        "git push --no-verify origin feat/x",
        "git push --force origin main",
        "(git push --force origin main)",
        "git -c user.name=bot push --force origin main",
        "/usr/bin/git push -f origin feat/x",
        'git push origin "+main"',
    ]:
        decision, reason = evaluate_command(forbidden)
        assert decision == "deny", f"Expected deny for: {forbidden}"
        assert reason


def test_allows_targeted_git_staging_and_commit_messages_with_dots(monkeypatch, capsys):
    """Explicit file staging and commit messages mentioning flags or dots must be allowed."""
    for allowed in [
        "",
        "git add AGENTS.md apps/engine/wiki_lint.py",
        "git add .agents/hooks.json",
        "git status --short",
        "git diff --cached --stat",
        "git commit -m 'feat(wiki): compact AGENTS.md and block git add . or -a' -m '- Remove duplicate sections'",
        "SEQUENTIAL=1 git commit -m 'fix(engine): handle edge case' -m '- Add hermetic test'",
        "git push -u origin feat/agentic-overhaul",
    ]:
        res = _run_gate_main(monkeypatch, capsys, _agy_payload(allowed))
        assert res["decision"] == "allow", f"Expected allow for: {allowed}"


def test_supports_pi_and_hermes_payload_shapes(monkeypatch, capsys):
    """Gate must extract bash commands from Pi, Hermes, and arguments.cmd shapes."""
    pi_payload = {"toolName": "bash", "input": {"command": "git add ."}}
    hermes_payload = {"tool_name": "terminal", "tool_input": {"command": "git push --force"}}
    alt_payload = {"tool_name": "bash", "arguments": {"cmd": "git push -f"}}

    assert _run_gate_main(monkeypatch, capsys, pi_payload)["decision"] == "deny"
    assert _run_gate_main(monkeypatch, capsys, hermes_payload)["decision"] == "deny"
    assert _run_gate_main(monkeypatch, capsys, alt_payload)["decision"] == "deny"

    pi_safe = {"toolName": "bash", "input": {"command": "git status --short"}}
    assert _run_gate_main(monkeypatch, capsys, pi_safe)["decision"] == "allow"


def test_blocks_multiline_python_c(monkeypatch, capsys):
    """Multiline inline python -c commands must be denied."""
    for multiline_cmd in [
        './apps/engine/.venv/bin/python3 -c "import sys\nprint(sys.version)"',
        'python3 -u -B -c "import os\nprint(os.getcwd())"',
    ]:
        res = _run_gate_main(monkeypatch, capsys, _agy_payload(multiline_cmd))
        assert res["decision"] == "deny", f"Expected deny for: {multiline_cmd}"
        assert "scratch" in res["reason"].lower()


def test_blocks_raw_dotenv_dump():
    """Direct shell dumps, redirects, or sourcing of .env files must be denied."""
    for dotenv_cmd in [
        "cat .env",
        "(cat apps/engine/.env)",
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


def test_fails_closed_on_malformed_empty_dict_or_null_command(monkeypatch, capsys):
    """Malformed JSON, empty {}, or shell tool calls missing a string command must fail closed."""
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

    for bad_input in [
        "",
        "   ",
        "{not-valid-json",
        "null",
        "[]",
        '"string"',
        "123",
        {},
        _agy_payload(None),
        {"toolName": "bash", "input": {}},
    ]:
        res = _run_gate_main(monkeypatch, capsys, bad_input)
        assert res["decision"] == "deny", f"Expected fail-closed deny for input: {bad_input!r}"
