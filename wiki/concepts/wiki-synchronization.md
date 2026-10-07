---
tags: [wiki, documentation, verification, workflow, maintenance]
category: concept
---

# Wiki Synchronization

The **Wiki Synchronization** mandate is the requirement that every code verification pass also brings the wiki back into agreement with the current codebase. It is enforced as the leading tier of the [[entities/verify-skill]] protocol and executed automatically by the verify runner script (`.agents/skills/verify/scripts/verify.sh`), so documentation drift is caught in the same pass that catches lint, type, and test regressions.

## Why It Exists

The wiki is the living truth of the project — pages must always reflect the present state of the codebase, never a past state. Without an explicit synchronization step, formula, scoring, model, tool, and architectural changes silently desynchronize the documentation from the code. The verify skill therefore treats documentation as a first-class verification surface rather than an afterthought.

## The Four Synchronization Actions

Every verify run performs four coordinated actions:

1. **Refresh code hotspots** — `apps/engine/hotspots.py --since "60 days ago" --top 15 --write-wiki` regenerates `wiki/concepts/code-hotspots.md` from live git churn and bug-fix forensics.
2. **Auto-index the catalog** — `apps/engine/wiki_lint.py --fix` indexes any newly created wiki pages into `wiki/index.md` and revalidates structural integrity (frontmatter, link targets, orphans, catalog coverage).
3. **Document behavior and rationale** — When code changes alter formulas, scoring, models, tools, or architectural patterns, the corresponding `wiki/concepts/` and `wiki/entities/` pages are updated with both the new behavior and the "why" behind it.
4. **Re-index semantic search** — `qmd update && qmd embed` regenerates QMD vector embeddings so knowledge remains discoverable via semantic search. This step is guarded by a `command -v qmd` availability check in the runner script.

## Enforcement Points

- **Verify skill protocol** (`.agents/skills/verify/SKILL.md`) — Tier 1 makes the synchronization steps mandatory alongside static hygiene and hotspot forensics.
- **Verify runner** (`.agents/skills/verify/scripts/verify.sh`) — executes the synchronization sequence before static checks; the `--hotspots` flag runs the hotspot refresh plus wiki write on its own.
- **Automated tests** (`apps/engine/tests/test_verify_skill.py`) — assert that `verify.sh` runs `wiki_lint.py --fix`, `hotspots.py --write-wiki`, `qmd update`, and `qmd embed`, and that both `SKILL.md` and [[entities/verify-skill]] describe the mandate.

## Related

- [[entities/verify-skill]] — the verification skill that carries the synchronization mandate
- [[entities/wiki-linter]] — the structural linter invoked with `--fix` to auto-index new pages
- [[entities/hotspots]] — the forensics script that rewrites the hotspots page
- [[concepts/code-hotspots]] — the regenerated living metrics page
- [[entities/auto-wiki]] — the agent that consumes these signals to update pages
