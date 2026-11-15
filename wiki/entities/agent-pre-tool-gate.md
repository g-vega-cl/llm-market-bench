---
tags: [agent, safety, hooks, git, secrets, tooling]
category: entity
---

# Agent Pre-Tool Gate

`apps/engine/agent_pre_tool_gate.py` is a deterministic `PreToolUse` safety hook for Antigravity coding agents. It inspects every `run_command` shell command *before* execution and returns an `allow` / `deny` decision, enforcing hard boundaries from `GEMINI.md` programmatically rather than relying on emphatic prose.

## Wiring

`.agents/hooks.json` registers the gate as the `agent-safety-gate` hook:

```json
{
  "agent-safety-gate": {
    "enabled": true,
    "PreToolUse": [
      {
        "matcher": "run_command",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ../apps/engine/agent_pre_tool_gate.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

The hook reads a JSON payload from stdin (`toolCall.args.CommandLine`), evaluates the command, and prints `{"decision": "allow"|"deny", "reason": "..."}`. Malformed or non-dict JSON input fails open (`allow`) so a broken payload never bricks the agent.

## Enforced Rules

`evaluate_command(command_line)` splits the command on `\n`, `&&`, `||`, `;`, `&`, and `|` into segments, then applies three checks:

1. **Targeted Git Staging Mandate (Principle 17)** — denies blanket staging. `git add` is denied when any argument matches `-A`/`-a`-style flags, `--all`, `--update`, or a bare `.`/`./`/`..`; `git commit` is denied when any argument matches `-a`-style flags or `--all`. Quoted strings are stripped before token matching so `git commit -m "fix: add ."` is not falsely flagged. `git -C <path>`, `--git-dir`, and `--work-tree` prefixes are tolerated.
2. **File-Based Python Execution Mandate (Principle 12)** — denies multiline inline `python3 -c` (a `python3 -c` invocation whose command line contains a newline). Single-line `-c` is still allowed; the rule targets the multiline scratch-script workaround.
3. **Secret Protection Gate** — denies direct shell reads/dumps of raw `.env` files: `cat`/`less`/`more`/`head`/`tail`/`awk`/`sed`/`source`/`.` targeting `.env` or `.env.<suffix>`, input redirection (`< .env`), and `grep`/`egrep`/`fgrep`/`rg` against a `.env` file. `.env.example`, `.env.sample`, and `.env.template` are explicitly exempt, and grepping for the literal string `.env` in another file (e.g. `grep .env .gitignore`) is allowed.

## Tests

`apps/engine/tests/test_agent_pre_tool_gate.py` is hermetic and covers: hook configuration presence, denial of every blanket-staging variant (including `git -C`, `git commit -am`, and chained `cd ... && git add .`), allowance of explicit file staging and normal git inspection, denial of multiline `python3 -c` with extra flags, denial of `.env` dumps/redirects/sourcing, allowance of `.env.example` and `.env`-string greps, and fail-open behavior on non-dict JSON stdin.

## Related

- [[entities/agent-rules]] — the `GEMINI.md` mandates this gate enforces
- [[concepts/agent-workflow]] — the Search/Plan/TDD sequence and lifecycle gates
- [[concepts/project-linting]] — pre-commit hook ordering
- [[entities/secret-scanner]] — the complementary staged-diff secret scanner
