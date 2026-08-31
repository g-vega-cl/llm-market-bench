---
tags: [engine, code-quality, git, forensics]
category: entity
---

# Code Hotspot Analyzer

`apps/engine/hotspots.py` — A git churn forensics and temporal coupling analyzer that identifies high-risk files with elevated bug fix density and implicit architectural dependencies.

## Purpose

Not all high-churn code is fragile. This tool distinguishes normal development churn from bug-prone hot spots by computing a composite score from commit frequency and bug fix density. It also detects temporal coupling: files that consistently change together, revealing hidden architectural dependencies.

## Usage

```bash
# Run with defaults (90-day window, top 20 hotspots)
./apps/engine/.venv/bin/python3 apps/engine/hotspots.py

# Custom lookback
./apps/engine/.venv/bin/python3 apps/engine/hotspots.py --since "30 days ago"

# JSON for automation
./apps/engine/.venv/bin/python3 apps/engine/hotspots.py --json

# Write/refresh wiki concept page with live metrics
./apps/engine/.venv/bin/python3 apps/engine/hotspots.py --write-wiki
```

## Implementation

- Scoped to `apps/` and `packages/` by default; excludes generated files, lockfiles, virtual environments, CI config, migrations, and wiki/source dirs.
- Bug fix heuristic: commit subject matches `fix|bug|broken|patch|hotfix|defect` (case-insensitive).
- Risk levels: CRITICAL (score ≥ 100 or churn ≥ 15 with fix ratio ≥ 35%), HIGH (≥ 30 or churn ≥ 10 with fix ratio ≥ 25%), MEDIUM (≥ 10 or churn ≥ 10), LOW.
- Temporal coupling: requires minimum 3 co-commits and at least 25% coupling ratio for one of the pair.

## Related

- [[concepts/code-hotspots]] — Detailed concept and usage guidelines
- [[entities/engine]] — Parent engine app directory
