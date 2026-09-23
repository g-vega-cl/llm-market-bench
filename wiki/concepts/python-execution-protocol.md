---
tags: [agents, execution, security, antigravity]
category: concept
---

# File-Based Python Execution

Mandatory agent protocol requiring all Python work to be executed from script files via the repository virtualenv binary, never as inline multiline `python3 -c "..."` commands. Driven by the security constraints of Antigravity's permission engine.

## Rationale

Inline interpreter invocations with evaluation flags (`-c`/`-e`) trip Antigravity's `RequiresExactMatch` execution-hijacking guardrail, which disables prefix allowlists (e.g. `command(./apps/engine/.venv/bin/python3)`) and demands an exact full-command match including code contents.

Three mechanisms make inline `-c` untenable:

1. **Execution Hijacking Guardrails** — `RequiresExactMatch` blocks prefix allowlisting of inline evaluation.
2. **Grant Regex Limitations** — Grant validation is a single-line regex (`^(command|...)\(.*\)$`); multi-line `-c` payloads fail with `invalid grant string` and cannot be saved or auto-approved.
3. **Dynamic Payloads** — Ad-hoc snippets vary per invocation, defeating permission persistence.

## Execution Protocol

- **Prohibited**: multiline or complex Python via `python3 -c "..."` or `./apps/engine/.venv/bin/python3 -c "..."`.
- **Canonical interpreter**: always `./apps/engine/.venv/bin/python3 <path/to/script.py> [args]`.
- **Scratch locations**: conversation scratch `<appDataDir>/brain/<conversation-id>/scratch/<name>.py`, or gitignored workspace scratch `.scratch/<name>.py` / `apps/engine/scratch/<name>.py`.
- **Workflow**: write script with `write_to_file` → execute via virtualenv binary → read output → clean up temporary workspace scratch files.

## Relationship to Agent Rules

Codified as mandatory rule #12 in `GEMINI.md` and detailed in `.agents/rules/python-execution.md`, both enforced by the agent instruction system documented in [[entities/agent-rules]].

## Related

- [[entities/agent-rules]]
- [[concepts/agent-workflow]]
