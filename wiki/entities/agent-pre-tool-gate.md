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

The hook reads a JSON payload from stdin (`toolCall.args.CommandLine` for Antigravity, `input.command` for Pi via `.pi/extensions/bench-gate.ts`, or `tool_input.command` for Hermes), evaluates the command, and prints `{"decision": "allow"|"deny", "reason": "..."}`. Empty, malformed, or non-dict JSON input **fails closed (`deny`)** so broken hook payloads can never bypass safety enforcement. Also blocks `--no-verify`, `git commit -n`, and `git push --force` / `-f` / `+ref`.

## Enforced Rules

`evaluate_command(command_line)` splits the command on `\n`, `&&`, `||`, `;`, `&`, and `|` into segments, unwraps subshells, tokenizes git invocations with `shlex.split` (handling env prefixes and git global flags), and applies four checks:

1. **Targeted Git Staging Mandate** — denies blanket staging (`git add -A`/`.`/`-u`/`--all`/`--update` and `git commit -a`/`--all`, even when quoted or inside `(cd ... && git add .)`).
2. **Git Hook & Branch Safety Gate** — denies hook bypasses (`git commit --no-verify`/`-n`, `git push --no-verify`) and force pushes (`git push --force`/`-f`/`--force-with-lease`/`+ref`).
3. **File-Based Python Execution Mandate** — denies multiline inline `python3 -c` (a `python3 -c` invocation whose command line contains a newline). Single-line `-c` is still allowed; the rule targets the multiline scratch-script workaround.
4. **Secret Protection Gate** — denies direct shell reads/dumps of raw `.env` files: `cat`/`less`/`more`/`head`/`tail`/`awk`/`sed`/`source`/`.` targeting `.env` or `.env.<suffix>`, input redirection (`< .env`), and `grep`/`egrep`/`fgrep`/`rg` against a `.env` file. `.env.example`, `.env.sample`, and `.env.template` are explicitly exempt, and grepping for the literal string `.env` in another file (e.g. `grep .env .gitignore`) is allowed.

## Tests

`apps/engine/tests/test_agent_pre_tool_gate.py` is hermetic and covers: hook and `.pi/extensions/bench-gate.ts` configuration presence, denial of every blanket-staging, `--no-verify`, and `--force` variant (including subshells, env prefixes, global flags, and quoted arguments), allowance of explicit file staging and normal git inspection, denial of multiline `python3 -c`, denial of `.env` dumps/redirects/sourcing, allowance of `.env.example` and `.env`-string greps, and strict **fail-closed (`deny`)** behavior on empty, malformed, non-dict, or command-missing JSON stdin.

## Related

- [[entities/agent-rules]] — the `GEMINI.md` mandates this gate enforces
- [[concepts/agent-workflow]] — the Search/Plan/TDD sequence and lifecycle gates
- [[concepts/project-linting]] — pre-commit hook ordering
- [[entities/secret-scanner]] — the complementary staged-diff secret scanner
