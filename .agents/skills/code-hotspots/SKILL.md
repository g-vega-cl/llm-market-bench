---
name: code-hotspots
description: Analyze git churn, bug hotspots, and temporal coupling to detect high-risk files and implicit architectural dependencies.
---

# Code Hotspots & Churn Forensics

Use this skill during research, planning, or refactoring to locate high-friction files and avoid stepping into known bug clusters.

## Why this matters

High churn alone is normal development. High churn paired with a high ratio of bug fixes signals fragile code where changes frequently cause regressions.

When editing high-risk files, small modifications have a wide blast radius. Use the forensics script to identify these files before planning or writing code.

## Running the analysis

Run the analyzer from the repo root:

```bash
./apps/engine/.venv/bin/python3 apps/engine/hotspots.py
```

### Useful options

- Custom lookback window:
  ```bash
  ./apps/engine/.venv/bin/python3 apps/engine/hotspots.py --since "30 days ago"
  ```
- JSON output for automated scripting:
  ```bash
  ./apps/engine/.venv/bin/python3 apps/engine/hotspots.py --json
  ```
- Update living wiki concept documentation:
  ```bash
  ./apps/engine/.venv/bin/python3 apps/engine/hotspots.py --write-wiki
  ```

## Working with hotspots

When your task involves files flagged as **CRITICAL** or **HIGH** risk:

1. **Write reproduction and regression tests first.**
   High-risk files have broken repeatedly. Do not touch them without a test that verifies existing behavior and asserts your fix.

2. **Check temporal coupling (co-churn).**
   Inspect whether your target file is tightly coupled to another file. If file A changes with file B in >50% of commits, check file B to ensure types, schemas, and companion tests stay in sync.

3. **Keep edits narrow.**
   Avoid bundling speculative refactors into bug fixes on hotspot files. Keep the diff small and focused.

4. **Decompose when appropriate.**
   If a file shows up repeatedly at the top of the hotspot list with high churn and >30% bug fixes, propose extracting discrete sub-modules instead of adding more procedural branches.
