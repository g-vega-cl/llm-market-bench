---
tags: [agent, rules, mandates, workflow]
category: entity
---

# Agent Rules and Instructions

The canonical source of truth for agent behavior, instructions, and operational commands is `GEMINI.md` at the repository root. `AGENTS.md` acts as an entry pointer directing all coding assistants to `GEMINI.md`.

This wiki page documents the role of `GEMINI.md` in the system architecture and its relationship to other project guidelines.

## Role and Authority

Root `GEMINI.md` is injected directly into agent context during pair-programming sessions. Its mandates take absolute precedence over default system prompts or autonomous workflows. When instructions conflict, trust the code and repository-root `GEMINI.md`.

### Precedence Hierarchy

1. **`GEMINI.md`** takes absolute precedence over general assistant defaults and external docs.
2. **Wiki `SCHEMA.md` and `index.md`** govern documentation conventions.
3. **Repository code** takes precedence over general framework assumptions.

## Core Mandates Summary

The full operational requirements are maintained in root `GEMINI.md`. Key principles link directly to deeper wiki concepts:

1. **Search First (QMD)**: Query the wiki using `qmd` before writing code or answering design questions.
2. **Plan First**: Present visual terminal plans (`[[concepts/visual-planning]]`) and wait for explicit approval before changing code.
3. **TDD First**: Every plan requires a reproduction test first (`[[concepts/agent-workflow]]`).
4. **Code is Truth**: Validate claims against working code.
5. **Observability**: Use structured tracebacks over opaque error strings (`[[concepts/observability-standard]]`).
6. **Hotspot Awareness**: Inspect churn forensics before modifying high-risk files (`[[concepts/code-hotspots]]`).
7. **API Integration Sanity**: Enforce strict HTTP error handling and realistic financial values.
8. **Tool-First, Agency-Driven Architecture**: Expose callable tools rather than injecting massive context tables (`[[concepts/tool-first-agency]]`).
9. **Zero Compute on Frontend**: Pre-materialize all heavy calculations in background pipelines (`[[concepts/zero-frontend-compute]]`).
10. **Vertical Slice Islands & File Size Ceiling**: 400 LOC soft ceiling, 800 LOC hard limit, colocated tests (`[[concepts/vertical-slice-islands]]`).
11. **Design System & UI Consistency**: Strict primitive consumption from `@llm-market-bench/ui-design-system` with zero arbitrary utility escapes. **CSS-first architecture (avoid JS for design)**: all 1D and 2D layouts use declarative CSS Grid and Flexbox (`grid`, `flex`, `flex-wrap`, `items-stretch`); never use JavaScript (`window.innerWidth`, `matchMedia`, `ResizeObserver`) to compute column counts, dimensions, or responsive stacking modes, and never pass layout, typography, or color values through inline `style={{ ... }}` objects (only continuous dynamic data percentages, such as progress-bar fills, are permitted). **Zero floating tooltips or popovers**: never use floating tooltips, SVG `<title>` hovers, or popovers — secondary telemetry renders in-flow inside recessed `.voxel-trough` slots (`[[concepts/in-flow-inspection]]`). The single high-contrast dark theme is **Matcha & Cedar / Cheddar Boxel** — sharp `rounded-none` voxel geometry, 2px directional bevels, and recessed `.voxel-trough` slots (`[[entities/design-system]]`).
12. **Dependency Restraint**: Do not add new packages, dev dependencies, test runners, or lockfile changes without explicit user approval; prefer the standard library and tooling already in the repo.
13. **Targeted Git Staging & Multi-Agent Isolation**: Never blanket-stage; stage only the files touched by the active task (`[[entities/agent-rules]]`).
14. **Live Edge & Server Deployment Mandate (Build Implies Run)**: Committing or syncing files is not completion — edge services must be deployed, launched, and health-verified (`[[entities/secondary-minipc-edge]]`).

## Design Specification (Canonical)

The complete web design specification — CSS-first layout, fluent responsive design, parent-owns-spacing, the 3-combination typography budget, boxel geometry and palette tokens, information-density budgets, CLS prevention, overflow/text-wrapping rules, and the zero-floating-tooltip in-flow inspection rule — is codified in `.agents/rules/design-spec.md`. That file is the single source of truth for `apps/web` and `@llm-market-bench/ui-design-system` styling, and it supersedes the former standalone CSS-overflow rule file. Related wiki concepts: [[concepts/fluent-responsive-design]], [[concepts/in-flow-inspection]], [[concepts/cumulative-layout-shift]], [[entities/design-system]].

## Zero Floating Tooltips & Popovers (MANDATORY)

Section 10 of `.agents/rules/design-spec.md` bans floating tooltips, poppers, popovers, HTML `title` attributes, and SVG `<title>` hovers across the web app and design system. Floating elements obscure adjacent time-series or market data, cause visual jitter and layout flicker, fail on touch/mobile devices, and violate WCAG keyboard accessibility standards.

- **Mandatory pattern**: secondary telemetry, details, and point inspections render in-flow inside a dedicated recessed `.voxel-trough` slot, a contextual inspector bar, or a bottom drawer.
- **Keyboard operability**: interactive markers and data points carry `tabindex="0"`, `role="button"`, an `aria-label`, and `Enter`/`Space` handlers, and toggle the trough slot by click selection.
- **Design-time precedence**: agents must verify UI proposals against `.agents/rules/design-spec.md` before suggesting interaction models in `/plan` or `/grill-me`. Never propose banned UI patterns (tooltips, modals, accordions) during feature design or user interviews, and never treat legacy code snippets or external library conventions as design canon without cross-checking the spec.

See [[concepts/in-flow-inspection]] for the full rationale and implementation pattern.

## Git Staging & Commit Protocol (MANDATORY)

### Targeted Staging Only (Multi-Agent Safety)

- **Explicit File Staging**: Agents MUST only stage the exact files modified or created for their specific task (e.g. `git add path/to/file1.py path/to/file2.ts`).
- **Zero Blanket Staging**: Running `git add -A`, `git add .`, `git add -u`, or `git commit -a` / `git commit -am` is **STRICTLY PROHIBITED**.
- **Multi-Agent Isolation**: Multiple agents and human developers often work concurrently on the same branch. Blanket staging captures incomplete changes from sibling sessions, pollutes commit scopes, and causes pre-commit hooks to fail on unrelated dirty files.
- **Pre-Commit Verification**: Before committing, always check `git status --short` or `git diff --cached --stat` to confirm that only task-relevant changes are staged.

### Commit Message Validation

All commit messages are strictly validated by `.husky/commit-msg` via `apps/engine/commit_msg_lint.py`. Commits must follow Conventional Commits formatting; `feat`, `fix`, `perf`, and `refactor` commits must include a descriptive body explaining context and reasoning so the git log serves as a clear historical record (`[[entities/commit-msg-lint]]`).

## Live Edge & Server Deployment Mandate (Build Implies Run)

Whenever an agent builds, modifies, or fixes edge server services or configurations for the MiniPC or the primary workstation — including `live-spy-trader`, Nginx reverse proxy routes, `free-llm-proxy`, or database replicas — the work is **not** complete at a git commit or a file synchronization step.

Agents MUST:

1. **Deploy and launch immediately** — run the secondary edge deployment, which synchronizes files and automatically rebuilds/restarts containers in its `[5/5]` step:
   ```sh
   ./docker/archive/deploy_secondary.sh cv-minipc@minipc
   ```
2. **Verify health** — confirm health endpoints respond and inspect container logs after the restart.
3. **Never leave services dirty** — an unstarted, dirty, or crashed server service is a failed task. The operating assumption is that "people assume it's running when we commit or finish it."

See [[entities/secondary-minipc-edge]] for the edge topology and [[entities/live-agent-trader]] for the trader container that this mandate most frequently covers.

## Verification Gate

After every code change, lint and coverage must pass before work is marked complete. The pre-commit hook blocks commits with lint errors, low coverage, or broken wiki links:

- `ruff check` on changed Python files (`ruff check --fix` / `--unsafe-fixes` to auto-fix)
- `biome check` on changed TS files (`biome check --write` to auto-fix)
- `./apps/engine/.venv/bin/python3 apps/engine/wiki_lint.py` whenever any file in `wiki/` is created or modified
- All backtick code references in wiki markdown must match existing paths on disk

A passing test suite with failing lint or low coverage is not done.

## Related

- [[concepts/agent-workflow]]
- [[concepts/visual-planning]]
- [[concepts/code-hotspots]]
- [[concepts/vertical-slice-islands]]
- [[concepts/zero-frontend-compute]]
- [[entities/design-system]]
- [[concepts/fluent-responsive-design]]
- [[concepts/in-flow-inspection]]
- [[concepts/cumulative-layout-shift]]
- [[entities/commit-msg-lint]]
- [[concepts/wiki-synchronization]]
- [[entities/secondary-minipc-edge]]
- [[entities/live-agent-trader]]
