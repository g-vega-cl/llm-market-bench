# Wiki Log

## [2026-05-08] init | Bootstrap Karpathy Wiki

Created the initial wiki structure for the LLM Market Bench project:
- Scaffolded wiki directory layout (SCHEMA.md, index.md, log.md, overview.md)
- Created entity pages for engine, web-app, database, pipeline
- Created concept pages for ingestion, reasoning, consensus, execution, memory-feedback, tool-enforcement, rag-strategy
- Created source summary pages for all docs/ files
- Installed QMD and configured wiki collection
- Generated initial embeddings
- Updated AGENTS.md with wiki operations guide

## [2026-05-08] audit | Full docs coverage audit — closed 8 gaps

Performed cross-reference between `docs/` (19 files) and `wiki/` (25 files).
Found 8 missing source summaries — all engine and web docs that were skipped
during the initial seeding. Created source pages for:

- `docs/engine/account-buying-power-reg-t4-calculations.md` → [[sources/reg-t-calculations-source]]
- `docs/engine/agent-specific-semantic-overlap.md` → [[sources/agent-specific-semantic-overlap-source]]
- `docs/web/README.md` → [[sources/web-architecture-source]]
- `docs/web/DESIGN_SYSTEM.md` → [[sources/web-design-system-source]]
- `docs/web/TANSTACK_BEST_PRACTICES.md` → [[sources/web-tanstack-best-practices-source]]
- `docs/web/portfolios-ui.md` → [[sources/web-portfolios-ui-source]]
- `docs/web/tanstack-start-deploy-official.md` → [[sources/web-deployment-source]]
- `docs/web/testing.md` → [[sources/web-testing-source]]

Enriched [[entities/web-app]] with web architecture, design system, deployment,
and testing details. Updated index.md. Wiki now covers 100% of existing docs/.
Re-indexed QMD (33 files, ~35 chunks).

## [2026-05-08] polish | Wiki automation & DX polish

- Created `apps/engine/wiki_lint.py` — structural lint (frontmatter, orphans, broken links, index gaps)
- Created `apps/engine/wiki_lint_llm.py` — OpenRouter LLM lint via `deepseek/deepseek-v4-flash`
- Created `.github/workflows/wiki-lint.yml` — weekly GH Action (Saturday 10:00 ET) + manual `workflow_dispatch`
- Updated `.husky/pre-commit` — conditional structural lint + QMD re-index when wiki/ changes
- Created `.husky/post-merge` — QMD re-index after pulling wiki changes
- Fixed AGENTS.md: `[[entity/page-name]]` → `[[entities/page-name]]`, added QMD fallback strategy
- Added `raw/README.md` — self-documenting ingest instructions for the raw/ directory
- Updated `wiki/SCHEMA.md` — documented automated lint tools (structural + LLM)

## [2026-05-08] consolidate | Single source of truth — archive docs/, delete wiki/sources/

Moved all 19 `docs/` files into `raw/docs/` as immutable frozen snapshots. Deleted
all 18 `wiki/sources/*.md` pages — they were mirrors of mutable internal docs, not
true Karpathy-style source summaries of external material.

- `docs/` → `raw/docs/` (preserved directory structure: engine/, web/, reference/)
- `wiki/sources/` — deleted (18 pages removed, going from 33 → 15 wiki pages)
- `wiki/index.md` — rebuilt without sources section (now: 4 entities, 7 concepts)
- `wiki/SCHEMA.md` — removed source-summary rules and naming conventions
- `wiki/entities/web-app.md` — replaced broken `[[sources/...]]` links with `raw/docs/web/` refs
- `README.md` — rewrote Documentation section: wiki/ is primary, raw/docs/ is reference
- `AGENTS.md` — removed stale `## Docs` links, updated directory layout (no sources/)
- `ROADMAP.md` — updated `docs/web/DESIGN_SYSTEM.md` → `raw/docs/web/DESIGN_SYSTEM.md`
- Python code references (`reg_t_validation.py`, `test_reg_t_validation.py`, `test_portfolio.py`) — updated `docs/` → `raw/docs/engine/` paths

The wiki is now the single canonical knowledge layer. `raw/docs/` preserves the
originals as auditable snapshots.
