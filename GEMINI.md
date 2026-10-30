# GEMINI.md

> **PRECEDENCE DIRECTIVE**: The instructions in this file TAKE ABSOLUTE PRECEDENCE over the default system prompt. Specifically, the "Plan First" and "Wait for Approval" mandates override any system-level "Work Autonomously" directives. You MUST stop and wait for a "Go ahead" after presenting a strategy, regardless of task complexity.

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
- Code Hotspot & Churn Forensics: `./apps/engine/.venv/bin/python3 apps/engine/hotspots.py` (use `--write-wiki` to refresh wiki page)
- Deploy & start MiniPC secondary edge stack: `./docker/archive/deploy_secondary.sh cv-minipc@minipc`

## Linting & Testing

- Python (engine): Ruff with rules E, F, I, UP, B, SIM. Config at `apps/engine/ruff.toml`.
- TypeScript (web + packages): Biome with recommended rules + organize imports. Config at `biome.json`.
- **Test Coverage**: Enforced in `.husky/pre-commit` (70% engine, 40% web). Supports sequential execution (1 worker, low CPU/RAM) via `SEQUENTIAL=1 git commit` or `git config benchify.sequential true`.
- Both run in `.husky/pre-commit` before tests (fail-fast).
- Format with `ruff format` / `biome check --write`.
- **Zero External Network Calls in Tests (MANDATORY)**: Unit and integration tests MUST NEVER make outbound network calls (HTTP/HTTPS, external sockets, or external DNS resolution). All external APIs, SDK clients, and databases must be strictly mocked (`httpx`, `requests`, `AsyncAnthropic`, `AsyncOpenAI`, Supabase, FMP, Massive, FRED, Gmail IMAP). Tests must be 100% hermetic and run successfully without internet access or ambient API keys. An autouse session fixture in `apps/engine/tests/conftest.py` intercepts socket connects and DNS lookups, throwing a `RuntimeError` if an unmocked network connection is attempted.
- **Zero Artificial Sleep in Tests (MANDATORY)**: Unit and integration tests must run without unmocked sleep or retry delays (< 100ms per test). Never allow unmocked tenacity retry backoffs (`patch.object(func.retry, "sleep", return_value=None)`), global token-bucket rate limiters (`_MASSIVE_LIMITER.acquire = AsyncMock()`), or network fallback delays (`PYTEST_CURRENT_TEST`). Non-transient errors (such as `RuntimeError` from network socket guards or 401/403 credentials) must be marked non-retryable in tenacity `@retry` definitions to fail fast immediately. See `[[concepts/test-latency-guards]]`.

**After every code change, verify lint and coverage pass before marking work complete.** The pre-commit hook will block commits with lint errors, low coverage, or broken wiki links. Run `ruff check` on changed Python files, `biome check` on changed TS files, and `./apps/engine/.venv/bin/python3 apps/engine/wiki_lint.py` whenever any file in `wiki/` is created or modified. Validate that all backtick code references in wiki markdown match existing paths on disk. Use `ruff check --fix` / `ruff check --fix --unsafe-fixes` / `biome check --write` to auto-fix before resorting to manual edits. A passing test suite with failing lint or low coverage is not done.

## Git Staging & Commit Protocol (MANDATORY)

### Targeted Staging Only (Multi-Agent Safety)

- **Explicit File Staging**: Agents MUST only stage the exact files modified or created for their specific task (e.g. `git add path/to/file1.py path/to/file2.ts`).
- **Zero Blanket Staging**: Running `git add -A`, `git add .`, `git add -u`, or `git commit -a` / `git commit -am` is **STRICTLY PROHIBITED**.
- **Multi-Agent Isolation**: Multiple agents and human developers often work concurrently on the same branch. Blanket staging captures incomplete changes from sibling sessions, pollutes commit scopes, and causes pre-commit hooks to fail on unrelated dirty files.
- **Pre-Commit Verification**: Before committing, always check `git status --short` or `git diff --cached --stat` to confirm that only task-relevant changes are staged.

### Commit Message Validation

All commit messages are strictly validated by `.husky/commit-msg` via `apps/engine/commit_msg_lint.py`. When drafting or suggesting git commits:

1. **Subject Line Format**: `<type>(<scope>): <description>` (e.g. `feat(daily-predictor): pass daily newsletter to predictor`)
   - **Valid `<type>`**: `feat`, `fix`, `perf`, `docs`, `refactor`, `style`, `test`, `build`, `ci`, `chore`, `revert`.
   - **Subject Length**: Must be strictly $\le 72$ characters recommended (hard limit $\le 100$ characters, $\ge 5$ characters description).
2. **Body Requirement**:
   - Commits of type `feat`, `fix`, `perf`, and `refactor` **MUST include a body** ($\ge 15$ characters) explaining the context and changes.
   - Must contain a **blank line** between the subject and the body.
3. **Drafting Template**:
   ```bash
   git commit -m "<type>(<scope>): <short imperative subject under 72 chars>" -m "- <Bullet 1 explaining what changed>
   - <Bullet 2 explaining why or rationale>
   - <Bullet 3 mentioning tests and docs>"
   ```

## Principles (MANDATORY)

1. **Search First (QMD)**: Before answering any question or starting any task, YOU MUST search the wiki using `qmd` (query, search, or vsearch). The wiki is the "compiled" project memory; do not rely on general knowledge.
2. **Plan First**: Before making *any* code changes or executing multi-turn workflows, present a written strategy and wait for explicit approval. Do not "just fix it."
   - **Research & Strategy**: Stay in "Default" mode (avoid automated/restricted plan modes) to ensure full access to `qmd` and shell tools during research.
   - **Wait for Approval**: Stop and wait for an explicit "Go ahead" before beginning the Execution phase.
   - **TDD Requirement**: Every plan MUST include a reproduction test that fails without the change.
   - **Visual Plan**: Plans for non-trivial features, migrations, or design questions MUST follow the terminal-friendly visual planning guidelines defined in `[[concepts/visual-planning]]`.
3. **TDD First, Hermetic Testing & Zero Sleep**: Every implementation plan MUST include a step for creating a reproduction test first. Verification requires a test that fails without your change and passes with it. Tests must be 100% hermetic: **NEVER make live network calls or rely on ambient environment API keys**. Mock all external HTTP, SDK, and DB interfaces. Tests must never perform real-time sleeps or unmocked tenacity backoffs; fast-forward or mock all delay mechanisms so tests complete in milliseconds. See `[[concepts/test-latency-guards]]`.
4. **Code is Truth**: Docs are hints. When they conflict, trust the code. Read the code before acting — don't assume.
5. **Observability**: Prioritize tracebacks over raw error strings. Use `logger.exception("Contextual message")` in `except` blocks. This ensures the automated log audit system can perform root-cause analysis on failures.
6. **Hotspot Awareness**: Before modifying high-risk areas, check hotspots with `apps/engine/hotspots.py`. Files flagged as CRITICAL or HIGH risk with high bug ratios require defensive editing, regression tests, and verification before changes are made.
7. **API Integration Sanity & HTTP Validation**: When introducing, configuring, or debugging external API integrations (e.g. Polygon/Massive, FMP, FRED, Supabase, LLM providers):
   - Always verify that the live response contains **realistic, financially sound values** (e.g., bounds checking on IV, non-zero Put/Call distributions, correct spot prices).
   - Ensure **zero unhandled HTTP error codes** (e.g., 401/403 subscription tier blocks, 429 rate limit errors, 400 bad requests).
   - Never assume free-tier or default endpoint responses match paid schema assumptions without end-to-end dry runs and reproduction tests.
8. **Tool-First, Agency-Driven Architecture (MANDATORY)**:
   - **Autonomous Decision & Trading Agents (Analysis, Predictors, Autoresearchers)**: We let LLMs and Autoresearchers decide on their own prompts, trading hypotheses, and behavior. Coding agents and developers are **strictly prohibited from modifying baseline prompts** (`CORE_ANALYSIS_SYSTEM_PROMPT`, etc.) to hardcode trading heuristics, filtering rules, pre-audit checks, or tool-execution sequences.
   - **Provide Tools, Don't Push Data**: Rather than bloating prompts with massive pre-injected data tables (news text dumps, macro snapshots, ledger XML), capabilities and data retrieval MUST be packaged as callable tools in `packages/config/tools.json` and `apps/engine/core/llm/tools.py`. The agent is given lean context and decides autonomously *which* tools to invoke.
   - **Autoresearch Owns Prompt Evolution**: Prompt mutation belongs exclusively to the Autoresearcher loop (`PromptResearchResult`). Developers may define optional, reusable reasoning blocks in `apps/engine/autoresearch/prompt_blocks.py` for the Autoresearcher to test and adopt, but must NEVER bake them into baseline prompts.
   - **Pipeline Utility & Editorial Tasks Allowed Direct Prompts**: Deterministic production utilities without an autoresearcher (e.g. `newsletter_generator.py`, de-advertisement `cleaner.py`, consensus synthesis) are exempt from the tool-pull requirement. Developers are expected to directly engineer system prompts for editorial voice, markdown layouts, and schemas, and pass input payloads directly.
9. **Zero Compute on Frontend (MANDATORY)**: The web layer (`apps/web`) is strictly presentation. Never execute heavy calculations, mathematical modeling, multi-table joins, or bulk raw data fetches on web read paths. All derived intelligence must be pre-calculated and materialized into lean tables during background pipelines. See `[[concepts/zero-frontend-compute]]`.
10. **Vertical Slice Islands & File Size Ceiling (MANDATORY)**:
    - **Size limits**: Soft ceiling at 400 lines of code. Any file crossing 400 lines requires decomposition into sub-components or domain sub-modules. Hard ceiling at 800 lines to prevent tool viewport truncation and patch collision. Target size for modular units is 100 to 300 lines.
    - **Cohesive islands over micro-file fragmentation**: Group related logic, validation, and domain state into complete vertical slices. Avoid micro-file indirection chains (such as 10-line files spread across multiple directory layers) that degrade agent tool tracing.
    - **Colocated tests**: Every component or module island must have its test file sitting immediately next to it (`foo.ts` and `foo.test.ts`, or `feature.py` and `test_feature.py`).
    - **Isolated boundaries**: Keep island interfaces narrow, explicit, and typed. Avoid ambient global state. See `[[concepts/vertical-slice-islands]]`.
11. **Design System & UI Consistency (MANDATORY)**:
    - **Enforce UI design system**: All web UI components in `apps/web` must consume `@llm-market-bench/ui-design-system` primitives and patterns (`Button`, `Card`, `Badge`, `SectionHeading`, `Table`, etc.).
    - **Zero arbitrary values**: Never use square-bracket Tailwind escapes (such as `w-[230px]` or `bg-[#1a2b3c]`). Use established theme spacing, typography, and token classes.
    - **Prefer default system props**: Always use built-in props (`colorScheme`, `variant`, `size`, `radius`) to achieve styling rather than ad-hoc custom `className` utility overrides.
    - **Unified high-contrast dark theme**: The application standardizes on a single theme ("Bloomberg Terminal meets Wired"). Never introduce light/dark toggles, custom theme switches, or `dark:` conditional classes. See `[[entities/design-system]]`.
12. **File-Based Python Execution (Zero Inline `-c`) (MANDATORY)**: Never execute multiline Python via `-c`. Write temporary or diagnostic scripts to conversation scratch (`<appDataDir>/brain/<conversation-id>/scratch/<name>.py`) or workspace `.scratch/<name>.py` and run via `./apps/engine/.venv/bin/python3 <script.py>`. See [`.agents/rules/python-execution.md`](file:///home/cv/Documents/Code/llm-market-bench/.agents/rules/python-execution.md).
13. **Fluent Layout & Overflow Prevention (MANDATORY)**: Never use explicit media query breakpoints (`sm:`, `md:`, `lg:`) or raw pixel layouts. Use `flex-wrap`, `repeat(auto-fit, minmax(...))`, relative `rem` tokens (`basis-72`, `basis-96`), `min-w-0`, and `whitespace-pre-wrap break-words` on `<pre>` elements. See [`.agents/rules/css-overflow-prevention.md`](file:///home/cv/Documents/Code/llm-market-bench/.agents/rules/css-overflow-prevention.md) and `[[concepts/fluent-responsive-design]]`.
14. **Workflow Consolidation & Piggybacking (MANDATORY)**:
    - Never create standalone GitHub Actions workflow files for secondary or periodic tasks if an existing scheduled pipeline runs on the appropriate cadence (e.g., market close, price update, ingest).
    - Prefer "piggybacking" tasks into established workflows (`update-prices.yml`, `update-earnings-alpha.yml`, `ingest.yml`) as distinct steps or chained script calls.
    - Only introduce a new workflow file if the cadence, trigger event, or execution runner environment is genuinely decoupled and cannot be shared.
15. **Hermetic Local Autoresearch (Zero External Cloud API Calls) (MANDATORY)**:
    - During local autoresearch, double-ratchet tournaments, and offline backtests, calling external or cloud LLM APIs (Anthropic, OpenAI, OpenRouter Jev, etc.) is **STRICTLY PROHIBITED**.
    - Iterating across hundreds of trading sessions over multiple generations causes catastrophic API credit drain. All inference for distillation and decision classification must run 100% locally on dedicated hardware (Strata and Laya).
    - If a local server encounters transient engine stalls or reload cycles, pipelines must execute local retries with progressive backoff. Cloud fallbacks must remain disabled.
16. **Avoid New Dependencies (MANDATORY)**:
    - Do not add new packages (pip, pnpm/npm, or otherwise), dev dependencies, test runners, or lockfile changes without explicit user approval. This includes adding a test framework to a package that has none.
    - Prefer the standard library and tooling already in the repo. Reuse existing binaries and configs before introducing new ones.
    - If a new dependency seems necessary, state the reason and the lighter alternatives in the plan, and wait for approval before installing.
17. **Targeted Git Staging & Multi-Agent Isolation (MANDATORY)**:
    - Never use blanket staging commands (`git add -A`, `git add .`, `git add -u`, or `git commit -a` / `-am`).
    - Explicitly stage only files touched by your active task (`git add <file1> <file2>`).
    - When multiple agents or developers work on the same branch, blanket staging scoops up in-flight intermediate work from other sessions, corrupts change attribution, and breaks hermetic pre-commit gates.
18. **Live Edge & Server Deployment Mandate (Build Implies Run) (MANDATORY)**:
    - Whenever building, modifying, or fixing edge server services or configurations for the MiniPC or workstation (such as `live-spy-trader`, Nginx reverse proxy routes, `free-llm-proxy`, or database replicas), agents MUST NOT stop at git commits or file synchronization.
    - Agents MUST immediately deploy and launch the containers (e.g. via `./docker/archive/deploy_secondary.sh cv-minipc@minipc`, which synchronizes files and automatically rebuilds/restarts containers via step `[5/5]`), and verify health endpoints and logs.
    - Never leave server services in an unstarted, dirty, or crashed state: "people assume it's running when we commit or finish it."





## Config

- Model names: `packages/config/models.json`
- Toolbox definitions: `packages/config/tools.json`
- Env vars: `apps/engine/.env.example`
- DB schema: `supabase/migrations/`
- DB schema source of truth is version-controlled migrations in `supabase/migrations/` deployed against the self-hosted PostgreSQL (pgvector) + PostgREST stack (`docker/archive/docker-compose.yml`, `https://benchify-archive-db.clvg.uk`)
- **Workflow Secrets & Environment Variables (MANDATORY)**: Every GitHub Actions workflow YAML (`.github/workflows/*.yml`) invoking engine tasks (`python main.py <command>`) MUST explicitly declare and inject all required environment variables and secrets in its step `env:` blocks (e.g. `FMP_API_KEY`, `FRED_API_KEY`, `SUPABASE_PROJECT_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and model provider keys `DEEPSEEK_API_KEY`, `MINIMAX_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`). When adding, updating, or routing models/providers (e.g., in `packages/config/models.json` or `apps/engine/core/config.py`), you MUST ensure every corresponding workflow YAML includes its proper environment variables. Omitting keys like `FMP_API_KEY` in workflow YAMLs causes live data fetching and pre-market analysis to fail on CI runners.


## Docs

- Original design documents preserved in `raw/docs/`
- Canonical synthesized knowledge in `wiki/`

## Wiki

The project maintains a persistent wiki at `wiki/` — a structured, interlinked
collection of markdown files. The LLM writes and maintains it; the human reads
and curates sources.

### Directory Layout

```
wiki/
  index.md       # Content catalog by category
  SCHEMA.md      # Page formats, naming, linking conventions
  overview.md    # High-level synthesis
  entities/      # Entity pages — one per major component
  concepts/      # Concept pages — one per key idea
raw/             # Immutable source documents (LLM reads, never writes)
```

### Page Format

Every wiki page uses YAML frontmatter:

```yaml
---
tags: [tag1, tag2]
category: entity|concept|source|synthesis
---
```

Cross-references use `[[entities/page-name]]` style. Naming is kebab-case.

### Operations

**Ingest**: Read a source from `raw/` (or a web URL), discuss key takeaways
with the user, write/update the source summary page, update entity/concept
pages affected by the new information, update `index.md`, append to `log.md`.

**Query**: When answering questions, search the wiki first (using QMD below).
Synthesize answers with citations. Good answers should be filed back as new
wiki pages so knowledge compounds.

If QMD is unavailable or returns no results, fall back to navigating
`wiki/index.md` directly and reading relevant pages by path. Use
`wiki/index.md` as the table of contents — it lists every page with a
one-line summary.

**Lint**: Periodically health-check the wiki for contradictions between pages,
stale claims superseded by newer sources, orphan pages with no inbound links,
concepts mentioned but lacking their own page, and data gaps to investigate.

### QMD Search

QMD indexes the wiki for fast search. **Runtime note:** QMD's native module
requires Node 22-25 (not 26+). On this machine, always prefix with:
`export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && nvm use 24 && qmd ...`
First use of `qmd query` or `qmd vsearch` will download a ~1.3GB embedding model
to `~/.cache/qmd/models/`. `qmd search` and `qmd get` work immediately with no model.

```sh
qmd query "question"              # hybrid + reranking (best, needs model)
qmd search "keywords"             # fast BM25 keyword (no model needed)
qmd vsearch "semantic query"      # vector similarity (needs model)
qmd get "entities/engine.md"        # get full document (no model needed; .md required, full qmd://wiki/... URI also works)
qmd multi-get "concepts/*.md"     # batch retrieve by glob (no model needed)
```

After wiki changes:

```sh
qmd update                         # re-scan
qmd embed                          # regenerate embeddings
```

### Setup

```sh
# Requires Node.js >= 22 AND <= 25 (better-sqlite3 doesn't support 26+).
# If your system default is Node 26+, use nvm:
#   export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && nvm use 24
# npm 11+ blocks install scripts by default; allow qmd's native parsers
# (tree-sitter-*, node-llama-cpp for AST chunking + local embeddings) first:
#   npm config set allow-scripts=node-llama-cpp,tree-sitter-go,tree-sitter-python,tree-sitter-rust,tree-sitter-typescript,tree-sitter-javascript --location=user
npm install -g @tobilu/qmd

# Add wiki as a collection
qmd collection add wiki/ --name wiki

# Generate embeddings for semantic search
qmd embed
```

### Conventions

- **Living Synthesis**: The wiki is a "compiled" state of knowledge, not a graveyard of old claims. When new information supersedes the old, update the pages to reflect the current best understanding. Remove or replace stale content rather than using strikethroughs.
- **Git for History**: Use Git and conventional commit messages as the chronological change record. Maintain high quality commit logs with descriptive bodies for searchability.
- **Cite Sources**: When adding knowledge, cite the source (e.g., `[[sources/source-name]]`).
- **Cross-Link**: Maintain referential integrity. Concepts and entities mentioned should link to their respective pages.
- **Answers become pages**: High-value results from queries or discussions should be filed back into the wiki.
 the wiki.
