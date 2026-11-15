#!/usr/bin/env python3
"""Deterministic PreToolUse safety gate for Antigravity coding agents.

Enforces hard boundaries from GEMINI.md before shell commands execute:
1. Blocks blanket git staging (git add -A, git add ., git add -u, git commit -a/-am).
2. Blocks multiline inline python -c execution (requires scratch files per Principle 12).
3. Blocks direct shell reads/dumps of raw .env secret files.
"""

import json
import re
import sys
from typing import Literal

Decision = Literal["allow", "deny"]

SEGMENT_SPLIT_RE = re.compile(r"(?:\n|&&|\|\||[;&|])+")
QUOTED_STR_RE = re.compile(r"""(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')""")

GIT_ADD_CMD_RE = re.compile(r"^\s*git(?:\s+(?:-C|--git-dir|--work-tree)\s+\S+)*\s+add\b(.*)$")
GIT_ADD_BLANKET_TOKEN_RE = re.compile(r"^(?:-[a-zA-Z]*[Au][a-zA-Z]*|--all|--update|\.\.?/?)$")

GIT_COMMIT_CMD_RE = re.compile(r"^\s*git(?:\s+(?:-C|--git-dir|--work-tree)\s+\S+)*\s+commit\b(.*)$")
GIT_COMMIT_ALL_TOKEN_RE = re.compile(r"^(?:-[a-zA-Z]*a[a-zA-Z]*|--all)$")

PYTHON_C_RE = re.compile(r"\bpython3?(?:\.[0-9]+)?(?:\s+-[a-zA-Z0-9]+)*\s+-c\s+")

DOTENV_TARGET_TOKEN = r"(?:^|[\s/\"'=])\.env(?:\.(?!example\b|sample\b|template\b)[a-zA-Z0-9_\-]+)?(?:\s|$|[\"'])"

DOTENV_READER_RE = re.compile(r"^\s*(?:cat|less|more|head|tail|awk|sed|source|\.)(?=\s).*" + DOTENV_TARGET_TOKEN)
DOTENV_REDIRECT_RE = re.compile(
    r"<+\s*(?:\S*/)?\.env(?:\.(?!example\b|sample\b|template\b)[a-zA-Z0-9_\-]+)?(?:\s|$|[\"'])"
)
DOTENV_GREP_RE = re.compile(r"^\s*(?:grep|egrep|fgrep|rg)\b(?:\s+-[a-zA-Z0-9]+)*\s+\S+.*" + DOTENV_TARGET_TOKEN)


def _is_blanket_git_segment(segment: str) -> bool:
    unquoted = QUOTED_STR_RE.sub('""', segment.strip())

    add_match = GIT_ADD_CMD_RE.match(unquoted)
    if add_match:
        tokens = add_match.group(1).split()
        if any(GIT_ADD_BLANKET_TOKEN_RE.match(tok) for tok in tokens):
            return True

    commit_match = GIT_COMMIT_CMD_RE.match(unquoted)
    if commit_match:
        tokens = commit_match.group(1).split()
        if any(GIT_COMMIT_ALL_TOKEN_RE.match(tok) for tok in tokens):
            return True

    return False


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

    if any(_is_blanket_git_segment(seg) for seg in segments):
        return (
            "deny",
            "Targeted Git Staging Mandate (GEMINI.md Principle 17): Blanket staging "
            "(`git add -A`, `git add .`, `git add -u`, `git commit -a`) is prohibited. "
            "Stage only the specific files modified for your task (`git add <file1> <file2>`).",
        )

    if PYTHON_C_RE.search(command_line) and "\n" in command_line:
        return (
            "deny",
            "File-Based Python Execution Mandate (GEMINI.md Principle 12): Multiline inline "
            "`python3 -c` is prohibited. Write a temporary script to conversation scratch or "
            "`.scratch/<name>.py` and run `./apps/engine/.venv/bin/python3 <script.py>`.",
        )

    if any(_is_dotenv_dump_segment(seg) for seg in segments):
        return (
            "deny",
            "Secret Protection Gate: Dumping raw `.env` files is prohibited. "
            "Inspect `apps/engine/.env.example` or `apps/engine/core/config.py` instead.",
        )

    return "allow", ""


def main() -> None:
    try:
        raw_input = sys.stdin.read()
        payload = json.loads(raw_input) if raw_input.strip() else {}
    except Exception:
        print(json.dumps({"decision": "allow"}))
        return

    if not isinstance(payload, dict):
        print(json.dumps({"decision": "allow"}))
        return

    tool_call = payload.get("toolCall")
    if not isinstance(tool_call, dict):
        tool_call = {}
    args = tool_call.get("args")
    if not isinstance(args, dict):
        args = {}
    command_line = args.get("CommandLine")
    if not isinstance(command_line, str):
        command_line = ""

    decision, reason = evaluate_command(command_line)
    response: dict[str, str] = {"decision": decision}
    if reason:
        response["reason"] = reason

    print(json.dumps(response))


if __name__ == "__main__":
    main()
