---
name: verify
description: Run an exhaustive verification protocol after coding to guarantee zero regressions, passing builds, hermetic test isolation, domain financial sanity, and strict architectural compliance.
---

# Code verification protocol

Use this skill after every coding round or when invoking `/verify` to audit changes against production standards before marking work complete.

## 1. Quick execution commands

Run the relevant checks for the modified surfaces:

```bash
# Static hygiene & bug hotspot forensics
./apps/engine/.venv/bin/ruff check apps/engine/
./apps/engine/.venv/bin/ruff format --check apps/engine/
pnpm biome check
./apps/engine/.venv/bin/python3 apps/engine/wiki_lint.py
./apps/engine/.venv/bin/python3 apps/engine/hotspots.py --since "60 days ago" --top 10

# Web types and build
cd apps/web && pnpm run typecheck
cd apps/web && pnpm run build

# Hermetic test suites with coverage
./apps/engine/.venv/bin/python3 -m pytest -n auto --cov=. --cov-config=.coveragerc
cd apps/web && pnpm test -- --coverage
```

Or run the bundled verification runner:

```bash
./.agents/skills/verify/scripts/verify.sh          # Full suite
./.agents/skills/verify/scripts/verify.sh --fast   # Lint, format, types, and wiki
./.agents/skills/verify/scripts/verify.sh --hotspots # Hotspot forensics & coupling
```

---

## 2. Verification tiers

Audit all changed files through these six tiers. Do not skip any tier.

### Tier 1. Static hygiene, size ceilings, and hotspot forensics

1. **Lint and format**:
   - Python: Ruff rules E, F, I, UP, B, SIM with zero warnings.
   - TypeScript: Biome checks pass with zero errors.
2. **File size ceilings** (Principle 10):
   - Soft ceiling: Under 400 lines of code. Extract sub-modules if exceeding 400 LOC.
   - Hard ceiling: Never exceed 800 lines.
3. **Colocated tests** (Principle 10):
   - Every modified module or component island must have its test sitting immediately next to it (`foo.py` with `test_foo.py`, `foo.tsx` with `foo.test.tsx`).
4. **Code bug hotspots and temporal coupling** (Principle 6):
   - Run `apps/engine/hotspots.py`. Check if any modified file is flagged as `CRITICAL` or `HIGH` risk (e.g., `daily_predictor.py`, `DailyPredictionsPage.tsx`, `market_data.py`, `tools.py`).
   - High fix-ratio files ($>25\%$) require defensive testing and narrow diffs. Avoid bundling speculative refactoring into fixes on these files.
   - Verify strongly coupled companions stay in sync:
     - `daily_predictor.py` $\leftrightarrow$ `test_daily_predictor.py`
     - `DailyPredictionsPage.tsx` $\leftrightarrow$ `DailyPredictionsPage.test.tsx`
     - `core/llm/tools.py` $\leftrightarrow$ `packages/config/tools.json` $\leftrightarrow$ `program.md` $\leftrightarrow$ `test_tools_consistency.py`
     - `researcher.py` $\leftrightarrow$ `handlers/base.py` $\leftrightarrow$ `tools.py`
     - `market_data.py` $\leftrightarrow$ `test_market_data.py`
5. **Wiki and documentation integrity**:
   - Run `./apps/engine/.venv/bin/python3 apps/engine/wiki_lint.py` whenever files in `wiki/` are added or modified.
   - **Root-relative paths in backticks**: Any backtick string starting with project prefixes (`apps/`, `packages/`, `scripts/`, `supabase/`, `wiki/`, `.github/`) must be an exact valid path from the repository root. Never use relative shorthand (e.g. `scripts/verify.sh` when the file is at `.agents/skills/verify/scripts/verify.sh`).
   - **Internal link resolution**: Every `[[page-name]]` cross-reference must resolve to an existing markdown page under `wiki/`.
   - **Catalog index parity**: Every new wiki page must be indexed in `wiki/index.md`. Run `apps/engine/wiki_lint.py --fix` to auto-index new pages.
   - **Config parity**: New models in `packages/config/models.json` and tools in `packages/config/tools.json` must be documented in the wiki.

### Tier 2. Build and type integrity

1. **TypeScript compilation**:
   - `pnpm run typecheck` passes with zero type errors.
   - No `any` escapes or unsafe type assertions on external API payloads.
2. **Web production build**:
   - `pnpm run build` succeeds without bundle errors or missing environment variable crashes.
3. **Subprocess execution safety**:
   - Python subprocess calls with compound commands (`&&`, `export`, pipes) must invoke bash or use file scripts. Never invoke compound commands directly without a shell wrapper.
   - Never run multiline inline `-c` commands. Use `.scratch/` scripts (Principle 12).
4. **CI workflow secret parity**:
   - If adding or updating environment variables or model providers in `apps/engine/core/config.py`, verify that every invoked GitHub Actions workflow in `.github/workflows/*.yml` explicitly injects them in its step `env:` blocks. Omitting keys causes CI runner failures.

### Tier 3. Hermetic testing and coverage

1. **Zero external network calls** (Principle 3):
   - Unit and integration tests must never connect to live sockets or make external DNS queries.
   - Mock all external interfaces (`httpx`, `requests`, Supabase, FMP, FRED, Alpaca, LLM clients).
2. **Ambient environment isolation**:
   - Tests must pass in a clean environment without relying on ambient environment variables (e.g., `FMP_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`).
3. **Coverage thresholds**:
   - Engine coverage must remain $\ge 70\%$.
   - Web coverage must remain $\ge 40\%$.
4. **TDD reproduction check**:
   - Bug fixes and new features must include a test that would fail without the change and passes with it.

### Tier 4. Domain, API, and financial invariants

1. **Financial and schema sanity** (Principle 7):
   - Realistic values: Bounds check implied volatility (non-negative), valid spot prices, valid option chain deltas, and non-zero Put/Call distributions.
   - Spot vs futures separation: Do not mix spot VIX with VIX futures ETFs.
2. **API error handling**:
   - Verify explicit handling for HTTP 401 (auth), 403 (tier forbidden), 429 (rate limits), and 400 (bad parameters).
   - Empty/weekend handling: Verify code handles zero rows or missing trading day data gracefully.
3. **Calendar, timezone, and schedule guards**:
   - Timezone localization: Never use naive `datetime.now()`. All market hours, calendar math, and predictor runs must explicitly use the `America/New_York` timezone.
   - Guard against non-trading days, weekends, holidays, and after-hours execution in daily predictor and trading pipelines.
4. **Trading order safety**:
   - Enforce trade idempotency on re-evaluations.
   - Enforce FIFO lot matching on positions.
   - Prevent accidental short positions when submitting exit SELL orders.
5. **Database migration RLS enforcement**:
   - Any new table created in `supabase/migrations/*.sql` must explicitly include `ALTER TABLE <table_name> ENABLE ROW LEVEL SECURITY;`.
6. **Tool definition parity**:
   - When introducing or altering tools, keep all four locations synchronized:
     1. `packages/config/tools.json`
     2. `apps/engine/core/llm/tools.py`
     3. `apps/engine/autoresearch/program.md`
     4. `apps/engine/tests/test_tools_consistency.py`

### Tier 5. Architecture, UI/UX, and design system

1. **Zero frontend compute** (Principle 9):
   - The web layer is presentation only.
   - Heavy aggregations, math, and multi-table joins must be computed in engine background pipelines and materialized in the database.
2. **Design system compliance** (Principle 11):
   - Strictly consume `@llm-market-bench/ui-design-system` components (`Button`, `Card`, `Badge`, `SectionHeading`, `Table`).
   - Zero arbitrary Tailwind values: Never use square-bracket escapes (`w-[240px]`, `bg-[#1a2b3c]`).
   - Prefer component props (`colorScheme`, `variant`, `size`, `radius`) over custom class overrides.
   - Single dark theme: Never introduce light/dark toggles or conditional `dark:` classes.
3. **Fluent responsive layout** (Principle 13):
   - No explicit media query breakpoints (`sm:`, `md:`, `lg:`).
   - Use CSS Grid `repeat(auto-fit, minmax(...))` and Flexbox `flex-wrap`.
   - Prevent overflow: Apply `min-w-0` on flex items and `whitespace-pre-wrap break-words` on preformatted blocks.
4. **Tool-first LLM architecture** (Principle 8):
   - For autonomous analysis and predictor agents, provide callable tools in `tools.json`. Do not bloat prompts with raw data dumps or hardcode trading heuristics into system prompts.

### Tier 6. Observability and error resilience

1. **Traceback preservation** (Principle 5):
   - In `except` blocks, log with `logger.exception("Context message")` instead of raw string logging or `print()`.
2. **No swallowed errors**:
   - Never write empty `except:` or `except Exception: pass` blocks without logging the traceback.

---

## 3. Verification report format

Conclude every verification run with a concise status report:

| Tier | Area | Result | Notes / Action Items |
| :--- | :--- | :--- | :--- |
| **Tier 1** | Static hygiene, LOC ceilings & hotspots | PASS / FAIL | Zero Ruff/Biome warnings; hotspot risk verified |
| **Tier 2** | Builds & types | PASS / FAIL | TypeScript and production build status |
| **Tier 3** | Hermetic tests & coverage | PASS / FAIL | Pytest / Vitest passing; coverage numbers |
| **Tier 4** | Domain & API sanity | PASS / FAIL | Financial bounds, schedule guards, tool parity |
| **Tier 5** | Architecture & UI/UX | PASS / FAIL | Zero frontend compute, design system, layout |
| **Tier 6** | Observability | PASS / FAIL | logger.exception used, zero swallowed exceptions |
