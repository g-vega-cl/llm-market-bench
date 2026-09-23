---
description: Enforce file-based Python script execution instead of inline python3 -c
---

# File-Based Python Execution (No Multiline `-c`)

## Rationale & Antigravity Security Engine Rules

Antigravity parses shell command tokens and enforces strict execution-hijacking security boundaries:
1. **Execution Hijacking Guardrails (`RequiresExactMatch`)**: Any invocation of an interpreter (`python3`, `bash`, `sh`, `node`) with inline evaluation flags like `-c` or `-e` triggers Antigravity's `RequiresExactMatch` rule. This disables prefix allowlists (such as `command(./apps/engine/.venv/bin/python3)`) and demands an exact string match of the entire command, including code contents.
2. **Grant Regex Limitations**: Antigravity's permission engine validates grants against a single-line regular expression (`^(command|...)\(.*\)$`). Multi-line scripts passed to `-c` fail validation (`invalid grant string`) and cannot be saved or auto-approved.
3. **Dynamic Payloads**: Ad-hoc inline snippets vary on every invocation, preventing permission persistence.

## Mandatory Execution Protocol

When testing modules, executing diagnostics, running one-off queries, or inspecting data:

### 1. Strictly Prohibited
- **NEVER** run multiline or complex Python code via `python3 -c "..."` or `./apps/engine/.venv/bin/python3 -c "..."`.

### 2. Canonical Interpreter
- **ALWAYS** use the repository virtualenv binary:
  ```bash
  ./apps/engine/.venv/bin/python3 <path/to/script.py> [args]
  ```

### 3. Scratch & Temporary Script Locations
When drafting temporary, inspection, or diagnostic scripts:
- **Conversation Scratch Directory**: Write to `<appDataDir>/brain/<conversation-id>/scratch/<name>.py` (automatically persisted across conversation steps).
- **Workspace Scratch Directory**: Write to `.scratch/<name>.py` or `apps/engine/scratch/<name>.py` (gitignored).

### 4. Workflow
1. Write the Python code to a script file using `write_to_file`.
2. Execute the file via:
   ```bash
   ./apps/engine/.venv/bin/python3 .scratch/test_script.py
   ```
3. Read the output.
4. If created in the repository workspace, clean up or delete temporary scratch files once diagnostics are complete.
