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

# Team health forensics: bus factor, commit velocity, crisis cadence
./apps/engine/.venv/bin/python3 apps/engine/hotspots.py --team

# Write/refresh wiki concept page with live metrics (implies --team)
./apps/engine/.venv/bin/python3 apps/engine/hotspots.py --write-wiki
```

## Implementation

- Scoped to `apps/` and `packages/` by default; excludes generated files, lockfiles, virtual environments, CI config, migrations, and wiki/source dirs.
- Bug fix heuristic: commit subject matches `fix|bug|broken|patch|hotfix|defect` (case-insensitive).
- Risk levels: CRITICAL (score ≥ 100 or churn ≥ 15 with fix ratio ≥ 35%), HIGH (≥ 30 or churn ≥ 10 with fix ratio ≥ 25%), MEDIUM (≥ 10 or churn ≥ 10), LOW.
- Temporal coupling: requires minimum 3 co-commits and at least 25% coupling ratio for one of the pair.

## Team Health (`hotspot_team.py`)

`apps/engine/hotspot_team.py` answers the companion question — "is the team healthy?" — and feeds the `--team` flag. It is invoked automatically by `--write-wiki`, so the generated wiki page always carries the section.

- **Population parity (structural)**: `hotspots.py` hands its own parsed `CommitRecord` list to `analyze_team_from_commits`, so the team section cannot describe a different commit population than the hotspot table. Both analyses exclude merges (`--no-merges`) and share the same `--scope` pathspec; the two remaining reference passes (12-month velocity months, all-time author list) are scoped the same way.
- **Bus factor**: top human author's share of human commits; **FRAGILE** at ≥ 60%. Authors are keyed by email (`identity`), because one human commits here under two display names (`g-vega-cl` and `Cesar Vega` share one address) — keying on the display name split a single engineer into a 100% bus factor and a phantom departed contributor. Known limits: a missing `%ae` falls back to the display name (no merge possible), a shared team/CI address merges distinct humans, and a blank author renders as `unknown`. `[bot]`, `github-actions`, `actions-user`, `dependabot*`, and `renovate*` identities are excluded from the denominator; all-time authors with ≥ 3 commits and zero commits in the window are listed as *Inactive this window*.
- **Commit velocity**: commits per calendar month anchored to the requested 12-month window (`velocity_window`) and zero-filled through the current month, so a revived project shows its idle months instead of a three-month slice. Months before the window start are trimmed, and a `through` value earlier than the data never prepends leading zeros. Trend compares the last 3 months against the 3 before with a ±25% band (edge inclusive): `ACCELERATING`, `STEADY`, `DECELERATING`, or `INSUFFICIENT` under 6 months of history.
- **Crisis cadence**: `revert|hotfix|emergency|rollback` counts only when it is the commit **type** or the leading description word. Informational and work-kind types (`docs`, `test`, `style`, `chore`, `build`, `ci`, `feat`, `refactor`, `perf`) are exempt before any match, and a scope keyword never counts, so `docs(rollback):`, `feat(rollback):`, `chore(hotfix):`, `refactor: rollback handler cleanup`, `fix(rollback):`, `fix(newsletter): eliminate date rollback` and `feat: rollback support for migrations` are all non-crises. Remaining known false-positive class: a non-exempt type whose description opens with the keyword (`fix: emergency fund calc`). The rate divides by the requested window length in months (`window_months`, resolved from `--since` such as `90 days ago` or an ISO date; a free-form `--since` falls back to the observed span labeled *estimated from commits*, or *assumed* when nothing was observed): ≤ 0.5/month `STABLE`, ≤ 1.0 `WATCH`, above `ELEVATED`.
- **Graceful degradation**: a failed team pass (`CalledProcessError`, `OSError`, `ValueError`) logs `Team forensics skipped, git command failed` and still prints the hotspot report with the team section omitted.
- Git history is read with `%an`/`%ae`, because `git shortlog -sn` returns nothing on this repo (squashed/merged history hides authorship).

## Related

- [[concepts/code-hotspots]] — Detailed concept and usage guidelines
- [[entities/engine]] — Parent engine app directory
