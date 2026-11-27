#!/usr/bin/env python3
"""Deterministic fail-closed PreToolUse safety gate for Antigravity, Pi, and Hermes.

Enforces hard boundaries from AGENTS.md before shell commands execute:
1. Blocks blanket git staging (git add -A, git add ., git add -u, git commit -a/-am).
2. Blocks git hook bypasses (--no-verify, git commit -n) and force pushes (git push --force/-f/+ref).
3. Blocks multiline inline python -c execution (requires .scratch/ scripts).
4. Blocks direct shell reads/dumps of raw .env secret files.
5. Fails closed (decision == "deny") on empty, malformed, non-dict, or unparseable shell payloads.
"""

import json
import re
import shlex
import sys
from pathlib import PurePosixPath
from typing import Any, Literal

Decision = Literal["allow", "deny"]

SEGMENT_SPLIT_RE = re.compile(r"(?:\n|&&|\|\||[;&|])+")
ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*$")

GIT_GLOBAL_OPTS_WITH_ARG = {"-C", "--git-dir", "--work-tree", "-c", "--exec-path", "--namespace", "--config-env"}
GIT_ADD_BLANKET_TOKEN_RE = re.compile(r"^(?:-[a-zA-Z]*[Au][a-zA-Z]*|--all|--update|\.\.?/?)$")
GIT_COMMIT_OPTS_WITH_ARG = {
    "-m",
    "--message",
    "-F",
    "--file",
    "-C",
    "--reuse-message",
    "-c",
    "--reedit-message",
    "--author",
    "--date",
    "--cleanup",
    "--untracked-files",
}
GIT_COMMIT_ALL_TOKEN_RE = re.compile(r"^(?:-[a-zA-Z]*a[a-zA-Z]*|--all)$")
GIT_COMMIT_NO_VERIFY_TOKEN_RE = re.compile(r"^(?:-[a-zA-Z]*n[a-zA-Z]*|--no-verify)$")
GIT_PUSH_OPTS_WITH_ARG = {"--repo", "--receive-pack", "--exec", "-o", "--push-option"}
GIT_PUSH_FORBIDDEN_TOKEN_RE = re.compile(
    r"^(?:-[a-zA-Z]*f[a-zA-Z]*|--force|--force-with-lease(?:=\S+)?|--force-if-includes|--no-verify|\+\S+)$"
)

PYTHON_C_RE = re.compile(r"\bpython3?(?:\.[0-9]+)?(?:\s+-[a-zA-Z0-9]+)*\s+-c\s+")
DOTENV_TARGET_TOKEN = r"(?:^|[\s/\"'=])\.env(?:\.(?!example\b|sample\b|template\b)[a-zA-Z0-9_\-]+)?(?:\s|$|[\"')])"
DOTENV_READER_RE = re.compile(r"^\s*\(*\s*(?:cat|less|more|head|tail|awk|sed|source|\.)(?=\s).*" + DOTENV_TARGET_TOKEN)
DOTENV_REDIRECT_RE = re.compile(
    r"<+\s*(?:\S*/)?\.env(?:\.(?!example\b|sample\b|template\b)[a-zA-Z0-9_\-]+)?(?:\s|$|[\"')])"
)
DOTENV_GREP_RE = re.compile(r"^\s*\(*\s*(?:grep|egrep|fgrep|rg)\b(?:\s+-[a-zA-Z0-9]+)*\s+\S+.*" + DOTENV_TARGET_TOKEN)
SHELL_TOOL_NAMES = {"run_command", "bash", "terminal", "shell", "exec"}


def _tokenize_git_subcommand(segment: str) -> tuple[str | None, list[str], bool]:
    """Return (git_subcommand, subcommand_args, parse_failed) for a single shell segment."""
    cleaned = segment.strip().lstrip("(").rstrip(")").strip()
    if not cleaned:
        return None, [], False
    try:
        tokens = shlex.split(cleaned)
    except ValueError:
        return None, [], True

    idx = 0
    while idx < len(tokens) and ENV_ASSIGN_RE.match(tokens[idx]):
        idx += 1
    if idx < len(tokens) and PurePosixPath(tokens[idx]).name == "env":
        idx += 1
        while idx < len(tokens) and (tokens[idx].startswith("-") or ENV_ASSIGN_RE.match(tokens[idx])):
            idx += 1
    if idx >= len(tokens) or PurePosixPath(tokens[idx]).name != "git":
        return None, [], False

    idx += 1
    while idx < len(tokens):
        tok = tokens[idx]
        if tok in GIT_GLOBAL_OPTS_WITH_ARG:
            idx += 2
            continue
        if tok.startswith("-"):
            idx += 1
            continue
        return tok, tokens[idx + 1 :], False
    return None, [], False


def _strip_opt_values(args: list[str], opts_with_arg: set[str]) -> list[str]:
    """Filter out option value arguments (like commit -m <msg>) so message text is not mistaken for flags."""
    filtered: list[str] = []
    skip_next = False
    for tok in args:
        if skip_next:
            skip_next = False
            continue
        if tok in opts_with_arg:
            filtered.append(tok)
            skip_next = True
            continue
        filtered.append(tok)
    return filtered


def _check_git_segment(segment: str) -> tuple[Decision, str]:
    subcmd, raw_args, parse_failed = _tokenize_git_subcommand(segment)
    if parse_failed and "git" in segment:
        return "deny", "Safety gate failed closed: unbalanced quotes in git command."
    if subcmd == "add" and any(GIT_ADD_BLANKET_TOKEN_RE.match(tok) for tok in raw_args):
        return (
            "deny",
            "Targeted Git Staging Mandate (AGENTS.md): Blanket staging "
            "(`git add -A`, `git add .`, `git add -u`, `git commit -a`) is prohibited. "
            "Stage only the specific files modified for your task (`git add <file1> <file2>`).",
        )
    if subcmd == "commit":
        args = _strip_opt_values(raw_args, GIT_COMMIT_OPTS_WITH_ARG)
        if any(GIT_COMMIT_ALL_TOKEN_RE.match(tok) for tok in args):
            return (
                "deny",
                "Targeted Git Staging Mandate (AGENTS.md): Blanket staging "
                "(`git add -A`, `git add .`, `git add -u`, `git commit -a`) is prohibited.",
            )
        if any(GIT_COMMIT_NO_VERIFY_TOKEN_RE.match(tok) for tok in args):
            return (
                "deny",
                "Git Hook & Branch Safety Gate (AGENTS.md): Bypassing hooks (`--no-verify`, `commit -n`) "
                "and force-pushing (`git push --force`, `-f`, `+ref`) are prohibited.",
            )
    if subcmd == "push":
        args = _strip_opt_values(raw_args, GIT_PUSH_OPTS_WITH_ARG)
        if any(GIT_PUSH_FORBIDDEN_TOKEN_RE.match(tok) for tok in args):
            return (
                "deny",
                "Git Hook & Branch Safety Gate (AGENTS.md): Bypassing hooks (`--no-verify`, `commit -n`) "
                "and force-pushing (`git push --force`, `-f`, `+ref`) are prohibited.",
            )
    return "allow", ""


def _is_dotenv_dump_segment(segment: str) -> bool:
    stripped = segment.strip()
    if DOTENV_READER_RE.search(stripped) or DOTENV_REDIRECT_RE.search(stripped):
        return True
    return bool(DOTENV_GREP_RE.search(stripped))


def evaluate_command(command_line: str) -> tuple[Decision, str]:
    """Return (decision, reason) for a shell command string."""
    if not command_line:
        return "allow", ""

    segments = [seg for seg in SEGMENT_SPLIT_RE.split(command_line) if seg.strip()]
    for seg in segments:
        decision, reason = _check_git_segment(seg)
        if decision == "deny":
            return decision, reason

    if PYTHON_C_RE.search(command_line) and "\n" in command_line:
        return (
            "deny",
            "File-Based Python Execution Mandate (AGENTS.md): Multiline inline "
            "`python3 -c` is prohibited. Write a temporary script to `.scratch/<name>.py` "
            "and run `./apps/engine/.venv/bin/python3 .scratch/<name>.py`.",
        )

    if any(_is_dotenv_dump_segment(seg) for seg in segments):
        return (
            "deny",
            "Secret Protection Gate: Dumping raw `.env` files is prohibited. "
            "Inspect `apps/engine/.env.example` or `apps/engine/core/config.py` instead.",
        )

    return "allow", ""


def _extract_tool_and_command(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return (tool_name, command_line) across Antigravity, Pi, and Hermes hook schemas."""
    tool_name: str | None = None
    for name_key in ("toolName", "tool_name", "name"):
        if isinstance(payload.get(name_key), str):
            tool_name = payload[name_key]
            break

    tool_call = payload.get("toolCall")
    if isinstance(tool_call, dict):
        if isinstance(tool_call.get("name"), str):
            tool_name = tool_call["name"]
        args = tool_call.get("args")
        if isinstance(args, dict) and isinstance(args.get("CommandLine"), str):
            return tool_name, args["CommandLine"]

    for container_key in ("input", "tool_input", "args", "arguments"):
        sub = payload.get(container_key)
        if isinstance(sub, dict):
            for cmd_key in ("command", "CommandLine", "cmd"):
                if isinstance(sub.get(cmd_key), str):
                    return tool_name, sub[cmd_key]

    if isinstance(payload.get("command"), str):
        return tool_name or "shell", payload["command"]
    return tool_name, None


def main() -> None:
    raw_input = sys.stdin.read()
    if not raw_input.strip():
        print(json.dumps({"decision": "deny", "reason": "Safety gate failed closed: empty hook payload."}))
        return

    try:
        payload = json.loads(raw_input)
    except Exception:
        print(json.dumps({"decision": "deny", "reason": "Safety gate failed closed: malformed JSON payload."}))
        return

    if not isinstance(payload, dict) or not payload:
        print(json.dumps({"decision": "deny", "reason": "Safety gate failed closed: expected non-empty JSON object."}))
        return

    tool_name, command_line = _extract_tool_and_command(payload)
    if command_line is None:
        if tool_name is None or tool_name.lower() in SHELL_TOOL_NAMES:
            print(
                json.dumps(
                    {
                        "decision": "deny",
                        "reason": "Safety gate failed closed: missing string command in shell hook payload.",
                    }
                )
            )
            return
        print(json.dumps({"decision": "allow"}))
        return

    decision, reason = evaluate_command(command_line)
    response: dict[str, str] = {"decision": decision}
    if reason:
        response["reason"] = reason
    print(json.dumps(response))


if __name__ == "__main__":
    main()
