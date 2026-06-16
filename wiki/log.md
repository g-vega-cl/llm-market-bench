## [2026-06-04] feature | Local RAG MCP Server Implementation & Setup Documentation
 
Implemented a workspace-local Model Context Protocol (MCP) server package and updated setup documentation:
- **RAG MCP Package**: Implemented `@llm-market-bench/mcp-knowledge-rag` under `packages/mcp-knowledge-rag/` to query the external `misc` Supabase database and generate 768-dimension Gemini embeddings.
- **CLI Plugin Configuration**: Configured the package as an Antigravity CLI plugin using `plugin.json` and `mcp_config.json`. Successfully registered the server locally using the `agy plugin install` interface.
- **Workspace Configuration**: Added `.mcp.json` and `.ai/mcp/mcp.json` config files for automatic discovery in Claude Code and Opencode.
- **Documentation**: Updated the main README and the `mcp-setup.md` wiki concept page with installation/uninstallation guides for the custom local RAG server.
 
**See**: [[concepts/mcp-setup]], [README.md](file:///Users/cesarvega/Documents/p-code/llm-market-bench/README.md)

## [2026-06-04] feature | Local RAG MCP Server Package

Implemented a new workspace-local Model Context Protocol (MCP) server package `@llm-market-bench/mcp-knowledge-rag` under `packages/mcp-knowledge-rag/`. The server provides semantic search (RAG) against the external `misc` Supabase database using Gemini embeddings (768-dimension) and pgvector's `match_emails` RPC. Includes workspace configuration files (`.mcp.json`, `.ai/mcp/mcp.json`) for automatic discovery in Claude Code and Opencode, plus Antigravity CLI plugin support via `plugin.json` and `mcp_config.json`. Environment variables `MISC_SUPABASE_URL` and `MISC_SUPABASE_KEY` added to engine `.env.example`. Biome linting scope extended to cover the new package.

## [2026-06-06] bugfix | Add participating agents metadata to consensus events and remove frontend consensus meter

Fixed consensus cards agent display bug and cleaned up Today page UI:
- **Backend Metadata Fix**: Saved both `participating_agents` and `models_involved` (derived from unique models grouped semantically in consensus) to memory metadata dictionary in `apps/engine/analysis/consensus.py`.
- **TDD Regression Tests**: Added metadata assertion tests to `apps/engine/tests/test_consensus.py` checking that the models involved are persisted in the database memory metadata.
- **Frontend Meter Removal**: Removed the arbitrary and confusing "Consensus" percentage meter from `apps/web/src/features/today/components/AgentInsights.tsx` as requested. The presence of model icons on each card now directly indicates consensus.

## [2026-06-07] feature | Interactive Prompt Changes Diff View & Custom LCS Algorithm

Implemented an interactive, unified line-by-line diff section on the Auto-Research Arena details page to display the differences between an experiment's prompt and its parent prompt:
- **Custom LCS Line-Diff Algorithm**: Implemented a lightweight, zero-dependency Longest Common Subsequence line diffing utility in `apps/web/src/features/autoresearch/utils/diff.ts` and verified it with unit tests.
- **PromptChanges Component**: Created `PromptChanges.tsx` under `apps/web/src/features/autoresearch/components/` incorporating a unified diff display with line prefix indicators (+/-), color-coded backgrounds (emerald/rose/neutral), and a toggle to collapse/hide unchanged lines. Handles baseline prompts with a friendly callout.
- **Integration**: Linked the parent experiment to `ExperimentDetails` in `AutoresearchPage.tsx` and nested the new `PromptChanges` component above the trading prompt block.
- **TDD & Auditing**: Authored unit tests for both the utility and UI component, passing 100% of the test suite and resolving all Biome strict formatting and cognitive complexity rules.

## [2026-06-07] bugfix | Default Auto-Research Prompt Diff to Changes-Only & Improve Empty State

Refined the Prompt Changes comparison on the Auto-Research Arena page:
- **Default View Mode**: Changed `showChangesOnly` to default to `true` in `PromptChanges.tsx` so only actual modified lines are displayed initially, preventing the diff box from being visually redundant with the full prompt box below.
- **Dynamic Empty States**: Differentiated the no-parent scenario. Baseline prompts still show the `"Initial baseline prompt"` card, while other experiments missing a parent (e.g. older incremental variants) show a customized `"No parent prompt"` callout.
- **TDD Tests**: Updated `PromptChanges.test.tsx` to align test expectations with the new default collapsed view and to cover the new non-baseline missing-parent UI.

**See**: [[entities/autoresearch-arena]], [PromptChanges.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/autoresearch/components/PromptChanges.tsx)

## [2026-06-08] feature | Frozen System Constraints & Output Structure for Auto-Research

Frozen all core system constraints and JSON output schemas to prevent the auto-research prompt-improver from modifying or breaking them:
- **Refactored Prompts**: Split `CORE_ANALYSIS_SYSTEM_PROMPT` in [prompts.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/prompts.py) into three constants: `SYSTEM_PROMPT_CONSTRAINTS_HEADER` (persona, price mechanism, tool requirements), `SYSTEM_PROMPT_MUTABLE_STRATEGIES` (5 Whys, seasonal strategies, trading logic), and `SYSTEM_PROMPT_CONSTRAINTS_FOOTER` (SMA rules and JSON Output Format rules).
- **Prompt Splitter Utility**: Added a robust `split_prompt` function to extract the mutable strategy portion using exact and fuzzy matching.
- **Auto-Research Integration**: Updated [evaluator.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/autoresearch/evaluator.py) to extract and show only the mutable strategy section of the active and baseline prompts in the researcher report. Updated [runner.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/autoresearch/runner.py) to automatically recombine the proposed prompt text from the researcher with the frozen header and footer before saving the variant to the database.
- **LLM Instruction Update**: Updated [program.md](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/autoresearch/program.md) to instruct the meta-researcher that system constraints are managed automatically and it is only responsible for optimizing the strategy section.
- **TDD Tests**: Added `TestPromptConstraints` in [test_autoresearch.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_autoresearch.py) to assert exact and fuzzy prompt splitting. Passed 100% of tests.

**See**: [[concepts/auto-research-prompt-improver]], [prompts.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/prompts.py)

## [2026-06-08] feature | Frozen System Constraints & Output Structure for Auto-Research

Frozen all core system constraints and JSON output schemas to prevent the auto-research prompt-improver from modifying or breaking them:
- **Refactored Prompts**: Split `CORE_ANALYSIS_SYSTEM_PROMPT` in `prompts.py` into three constants: `SYSTEM_PROMPT_CONSTRAINTS_HEADER` (persona, price mechanism, tool requirements), `SYSTEM_PROMPT_MUTABLE_STRATEGIES` (5 Whys, seasonal strategies, trading logic), and `SYSTEM_PROMPT_CONSTRAINTS_FOOTER` (SMA rules and JSON Output Format rules).
- **Prompt Splitter Utility**: Added a robust `split_prompt` function to extract the mutable strategy portion using exact and fuzzy matching.
- **Auto-Research Integration**: Updated `evaluator.py` to extract and show only the mutable strategy section of the active and baseline prompts in the researcher report. Updated `runner.py` to automatically recombine the proposed prompt text from the researcher with the frozen header and footer before saving the variant to the database.
- **LLM Instruction Update**: Updated `program.md` to instruct the meta-researcher that system constraints are managed automatically and it is only responsible for optimizing the strategy section.
- **TDD Tests**: Added `TestPromptConstraints` in `test_autoresearch.py` to assert exact and fuzzy prompt splitting. Passed 100% of tests.

**See**: [[concepts/auto-research-prompt-improver]], [[concepts/system-heavy-prompt]]

## [2026-06-08] feature | Multi-Window Correlation & Trailing Returns

Added support for multiple correlation/trailing-return windows (7d, 30d, 60d, 90d) across the full stack:

- **Engine**: Extended `compute_correlation_matrices` and `compute_trailing_returns` to accept arbitrary window sizes. `store_correlation_results` now persists all four windows.
- **Database**: New migration adds 12 columns to `correlation_data` for 7d/30d/60d returns and correlations.
- **Web UI**: Added timeframe switcher to Market Overview (Current tab) and Correlation History Explorer. Data is mapped client-side. A disclaimer warns about noisy 7d correlations.
- **Tests**: New `TestMultiWindowCorrelation` class verifies windowed computation and alignment.

All existing wiki pages already reflect the new state; the correlation-matrix source page was updated inline with this commit.

## [2026-06-08] feature | Homepage routing scaffold & Today page migration

Moved the core "Today" dashboard from the root `/` route to its own `/today` route in `apps/web`. The root route (`/`) is now a placeholder `HomePage` component scaffolding ready for a planned UI redesign. Verified full route generation type safety and Tanstack navigation TDD tests.

## [2026-06-08] feature | Homepage routing scaffold & Today page migration

Moved the core "Today" dashboard from the root `/` route to its own `/today` route in the web app. The root route (`/`) is now a placeholder `HomePage` component with a welcome message, scaffolding for a planned UI redesign. The `Today` nav item now points to `/today` instead of `/`. Added TDD verification tests for the routing migration and updated route tree generation. Wiki pages already updated to reflect the new state.

## [2026-06-09] feature | HomePage dashboard with Liquid Glass design system

Implemented the full HomePage dashboard component with a "Liquid Glass" design system featuring dot grid backgrounds, ambient glowing orbs, and glassmorphism cards. The page displays:
- **S&P 500 Benchmark card** — visually distinct with yellow/gold styling, showing today and week performance
- **Individual portfolio cards** — per-LLM cards with equity, today P&L, active status, and auto-research badges
- **Market Feeling footer** — sentiment indicator with color-coded dot and summary text

Data is fetched server-side via `createServerFn` in the route loader, aggregating portfolio performance, benchmark history, and today's market feeling data. Portfolio names are cleaned from `ownerId` slugs (e.g., `org/Claude-3-Opus` → `Claude 3 Opus`). Added comprehensive test coverage for the dashboard rendering.

## [2026-06-10] feature | Background video with parallax scroll and SSR/CSR phased loading

Added `BackgroundVideo` component that uses a two-phase SSR/CSR strategy: server-side renders a fast static poster image (`data-testid="background-video"`), client-side hydrates to a hardware-accelerated `<video>` with parallax scroll effect via `requestAnimationFrame`. Uses permanent S3 URLs for video and poster assets. Integrated into `HomePage` as a fixed background layer behind the dot grid overlay. Removed the solid `bg-[#050914]` fallback since the poster now handles the initial paint. Test updated to verify `data-testid` presence.

## [2026-06-11] chore | Legacy PENDING trades migration completed; mobile layout fixes

Ran one-time migration script (`apps/engine/scripts/migrate_pending_trades.py`) to resolve all 33 remaining PENDING orders to terminal Alpaca statuses (32 filled, 1 canceled). Updated [[concepts/alpaca-order-sync]] with details. Also fixed mobile overflow in portfolio positions and trades tables by applying `min-width` to the inner table element instead of the container.

## [2026-06-12] feature | WebGL ShaderBackground component with 8 background variant themes

Added `ShaderBackground` React component using WebGL fragment shaders to render animated backgrounds on the HomePage. Supports 8 variants: pointillism, waves, nexus, cosmic, emerald_tide, royal_bronze, css_emerald, plus the original CSS dot grid (now selected via dropdown). Includes WebGL context loss/restore handling, visibility-change pausing, logical CSS pixel density mapping via `u_pixelRatio`, and pixel-ratio-aware canvas sizing. Resolved all Biome linter errors (non-null assertions and top-level React hook false-positives for WebGL methods). HomePage updated with a `<select>` dropdown to switch between variants in real time.

## [2026-06-12] feature | PostHog MCP server plugin

Added a local plugin wrapper (`packages/mcp-posthog/`) for the hosted PostHog MCP server, supporting both hosted SSE and personal API key authentication.- Integrated documentation in `concepts/mcp-setup.md` with step-by-step installation instructions for remote MCP servers.

## [2026-06-12] feature | HomePage Background A/B Testing via PostHog

Replaced the manual background dropdown selector on the HomePage with an automated, data-driven A/B test using PostHog feature flags.
- **Background Removal**: Stripped the unused `waves`, `nexus`, `cosmic`, and `emerald_tide` GLSL shaders from `ShaderBackground.tsx` to optimize the component bundle.
- **PostHog Integration**: Wired up the `homepage-bg-experiment` feature flag in `HomePage.tsx` via `@posthog/react`'s `usePostHog` to randomly assign users to one of 4 remaining variants (`css` [control], `css_emerald`, `pointillism`, `royal_bronze`).
- **Experiment Launch**: Deployed the experiment remotely via the PostHog MCP server with a perfectly distributed 25% rollout configuration.
- **TDD Safety Net**: Updated `HomePage.test.tsx` by mocking `@posthog/react` and verifying that the legacy manual dropdown is no longer rendered and the background is determined correctly by the feature flag.
- **Documentation**: Updated `entities/shader-background.md` and `index.md` to reflect the removal of the 4 unused variants and the transition to the A/B testing mechanism.

## [2026-06-13] new entity | Global Background component added

Introduced a `GlobalBackground` component in the design system's layouts. It provides a fixed dot grid and colored ambient orbs behind all pages. The HomePage was refactored to remove its previous A/B-tested background (CSS variant and ShaderBackground) and rely on this global layer. The component is rendered in the root layout, simplifying background management.

## [2026-06-13] refactor | Remove unused Badge dot variant and Card ghost variant

Removed `dot` variant from Badge primitive and `ghost` variant from Card primitive in the design system. Cleaned up related styles and conditional rendering. The Badge `showDot` prop remains for backward-compatible dot indicators. The Card ghost variant was removed as unused. Minor layout fixes applied to PortfoliosPage cards (h-full, flex, mt-auto) for equal-height card grid. Added unit test for card layout.

## [2026-06-14] feature | Volume & Liquidity Metrics in Price History

Enhanced the `get_price_history` tool to support Volume and Liquidity analysis directly within the LLM tool loop.
- **Execution Logic**: Modified `execute_price_history_tool` to output daily volume alongside historical prices and dynamically calculate Volume Context (ADV/RVOL) using the existing `compute_volume_context` engine function.
- **Prompt Engineering**: Updated the `PRICE_HISTORY_TOOL` JSON schema description to explicitly notify trading agents that volume data and metrics are available.
- **TDD Verification**: Authored `test_price_history_tool.py` to assert the inclusion of volume and context strings.
- **Documentation**: Updated `fundamental-analysis.md` to reflect the new volume analysis capabilities.

## [2026-06-15] refactor | Remove unused Badge dot variant and Card ghost variant

Removed `dot` variant from Badge primitive and `ghost` variant from Card primitive in the design system. Cleaned up related styles and conditional rendering. The Badge `showDot` prop remains for backward-compatible dot indicators. The Card ghost variant was removed as unused. Minor layout fixes applied to PortfoliosPage cards (h-full, flex, mt-auto) for equal-height card grid. Added unit test for card layout.

## [2026-06-15] enhancement | Enhanced Market Feeling Card with Confidence Bar, Concerns, and Metadata

- Added `MarketFeelingCard` component with `ConfidenceBar`, `ConcernsSection`, and `MetadataFooter` subcomponents.
- New `fetchLatestMarketFeeling` server function queries `market_feeling` table directly.
- Populated new fields: `sentimentLabel`, `sentimentEmoji`, `confidence`, `primaryConcern`, `secondaryConcern`, `modelUsed`, `lastAnalyzed`.
- Improved caching in `fetchTodayData`: cache bypass adjusted to compare against cached limit instead of hardcoded 50; exported `clearTodayDataCache` for testing.
- Routes updated to use `fetchLatestMarketFeeling` and `formatEasternTime`.
- Tests added for new market feeling flow and cache behavior.

## [2026-06-15] bugfix | Fix portfolio performance window truncation when a new portfolio starts

The `fetchAllActivePortfolioPerformance` function incorrectly used the most recent portfolio start date to trim the performance window, causing older portfolios' history to be clipped whenever a new portfolio was created on the current day. This was corrected to use the earliest start date across all active portfolios, preserving full historical data for each agent while still honoring the `maxDays` parameter. A regression test was added to prevent future regressions.

## [2026-06-15] bugfix | Fix portfolios page benchmark selection cache pollution

Resolved a bug where selecting alternative benchmarks (such as QQQ, GLD, TLT) in the portfolios comparison chart failed to display their respective performance lines:
- **React Query Cache Pollution**: Removed stale `initialData` parameter from `useSuspenseQuery` inside `PortfoliosPage.tsx` to stop old default ('SPY') benchmark data from seeding and freezing new query keys.
- **Smooth Suspense Transition**: Integrated `React.useTransition` to wrap `setSelectedBenchmark` updates, allowing client-side background refetching to transition smoothly without triggering hard-suspense loaders.
- **TDD Regression Suite**: Added `PortfoliosPageBenchmark.test.tsx` which simulates switching benchmark options and verifies the chart receives the correct dataset.
- **Documentation**: Documented this specific React Query `initialData` gotcha in `concepts/tanstack-query.md`.

**See**: [[concepts/tanstack-query]], [PortfoliosPage.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/portfolios/pages/PortfoliosPage.tsx)

## [2026-06-15] bugfix | Fix portfolios page benchmark selection cache pollution

Resolved a bug where selecting alternative benchmarks (such as QQQ, GLD, TLT) in the portfolios comparison chart failed to display their respective performance lines:
- **React Query Cache Pollution**: Removed stale `initialData` parameter from `useSuspenseQuery` inside `PortfoliosPage.tsx` to stop old default ('SPY') benchmark data from seeding and freezing new query keys.
- **Smooth Suspense Transition**: Integrated `React.useTransition` to wrap `setSelectedBenchmark` updates, allowing client-side background refetching to transition smoothly without triggering hard-suspense loaders.
- **TDD Regression Suite**: Added `PortfoliosPageBenchmark.test.tsx` which simulates switching benchmark options and verifies the chart receives the correct dataset.
- **Documentation**: Documented this specific React Query `initialData` gotcha in `concepts/tanstack-query.md`.

**See**: [[concepts/tanstack-query]], [PortfoliosPage.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/portfolios/pages/PortfoliosPage.tsx)

## [2026-06-15] fix | Eliminate benchmark switch flash and add D3 fade transition

Root-caused and fixed a visual flash in the portfolio comparison chart when switching the benchmark dropdown:

- **Root cause 1 — `key={selectedBenchmark}` on chart component**: React interpreted a different `key` as a different component and fully unmounted + remounted the `<PortfolioComparisonChart>` on every benchmark change, destroying the D3 SVG and all state. Removed the `key` prop; the chart's existing `useEffect([data, benchmarkData, selectedBenchmark])` already handles in-place re-draws correctly.
- **Root cause 2 — `useSuspenseQuery` without `placeholderData`**: When the query key changed (new benchmark), `useSuspenseQuery` suspended immediately (no cache hit), triggering the nearest Suspense fallback and blanking the chart area. Added `placeholderData: keepPreviousData` so the previous benchmark's cached data stays visible while the new fetch runs.
- **Smooth D3 animation**: Added a 350ms `easeQuadInOut` opacity fade-in transition to all chart paths (portfolio lines and benchmark line) on every D3 redraw. Combined with the two fixes above, switching benchmarks now produces a smooth animated handoff instead of a hard snap.
- **TDD regression guard**: Added a second test in `PortfoliosPageBenchmark.test.tsx` that captures the DOM node reference before a benchmark switch and asserts it is the exact same node after — a structural guarantee that no unmount/remount occurred.
- **Documentation**: Updated `concepts/tanstack-query.md` with the corrected `keepPreviousData` solution pattern and a new pitfall entry for the `key={dynamicValue}` anti-pattern. Updated `sources/web-portfolios-source.md` with a Smooth Benchmark Switching bullet.

**See**: [[concepts/tanstack-query]], [[sources/web-portfolios-source]], [PortfoliosPage.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/portfolios/pages/PortfoliosPage.tsx), [PortfolioComparisonChart.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/portfolios/components/PortfolioComparisonChart.tsx)

## [2026-06-16] fix | Hardcode ingest schedule to UTC for DST correctness

GitHub Actions does not correctly handle DST when using the `timezone` field — it treats `America/New_York` as always UTC-5. The ingest workflow schedule has been converted to explicit UTC times (13:35, 15:35, 19:00) to match the intended 9:35 AM, 11:35 AM, and 3:00 PM ET during EDT (UTC-4). This ensures the pipeline runs at the correct market hours year-round without relying on GitHub's broken DST support.

## [2026-06-16] documentation | Simplified pipeline wiki and hardcoded ingest schedule for DST

The `how-it-works.json` data source has been emptied, removing the detailed 7-phase breakdown from the web UI. The [[entities/pipeline]] wiki page has been condensed to a high-level 6-phase overview with UTC schedule details. The ingest workflow cron is now hardcoded to UTC to avoid GitHub Actions DST handling bug.

## [2026-06-16] refactor | Unified HomePage dashboard with table layout

Merged separate mobile/desktop views into a single responsive Dashboard component. Replaced portfolio cards with a compact table row layout, collapsed the market feeling analysis into a toggleable section, and removed the desktop-specific BenchmarkCard and MarketFeelingCard in favor of inline rows. Simplified the sentiment header and removed the background selector experiment logic.

## [2026-06-16] fix | MiniMax empty response and DeepSeek tool call narration anomalies

Resolved two critical LLM engine anomalies identified during the 2026-06-16 15:21 UTC ingest run audit:
- **MiniMax Empty Response & Tag Clash**: Stripped `<think>...</think>` reasoning blocks (including unclosed blocks) from the raw response content in `_analyze_with_minimax` before attempting JSON extraction, preventing parser clashes with internal thoughts. Coerced `None` response content to `""` to prevent attribute errors, and passed `response_format={"type": "json_object"}` to force valid JSON output.
- **DeepSeek Tool Call Narration**: Disabled `thinking` mode during the info-gathering tool execution loop (`run_tool_loop`) for DeepSeek to stop the reasoning model from narrating its planned tool calls in text instead of emitting structured API `tool_calls` objects.
- **DeepSeek Final Extraction Thinking**: Explicitly enabled `thinking` mode (`extra_body={"thinking": {"type": "enabled"}}`) in the final extraction phase inside `analyze_with_provider` so the model uses its full reasoning capacity to formulate the final trade decisions.
- **TDD Verification**: Created `test_reproduce_deepseek_minimax.py` reproducing the anomalies and verifying the fixes. Passed 100% of the 757-test suite.

**See**: [[concepts/model-anomalies]], [[concepts/tool-enforcement]], [analysis.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/analysis.py), [deepseek.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/handlers/deepseek.py), [test_reproduce_deepseek_minimax.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_reproduce_deepseek_minimax.py)

## [2026-06-16] fix | MiniMax empty response and DeepSeek tool call narration anomalies

Resolved two critical LLM engine anomalies identified during the 2026-06-16 15:21 UTC ingest run audit:
- **MiniMax Empty Response & Tag Clash**: Stripped ` thinking... response` reasoning blocks (including unclosed blocks) from the raw response content in `_analyze_with_minimax` before attempting JSON extraction, preventing parser clashes with internal thoughts. Coerced `None` response content to `""` to prevent attribute errors, and passed `response_format={"type": "json_object"}` to force valid JSON output.
- **DeepSeek Tool Call Narration**: Disabled `thinking` mode during the info-gathering tool execution loop (`run_tool_loop`) for DeepSeek to stop the reasoning model from narrating its planned tool calls in text instead of emitting structured API `tool_calls` objects.
- **DeepSeek Final Extraction Thinking**: Explicitly enabled `thinking` mode (`extra_body={"thinking": {"type": "enabled"}}`) in the final extraction phase inside `analyze_with_provider` so the model uses its full reasoning capacity to formulate the final trade decisions.
- **TDD Verification**: Created `test_reproduce_deepseek_minimax.py` reproducing the anomalies and verifying the fixes. Passed 100% of the 757-test suite.

**See**: [[concepts/model-anomalies]], [[concepts/tool-enforcement]]

