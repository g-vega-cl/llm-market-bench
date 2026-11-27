# AGENTS.md

> **PRECEDENCE DIRECTIVE**: This file is the canonical root instruction map for Antigravity CLI, Pi, and Hermes (`GEMINI.md` symlinks here). Its workflow and safety gates override default assistant behaviors.

## Plan-Gated Worktree Workflow (MANDATORY)

1. **Search First (QMD)**: Query the compiled wiki via QMD (`qmd` MCP or CLI below) before answering questions or planning code changes. When docs and code disagree, trust the code.
2. **Plan-Gated Sign-Off**: Never jump straight into editing code. Present a compact visual terminal plan (`[[concepts/visual-planning]]`) including a failing reproduction test case, then wait for explicit user approval on CLI or Telegram:
   - **Localized bug fixes**: Inline chat plan with exact files and failing test.
   - **Multi-file features, DB migrations, API contracts, or trading/risk logic**: Write a 1-page `specs/<task>/SPEC.md` with mechanical acceptance criteria, permitted paths, and verification commands.
3. **Uninterrupted Worktree Execution**: Once the user approves the plan, execute end-to-end inside an isolated git worktree (`.worktrees/<slug>`, via `/implement`) without stopping on routine sub-steps: Red test -> Green minimal code -> Refactor -> `/verify` + cold reviewer subagent.
4. **Hold Until `/ship`**: Leave verified worktree branches ready and report completion. Do not merge/push to `main` or trigger production deploys until the user explicitly runs `/ship` or merges a PR. Pause mid-run only on unapproved Red-Line events (unexpected DB migrations, protected evaluator edits, missing credentials, or a 2-round verification stall).

## Minimal-Code Ladder (Ponytail Discipline)

Climb this ladder in order before writing new abstractions:
1. **Delete or simplify**: Can dead code, duplicate state, or boolean flag sprawl (`[[concepts/state-machines]]`) be removed instead?
2. **Configure**: Can an existing PostgREST query, SQL constraint, Tailwind utility, or JSON config solve it?
3. **Reuse stdlib & repo modules**: Prefer Python/Node standard library and existing `packages/*` or `apps/engine/core/*` helpers. Never add packages or lockfile entries without explicit user approval.
4. **Write small vertical slices**: Soft ceiling 400 LOC, hard ceiling 800 LOC, target 100-300 LOC with colocated tests (`foo.py` + `test_foo.py`, `foo.tsx` + `foo.test.tsx`; see `[[concepts/vertical-slice-islands]]`).

## Commands

- Engine tests (4 workers): `cd apps/engine && ./.venv/bin/python3 -m pytest -n 4 --cov=. --cov-config=.coveragerc` (omit `-n 4` for sequential low-RAM mode)
- Engine lint & format: `./apps/engine/.venv/bin/ruff check apps/engine/ && ./apps/engine/.venv/bin/ruff format --check apps/engine/`
- Web lint, types & build: `pnpm biome check && pnpm --filter web typecheck && pnpm build:web`
- Web tests: `cd apps/web && pnpm test --maxWorkers=4 --coverage`
- Wiki structural & graph lint: `./apps/engine/.venv/bin/python3 apps/engine/wiki_lint.py` (`--fix` auto-indexes; `--affected-by <file>` lists impacted wiki pages; `--topic-map` prints subsystem reverse map)
- Code hotspots: `./apps/engine/.venv/bin/python3 apps/engine/hotspots.py --since "60 days ago" --top 15`
- Full verification suite: `./.agents/skills/verify/scripts/verify.sh` (`--fast`, `--engine`, `--web`, `--sequential`)
- Secondary MiniPC deploy: `./docker/archive/deploy_secondary.sh cv-minipc@minipc`

## Universal Invariants

- **Hermetic TDD & Zero Sleep**: Write a failing test first. Unit/integration tests must run in `< 100ms` with zero outbound network/DNS (`conftest.py` blocks sockets) and zero unmocked sleep or retry backoff (`[[concepts/test-latency-guards]]`). Mock external I/O boundaries only, never the module under test.
- **Observability**: Log tracebacks with `logger.exception("Context")` in `except` blocks; never swallow exceptions silently.
- **Targeted Git Staging & Commits**: Stage only task-specific files (`git add path/a path/b`). Blanket staging (`git add .`, `-A`, `-u`, `git commit -a`), `--no-verify`, and `git push --force` are blocked by user-space guardrails (`apps/engine/agent_pre_tool_gate.py`). Commit format: `<type>(<scope>): <subject>` (`<= 72` chars), plus a blank line and body (`>= 15` chars) for `feat`, `fix`, `perf`, and `refactor`.
- **File-Based Python Execution**: Never run multiline `python3 -c`. Write temporary scripts to `.scratch/<name>.py` and run `./apps/engine/.venv/bin/python3 .scratch/<name>.py` (`.agents/rules/python-execution.md`).
- **Core Web Vitals**: Enforce p75 `LCP <= 2.5s`, `INP <= 200ms`, and `CLS <= 0.1` (`https://web.dev/articles/vitals`) with 3-tier JS loading and layout-matched `Skeleton` states (`[[concepts/core-web-vitals]]`).
- **Live Edge & Replica Parity**: Changes to `free-llm-proxy`, `live-spy-trader`, Nginx configs, or `supabase/migrations/*.sql` require `./docker/archive/deploy_secondary.sh cv-minipc@minipc` and a `200 OK` PostgREST read probe during `/ship`.
- **Rule Budget**: Keep root and `.agents/rules/*.md` files under 20,000 bytes (enforced by `wiki_lint.py`).

## Progressive Context & Skills Map

- **Engine domain rules**: `apps/engine/AGENTS.md` (tool-first trading agents, local autoresearch, financial/API bounds, PostgREST replica parity)
- **Web & UI domain rules**: `apps/web/AGENTS.md`, `PRODUCT.md` ("show the receipts" soul), and `.agents/rules/design-spec.md` (Matcha & Cedar / Cheddar Voxel UI)
- **Shared skills (`.agents/skills/`)**: `/grill-me` (Socratic design interview), `wayfinder` (multi-session issue maps), `/implement` (worktree TDD), `/qa` (live browser + Voxel UI audit), `/verify` (8-tier audit + cold reviewer), `/ship` (manual merge/deploy gate), `qmd-wiki`, `last30days`, `unslop`, `code-hotspots`
- **Config & Memory**: `packages/config/models.json`, `packages/config/tools.json`, `wiki/index.md` (`wiki_lint.py --topic-map` for on-demand code-to-wiki reverse map)

### QMD Search

Prefer the `qmd` MCP server (`mcp__qmd__query` with `lex` first, then `mcp__qmd__get`). Shell fallback under Node 24:
```sh
export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && nvm use 24
qmd search "keywords" -c wiki -n 10
qmd get "entities/engine.md"
```
