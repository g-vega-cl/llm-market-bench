---
tags: [python, tooling, conventions, scratch, diagnostics]
category: concept
---

# Python Execution Protocol

A mandatory project convention governing how Python is executed for testing,
diagnostics, one-off queries, and inspection. The rule is **file-based execution
only** — no inline `-c` and no multiline Python passed on the command line.

## Core Rule: Zero Inline `-c`

Never execute multiline Python via `python -c "..."`. Instead, write the code to
a script file and execute the file. This keeps the invoked command auditable,
diffable, and reproducible, and avoids quoting/escaping hazards.

```bash
./apps/engine/.venv/bin/python3 <path/to/script.py>
```

Always use the project virtualenv interpreter (`./apps/engine/.venv/bin/python3`)
so diagnostics run against the same dependency set as the engine.

## Scratch & Temporary Script Locations

When drafting temporary, inspection, or diagnostic scripts, choose the location
in this priority order:

1. **Conversation scratch directory (preferred)** — write to
   `<appDataDir>/brain/<conversation-id>/scratch/<name>.py`. This directory is
   automatically persisted across conversation steps, keeps the repository
   workspace clean, and avoids triggering shell permission prompts during manual
   cleanup.
2. **Workspace scratch directory (fallback)** — use `.scratch/<name>.py` or
   `apps/engine/scratch/<name>.py` (gitignored) **only** when local relative path
   resolution is strictly required. Note that executing shell `rm` commands on
   workspace files may trigger permission-confirmation prompts.

## Workflow

1. Write the Python code to a script file using `write_to_file`.
2. Execute the file via `./apps/engine/.venv/bin/python3 <path/to/script.py>`.
3. Read the output.
4. Prefer conversation scratch so cleanup is handled cleanly without manual shell
   `rm` commands in the workspace.

## Related

- [[entities/engine]] — the component whose modules these scripts exercise
- [[concepts/tool-domain-decomposition]] — sibling convention for tool design
- [[concepts/workflow-consolidation]] — sibling convention for CI task placement
