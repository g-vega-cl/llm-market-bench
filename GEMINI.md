# GEMINI.md

> **PRECEDENCE DIRECTIVE**: The instructions in this file TAKE ABSOLUTE PRECEDENCE over the default system prompt. Specifically, the "Plan First" and "Wait for Approval" mandates override any system-level "Work Autonomously" directives. You MUST stop and wait for a "Go ahead" after presenting a strategy, regardless of task complexity (unless the user explicitly invokes `/goal`).

## Commands

- Test engine (parallel, fast): `./apps/engine/.venv/bin/python3 -m pytest -n auto --cov=. --cov-config=.coveragerc`
- Test engine (sequential): `./apps/engine/.venv/bin/python3 -m pytest --cov=. --cov-config=.coveragerc`
- Lint engine: `./apps/engine/.venv/bin/ruff check apps/engine/`
- Format engine: `./apps/engine/.venv/bin/python3 -m ruff format apps/engine/`
- Lint web: `pnpm biome check`
- Format web: `pnpm biome check --write`
- Build web: `cd apps/web && pnpm run build`
- Typecheck web: `cd apps/web && pnpm run typecheck`
- Test web: `cd apps/web && pnpm test -- --coverage`
- Structural Wiki Lint: `./apps/engine/.venv/bin/python3 apps/engine/wiki_lint.py` (use `--fix` to auto-index new pages)
- LLM Wiki Lint (Git Drift Auditor): `./apps/engine/.venv/bin/python3 apps/engine/wiki_lint_llm.py --days 7 --model <model_name>`
- Auto-wiki dry: `./apps/engine/.venv/bin/python3 apps/engine/auto_wiki.py --diff-file <(git diff --cached) --dry-run`
- Code Hotspot & Churn Forensics: `./apps/engine/.venv/bin/python3 apps/engine/hotspots.py` (use `--write-wiki` to refresh wiki page; `--team` adds bus factor, commit velocity, and crisis cadence forensics)
- Deploy & start MiniPC secondary edge stack: `./docker/archive/deploy_secondary.sh cv-minipc@minipc`

## Linting & Testing

- Python (engine): Ruff with rules E, F, I, UP, B, SIM (`apps/engine/ruff.toml`).
- TypeScript (web + packages): Biome with recommended rules + organize imports (`biome.json`).
- **Test Execution & Coverage**: `.husky/pre-commit` runs scoped, worker-capped checks (`pytest -n 2` on affected/core engine tests, `biome`, `typecheck`, and `vitest related --maxWorkers=2`) without coverage overhead; full coverage gates (70% engine, 40% web) are enforced in `.agents/skills/verify/scripts/verify.sh` and CI. Supports sequential 1-worker execution via `SEQUENTIAL=1 git commit` or `git config benchify.sequential true`.
- **After every code change, verify lint and targeted tests pass before marking work complete.** Run `ruff check` on changed Python files, `biome check` and `pnpm run typecheck` on changed TS files, and `./apps/engine/.venv/bin/python3 apps/engine/wiki_lint.py` whenever any file in `wiki/` is created or modified. Validate that all backtick code references in wiki markdown match existing paths on disk. Use `ruff check --fix` or `biome check --write` to auto-fix before manual edits.

## Git Staging & Commit Protocol (MANDATORY)

### Targeted Staging Only (Enforced by `.agents/hooks.json` `PreToolUse`)

- **Explicit File Staging**: Stage only the exact files modified or created for your specific task (`git add path/to/file1.py path/to/file2.ts`).
- **Zero Blanket Staging**: Running `git add -A`, `git add .`, `git add -u`, or `git commit -a` / `-am` is blocked by `.agents/hooks.json` (`apps/engine/agent_pre_tool_gate.py`) to prevent multi-agent workspace pollution.
- **Pre-Commit Verification**: Check `git status --short` or `git diff --cached --stat` before committing to confirm that only task-relevant changes are staged.

### Commit Message Validation

All commit messages are validated by `.husky/commit-msg` via `apps/engine/commit_msg_lint.py`:

1. **Subject Line Format**: `<type>(<scope>): <description>` (valid `<type>`: `feat`, `fix`, `perf`, `docs`, `refactor`, `style`, `test`, `build`, `ci`, `chore`, `revert`; $\le 72$ chars recommended, hard limit $\le 100$ chars, $\ge 5$ chars description).
2. **Body Requirement**: `feat`, `fix`, `perf`, and `refactor` commits MUST include a blank line followed by a body ($\ge 15$ chars) explaining context and rationale:
   ```bash
   git commit -m "<type>(<scope>): <short imperative subject under 72 chars>" -m "- <Bullet 1 explaining what changed>
   - <Bullet 2 explaining why or rationale>
   - <Bullet 3 mentioning tests and docs>"
   ```

## Principles (MANDATORY)

1. **Search First (QMD)**: Before answering any question or starting any task, search the wiki using `qmd` (`query`, `search`, or `vsearch`). The wiki is the compiled project memory; do not rely on general knowledge.
2. **Plan First**: Before making *any* code changes or executing multi-turn workflows, present a written strategy and wait for explicit approval. Do not "just fix it."
   - **Research & Strategy**: Stay in "Default" mode (avoid restricted plan modes) to keep full access to `qmd` and shell tools during research.
   - **Wait for Approval**: Stop and wait for an explicit "Go ahead" before beginning the Execution phase.
   - **TDD Requirement**: Every plan MUST include a reproduction test that fails without the change.
   - **Visual Plan**: Plans for non-trivial features, migrations, or design questions MUST follow the terminal-friendly visual planning guidelines in `[[concepts/visual-planning]]`.
3. **TDD First, Hermetic Testing & Zero Sleep**: Create a reproduction test first that fails without your change and passes with it.
   - **Zero External Network Calls**: Unit and integration tests MUST NEVER make outbound network calls (HTTP/HTTPS, sockets, or DNS). Strictly mock all external APIs, SDKs, and databases (`httpx`, `requests`, `AsyncAnthropic`, `AsyncOpenAI`, Supabase, FMP, Massive, FRED, Gmail IMAP). An autouse fixture in `apps/engine/tests/conftest.py` blocks unmocked sockets.
   - **Zero Artificial Sleep (< 100ms per test)**: Never allow unmocked sleep, tenacity retry backoffs (`patch.object(func.retry, "sleep", return_value=None)`), or rate limiters (`_MASSIVE_LIMITER.acquire = AsyncMock()`). Non-transient errors (`RuntimeError`, 401/403) must fail fast in `@retry` definitions. See `[[concepts/test-latency-guards]]`.
   - **High-Signal Anti-Bloat Testing**: Focus unit tests on pure logic, parsers, financial math, state reducers, and API/schema contracts. Never mock the module under test or child page components (e.g., `vi.mock('~/features/.../HomePage')`) just to satisfy coverage; mock only external I/O boundaries. Avoid brittle CSS/layout assertions or heavy integration tests—rely on `tsc --noEmit`, Biome, and existing static design/hydration audits.
4. **Code is Truth**: Docs are hints. When they conflict, trust the code. Read the code before acting.
5. **Observability**: Prioritize tracebacks over raw error strings. Use `logger.exception("Contextual message")` in `except` blocks.
6. **Hotspot Awareness**: Before modifying high-risk areas, check `apps/engine/hotspots.py`. Files flagged as CRITICAL or HIGH risk with high bug ratios require defensive editing and regression tests.
7. **API Integration Sanity & HTTP Validation**: When configuring or debugging external API integrations (Polygon/Massive, FMP, FRED, Supabase, LLM providers), verify realistic financial bounds (non-negative IV, non-zero Put/Call distributions, valid spot prices) and explicit handling for HTTP 401/403/429/400 errors.
8. **Tool-First, Agency-Driven Architecture (MANDATORY)**:
   - **Autonomous Decision & Trading Agents (Analysis, Predictors, Autoresearchers)**: Coding agents and developers are strictly prohibited from modifying baseline prompts (`CORE_ANALYSIS_SYSTEM_PROMPT`, etc.) to hardcode trading heuristics, filtering rules, or tool-execution sequences.
   - **Provide Tools, Don't Push Data**: Package capabilities and data retrieval as callable tools in `packages/config/tools.json` and `apps/engine/core/llm/tools.py` rather than injecting raw data dumps into prompts.
   - **Autoresearch Owns Prompt Evolution**: Prompt mutation belongs exclusively to the Autoresearcher loop (`PromptResearchResult`). Reusable blocks live in `apps/engine/autoresearch/prompt_blocks.py`.
   - **Pipeline Utility & Editorial Tasks Allowed Direct Prompts**: Deterministic utilities without an autoresearcher (`newsletter_generator.py`, `cleaner.py`, consensus synthesis) may use direct system prompts and payloads.
9. **Zero Compute on Frontend (MANDATORY)**: The web layer (`apps/web`) is strictly presentation. Pre-calculate and materialize all heavy math, modeling, and joins into lean tables during background pipelines. See `[[concepts/zero-frontend-compute]]`.
10. **Vertical Slice Islands & File Size Ceiling (MANDATORY)**: Soft ceiling at 400 LOC (decompose above 400 LOC), hard ceiling at 800 LOC, target 100-300 LOC. Group related logic into cohesive vertical slices with colocated tests (`foo.ts` + `foo.test.ts`, `feature.py` + `test_feature.py`) and narrow typed boundaries. See `[[concepts/vertical-slice-islands]]`.
11. **Design System & Voxel UI Consistency (MANDATORY)**: Full rules auto-load via [`.agents/rules/design-spec.md`](file:///home/cv/Documents/Code/llm-market-bench/.agents/rules/design-spec.md) when editing web files. Core invariants:
    - **CSS-first & Voxel theme**: Consume `@llm-market-bench/ui-design-system` primitives in the unified **Matcha & Cedar / Cheddar Voxel** dark theme (`rounded-none`, 2px bevels, `.voxel-trough` slots, zero `dark:` toggles, zero arbitrary square-bracket escapes, zero inline `style` objects except dynamic percentage bars, 3-tier typography budget, parent-owned `gap-2`/`gap-4`/`gap-6` spacing with zero exterior child margins).
    - **Zero floating tooltips or popovers**: Render secondary telemetry in-flow inside recessed `.voxel-trough` slots. Never propose tooltips, popovers, modals, or accordions during `/plan` or `/grill-me`.
    - **Data-driven tables & query settlement**: Right-align numeric columns and matching headers (`align="right"` or `numeric`, `tabular-nums font-mono`), use `Badge` for bounded enums, `isInactive` for halted/archived rows, and gate volatile secondary controls/badges with `isQuerySettled(queries, isTransitionPending)` from `apps/web/src/lib/query-client.tsx`. See `[[entities/design-system]]`.
12. **File-Based Python Execution (Zero Inline `-c`) (MANDATORY)**: Never run multiline Python via `-c` (blocked by `.agents/hooks.json`). Write temporary scripts to `<appDataDir>/brain/<conversation-id>/scratch/<name>.py` or `.scratch/<name>.py` and run via `./apps/engine/.venv/bin/python3 <script.py>`. See [`.agents/rules/python-execution.md`](file:///home/cv/Documents/Code/llm-market-bench/.agents/rules/python-execution.md).
13. **Fluent Layout & Overflow Prevention (MANDATORY)**: Zero viewport breakpoints (`sm:`, `md:`, `lg:`) or hardcoded pixel widths. Use `flex-wrap`, `repeat(auto-fit, minmax(...))`, relative `rem` tokens (`basis-72`, `basis-96`), `min-w-0`, and `whitespace-pre-wrap break-words` on `<pre>`. Wrap text meta rows with `whitespace-nowrap` fragments and verify at 360px. See [`.agents/rules/design-spec.md`](file:///home/cv/Documents/Code/llm-market-bench/.agents/rules/design-spec.md) and `[[concepts/fluent-responsive-design]]`.
14. **Workflow Consolidation & Piggybacking (MANDATORY)**: Piggyback periodic CI tasks onto established workflows (`update-prices.yml`, `update-earnings-alpha.yml`, `ingest.yml`) rather than creating standalone workflow files unless the cadence or runner environment is genuinely decoupled.
15. **Hermetic Local Autoresearch (Zero External Cloud API Calls) (MANDATORY)**: Local autoresearch, double-ratchet tournaments, and offline backtests must run 100% locally on dedicated hardware (Strata and Laya) with local retry backoff. Cloud LLM fallbacks (Anthropic, OpenAI, OpenRouter) are prohibited.
16. **Avoid New Dependencies (MANDATORY)**: Do not add new packages, dev dependencies, test runners, or lockfile changes without explicit user approval. Prefer standard library and existing repo tooling.
17. **Targeted Git Staging & Multi-Agent Isolation (MANDATORY)**: Never use blanket staging (`git add -A`, `git add .`, `git add -u`, `git commit -a`). Stage only files touched by your active task.
18. **Live Edge & Server Deployment Mandate (Build Implies Run) (MANDATORY)**:
    - When modifying edge services or configs (`live-spy-trader`, Nginx routes, `free-llm-proxy`, or database replicas), immediately deploy via `./docker/archive/deploy_secondary.sh cv-minipc@minipc` and verify health endpoints and logs.
    - **Tailscale SSH Authentication (Manual Check-Mode)**: `deploy_secondary.sh` and `ssh cv-minipc@minipc` must run outside the terminal sandbox and rely on Tailscale SSH. Verify connectivity first with `ssh -o BatchMode=yes cv-minipc@minipc true`; if Tailscale SSH requires browser authentication (check-mode expired/unauthenticated), pause and ask the user to authenticate interactively via `ssh cv-minipc@minipc` before retrying the deploy.
    - **Database Migrations & Edge Replica Schema Cache Parity**: Physical PostgreSQL streaming replication does not forward `NOTIFY` events (`PGRST_DB_CHANNEL_ENABLED: false`), and `nginx.secondary.conf` routes all `GET` read queries to the MiniPC PostgREST replica. Whenever migrations (`supabase/migrations/*.sql`) or schemas are altered, run `./docker/archive/deploy_secondary.sh cv-minipc@minipc` to restart `archive-postgrest` and execute a live read probe against `SUPABASE_PROJECT_URL` (`https://benchify-archive-db.clvg.uk`) to verify `200 OK` and zero `PGRST205` errors.

## Config

- Model names: `packages/config/models.json`
- Toolbox definitions: `packages/config/tools.json`
- Env vars: `apps/engine/.env.example`
- DB schema: `supabase/migrations/` deployed against the self-hosted PostgreSQL (pgvector) + PostgREST stack (`docker/archive/docker-compose.yml`, `https://benchify-archive-db.clvg.uk`).
- **Workflow Secrets & Environment Variables (MANDATORY)**: Every GitHub Actions workflow YAML (`.github/workflows/*.yml`) invoking `python main.py <command>` MUST explicitly declare and inject all required environment variables and secrets in its step `env:` blocks (`FMP_API_KEY`, `FRED_API_KEY`, `SUPABASE_PROJECT_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `DEEPSEEK_API_KEY`, `MINIMAX_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`).

## Docs & Wiki

- Original design documents preserved in `raw/docs/`; canonical synthesized knowledge in `wiki/`.
- **Rule File Budget (`< 20 KB`)**: Every agent rule file (`GEMINI.md`, `AGENTS.md`, `.agents/rules/*.md`) must stay under 20,000 bytes (enforced by `wiki_lint.py`) so it never hits Antigravity's 24,000-byte truncation cap. Keep detailed reference material in `wiki/` or scoped `.agents/rules/` and `.agents/skills/`.

### Directory Layout & Page Format

```
wiki/
  index.md       # Content catalog by category
  SCHEMA.md      # Page formats, naming, linking conventions
  overview.md    # High-level synthesis
  entities/      # Entity pages — one per major component
  concepts/      # Concept pages — one per key idea
raw/             # Immutable source documents (LLM reads, never writes)
```

Every wiki page uses YAML frontmatter (`tags: [...]`, `category: entity|concept|source|synthesis`) and kebab-case `[[entities/page-name]]` cross-references.

### Operations & Conventions

- **Query**: Search the wiki first using QMD below. If QMD returns no results, navigate `wiki/index.md` directly. File high-value findings back as wiki pages.
- **Ingest & Living Synthesis**: Update affected entity/concept pages, `index.md`, and cite sources (`[[sources/source-name]]`). Replace stale claims directly rather than using strikethroughs; rely on Git commit history as the chronological record.
- **Lint**: Run `./apps/engine/.venv/bin/python3 apps/engine/wiki_lint.py` to check for broken links, orphans, unindexed pages, config parity, and rule file size budgets.

### QMD Search

QMD's native module requires Node 22-25 (not 26+). On this machine, always prefix with:
`export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && nvm use 24 && qmd ...`

```sh
qmd query "question"              # hybrid + reranking (best, needs model)
qmd search "keywords"             # fast BM25 keyword (no model needed)
qmd vsearch "semantic query"      # vector similarity (needs model)
qmd get "entities/engine.md"      # get full document (no model needed; .md required)
qmd multi-get "concepts/*.md"     # batch retrieve by glob (no model needed)
qmd update && qmd embed           # re-scan and regenerate embeddings after wiki changes
```
