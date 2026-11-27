---
tags: [agent, workflow, worktrees, skills, tdd, governance]
category: concept
---

# Agentic Worktree Spine and 4-Layer Context

`llm-market-bench` standardizes Antigravity CLI (`agy`), Pi, and Hermes as interchangeable full-stack coding peers sharing one 4-layer progressive context architecture, one `.agents/skills/` spine, isolated git worktrees, and deterministic sensor-gated verification.

## 1. Progressive 4-Layer Context Layout

To avoid 18 KB per-turn prompt bloat and silent rule truncation while keeping Hermes and Pi subdirectory discovery active:

1. **Layer 1: Root Map (`AGENTS.md`, symlinked from `GEMINI.md`, `< 6 KB`)** — Defines the Plan-Gated Worktree Workflow, Ponytail Minimal-Code Ladder (delete > configure > stdlib/repo > small vertical slice), exact build/test commands, universal invariants, and `### QMD Search`. Legacy `.hermes.md`, `.pi/APPEND_SYSTEM.md`, `.claude/`, and `opencode.json` are removed so all three CLIs load progressive subdirectory rules cleanly.
2. **Layer 2: Scoped Domain & Product Rules** — `apps/engine/AGENTS.md` (import root hygiene, tool-first trading agents, local hermetic autoresearch, PostgREST `PGRST205` replica reload), `apps/web/AGENTS.md` (zero frontend compute, Voxel UI rules), `PRODUCT.md` ("show the receipts" anti-scammer proof positioning), and glob-triggered `.agents/rules/design-spec.md`.
3. **Layer 3: Unified `.agents/skills/` Catalog (symlinked to `.pi/skills/`)** — `/grill-me`, `wayfinder`, `/implement` (worktree TDD), `/qa` (live browser + Impeccable Voxel UI critique at 360px and desktop), `/verify` (8-tier verification + `.agents/reviewer-profiles.json` cold-context subagent review), `/ship` (`disable-model-invocation: true`), `qmd-wiki`, `last30days`, `unslop`, `code-hotspots`, `creative-ideation`, and `gemini-api-dev`.
4. **Layer 4: Compiled Memory & Reverse Code Graph** — `wiki/` queried on demand via `apps/engine/wiki_graph.py` and `apps/engine/wiki_lint.py` (`--affected-by`, `--topic-map`), exposed across all CLIs via `qmd` MCP in `.mcp.json` and `.pi/mcp.json`.

## 2. Plan-Gated Execution & Worktree Isolation

1. **Plan Sign-Off**: Every task presents a short visual terminal plan (`[[concepts/visual-planning]]`) with a failing TDD test case (inline in chat for localized bug fixes; `specs/<slug>/SPEC.md` for multi-file features, migrations, or trading/risk logic) and waits for explicit CLI or Telegram sign-off.
2. **Uninterrupted Worktree Run**: Once approved, `/implement` executes end-to-end inside `.worktrees/<slug>` without pausing on micro-decisions, guarded by `apps/engine/agent_pre_tool_gate.py` and `.pi/extensions/bench-gate.ts`.
3. **Hold Until `/ship`**: Verified worktree branches stay isolated until explicit `/ship` or PR merge, preventing unreviewed commits from triggering `docker/archive/watch_web_deploy.sh`.

## 3. Fedora Persistence & Fast Hooks

- `.husky/pre-commit` runs strictly fast deterministic checks (`apps/engine/secret_scanner.py`, Ruff, targeted pytest, Biome, `tsc`, Vitest, and structural `apps/engine/wiki_lint.py`), omitting slow LLM `auto-wiki` calls and GPU `qmd embed`.
- `scripts/install-fedora-agent-units.sh` provisions lingering `systemd --user` timers for stale lockfile cleanup (`scripts/worktree-janitor.sh`), background QMD indexing/embedding (`scripts/qmd-garden.sh`), and a persistent `tmux` PTY bridge (`scripts/pi-telegram-daemon.sh`) for `@llblab/pi-telegram`.

## Related

- [[entities/agent-rules]]
- [[entities/agent-pre-tool-gate]]
- [[entities/verify-skill]]
- [[entities/wiki-linter]]
- [[entities/free-llm-proxy]]
- [[concepts/qmd-wiki-skill]]
- [[concepts/visual-planning]]
