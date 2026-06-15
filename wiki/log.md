## [2026-06-15] configuration | Git Union Merge for Wiki Logs

Configured Git union merge strategy for `wiki/log.md` and archived log files in `wiki/log/*.md` via `.gitattributes` to automatically resolve merge conflicts in multi-user/multi-agent setups. Documented this behavior and the fallback strategy in `wiki/SCHEMA.md`.

## [2026-06-14] feature | AI Sector Predictor and Model Arena

**Inference Loop**: Implemented weekly sector and uncorrelated-pair predictor tasks (`sector_predictor.py`) utilizing two competing models: **DeepSeek Flash** (via instructor proxy with markdown json format mode) and **MiniMax-M3** (via custom raw HTTP client).

**Auto-Research & Isolation**: Implemented a completely isolated meta-evolution task (`predictor_autoresearch.py`) executing against the `SECTOR_PREDICTOR_PROMPT` tag to prevent cross-experiment strategy dilution.

**Percentile Evaluation & TDD**: Implemented a mathematical percentile-ranking scoring module (`evaluate_predictions.py`) scoring single sector targets and uncorrelated pairs from 0 to 100 relative to the sector returns universe. Wrote pytest suite validating both prediction parsing and auto-research evolution.

**Front-End Comparison Dashboard**: Created `/ai-predictions` route with a custom D3 performance line chart, model scoring cards, and interactive logic reasoning history breakdown.

**See**: [[entities/sector-predictor-arena]], [[concepts/auto-research-prompt-improver]]

## [2026-06-14] optimization | Dynamic Liquid Glass Card Heatmap & Ellipsis Overflow Fix

**User Experience**: Shifted portfolio cards from a static single cyan border to a dynamic performance-based heatmap. Higher returns display gold/amber gradients and borders/glows, mid returns green, flat returns sky blue, and losses rose/deep crimson.

**Bug Fix**: Resolved browser-specific clashing styles where `truncate` on text containing both `-webkit-text-fill-color: transparent` and `bg-clip-text` resulted in invisible truncation ellipses. Shifted truncation behavior to an outer `overflow-hidden` wrapper.

**TDD & Testing**: Added robust assertions to `HomePage.test.tsx` verifying card border colors and box shadow styling correspond correctly to performance values, and verifying that the `truncate` class is not directly placed on the gradient headings. Passed all 235 Vitest tests.

**Wiki Updates**: Documented the clashing styles pitfall (`truncate` + `bg-clip-text`) and the dynamic card performance heatmap conventions in `entities/design-system.md`.
## [2026-06-01] refactor | Macro Volatility Pre-Calculation Caching — Database-Driven Architecture Shift

This refactor moves macro volatility calculations (daily % change, 30-day standard deviation, regime flags) from runtime computation in both the Python engine and TypeScript web loader into pre-calculated database columns persisted by the `update_prices.py` background script.

**Changes:**
- **Supabase Migration**: Added `today_pct_change`, `stdev_pct`, and `regime_flag` columns to `market_data_cache` (migration `20260601183000`).
- **TypeScript Types**: Regenerated Supabase types (`supabase-types.ts`) to include new columns, plus a new `prompt_experiments` table type and an `alpaca_filled_at` field on trades.
- **Python Macro Tracker**: Replaced dynamic `get_history()` calls and manual return/stdev computation with a single `.in()` query to `market_data_cache` for pre-calculated stats.
- **TypeScript Loader**: Eliminated the `price_history` table query entirely from the web loader (`fetch-today-data.ts`). Added a 30-second in-memory cache. Macro stats now map directly from `market_data_cache` rows with zero dynamic computation.
- **Tests**: Updated `test_macro_tracker.py` to mock the single cache query instead of quote/history chains. Updated `fetch-today-data.test.ts` to assert zero `price_history` queries and verify pre-calculated field mapping.
- **Design System**: Updated neutral color scheme variants for Button and Badge to use responsive `dark:`-prefixed high-contrast classes instead of hardcoded dark-only zinc values. Updated UI components (`GlobalMacroStats.tsx`, `TradeActivity.tsx`) to use responsive text contrast classes.
- **Performance Auditing Concept**: Added Database-Driven Pre-calculation as a core architectural principle in `concepts/performance-auditing-strategy.md`.
- **Macro Tracker Entity**: Documented the execution/scheduling of `update_prices.py` via GitHub Actions in `entities/macro-tracker.md`.

## [2026-06-02] optimization | Instant Pageview Analytics and Contrast Accessibility Compliance

Optimized the web application's initial client-side loading performance and resolved all core color contrast accessibility issues flagged in the Lighthouse audit:
- **Instant Client-Side PostHog Initialization**: Refactored the PostHog analytics integration in `__root.tsx` to pre-initialize the `posthog-js` SDK client-side only (within `typeof window !== 'undefined'`) immediately on JS parse. Passed this pre-initialized instance to `<PostHogProvider client={posthog}>` to eliminate double-mounting of router children. This guarantees **instant event capture and 100% reliable tracking of the initial pageview** upon load, while keeping the server-rendered HTML payloads completely free of dynamic tracking script tags to protect FCP and LCP scores.
- **Contrast Accessibility Compliance**:
  - Updated the design system's `--color-accent` token in `app.css` from `#3b82f6` (blue-500) to `#2563eb` (blue-600), achieving a compliant **4.56:1** contrast ratio with white text for solid buttons (LOGIN / MARKET) and links.
  - Adjusted `--color-accent-hover` to `#1d4ed8` (blue-700) to maintain hover contrast states.
  - Updated the "No activity found" text element in `TradeActivity.tsx` from `text-zinc-400 dark:text-zinc-500` to `text-zinc-500 dark:text-zinc-300`, guaranteeing AA-compliant contrast ratios in both light and dark themes.
- **TDD Regression Suite**:
  - Refactored `src/routes/-__root.test.tsx` to mock `posthog-js` directly and assert that the client-side pre-initialization is executed with `/p` as `api_host` and `disable_surveys: true` to prevent any JSDOM network attempts.
  - Verified 100% success on the full Vitest suite (208/208 tests passed) and completed a clean Biome and TypeScript typecheck build.
- **Living Synthesis**: Documented the pre-initialization pattern and its performance advantages in the canonical `concepts/performance-auditing-strategy.md` wiki page.

## [2026-06-02] optimization | Layout Optimization, SSR Fetch Limiting, and Background Hydration

Drastically improved server response times (TTFB), eliminated unused JavaScript penalties, and fixed hydration performance by embracing out-of-the-box data fetching patterns and eliminating unneeded DOM layout elements:
- **Reverted PostHog Initialization**: Reverted the immediate client-side `posthog.init()` approach back to the deferred `<PostHogProvider apiKey=...>` approach. The immediate initialization forced the massive `posthog-js` SDK into the critical `main.js` bundle, tanking Lighthouse scores due to unused JavaScript penalties. The declarative provider correctly lazy-loads the SDK out of the critical rendering path.
- **Layout Adjustments**: Omitted full feed counts from the Today layout, removing the requirement to fetch unbound arrays during initial load.
- **Strict SSR Fetch Limiting**: Added `.limit(5)` to all heavy feed queries (newsletters, trades, decisions, memories) in the TanStack Router SSR loader (`fetch-today-data.ts`), reducing the HTML payload from 748KB to a negligible size.
- **Seamless Background Hydration**: Replaced complex custom Intersection Observers and "Load More" buttons with native React Query behavior. Passed the SSR payload as `initialData` alongside a client-side `useQuery` executing with `.limit(50)`. With a default `staleTime: 0`, this achieves an instant First Contentful Paint followed by a seamless background refetch to lazy load the rest of the feed transparently.
- **Living Synthesis**: Documented the unified Data Fetching Philosophy and the Deferred SDK Initialization rule in `concepts/performance-auditing-strategy.md`.

## [2026-06-02] optimization | Consolidated Server Loader Fast Fetch Optimization Across Core Routes

Successfully scaled the Time-to-First-Byte (TTFB) optimization paradigm (Server Loader Fast Fetch) from the Today homepage to all core auxiliary pages:
- **Cause & Effect Refactor**: Upgraded the `fetchCauseAndEffect` API to accept pagination limits. Implemented a `limit: 5` constraint on the `createServerFn` loader inside `routes/cause-and-effect/index.tsx`, eliminating the massive unbounded database fetch on initial SSR render.
- **Memories N+1 Consolidation**: Refactored the heavy SSR data fetching block in `routes/memories/index.tsx` which previously fired 5 parallel unconstrained category queries (fetching 250 rows). By enforcing a `limit: 5` on the backend loader parameter, the SSR blocking payload was cut down to just 25 rows, accelerating first paint.
- **Reasoning Log Hydration Fix**: Addressed the complete lack of an SSR loader in `routes/reasoning/index.tsx`. By wrapping a `limit: 5` fast-fetch loader and injecting `initialData` directly into the `useInfiniteQuery` hook inside `ReasoningPage.tsx`, the page now achieves instant hydration without rendering a blocking spinner.
- **TDD Regression Tests**: Authored targeted unit tests for the core fetch APIs (`fetchCauseAndEffect`, `fetchMemories`, `fetchReasoningLogs`) and updated the `hydration.test.tsx` suite to assert that the `limit` query parameters are strictly applied by the Supabase client chain, preventing future regressions.

## [2026-06-02] optimization | Database RPC Traversal & Market Overview SSR Fast-Fetch

Optimized the performance of the `/market-overview` and `/memories/chain/{$memoryId}` routes to achieve sub-second edge TTFB:
- **Memories Chain RPC**: Pushed database migration `20260602140000_add_get_memory_chain_rpc.sql` introducing recursive CTE function `get_memory_chain` to retrieve memory ancestor/descendant structures in a single query. Updated the frontend router loader to query the RPC, reducing loading from 8 sequential queries down to 1.
- **Market Overview SSR Limiting**: Upgraded `fetchMarketOverviewData` to support a `limit` parameter and constrained the SSR loader to `limit: 5` for instant server rendering. Enabled `refetchOnMount: 'always'` to hydrate the full correlation matrix on client mount.
- **TDD Verification**: Added unit tests to `fetch-market-overview.test.ts` and `fetch-memories.test.ts` to assert correct parameter usage, passing all 214 web tests.

## [2026-06-02] optimization | Memory Chain RPC & Market Overview SSR Fast-Fetch

**Database**: Deployed `get_memory_chain` recursive CTE RPC function (migrations `20260602140000` and `20260602150000`) to resolve graph-traversal N+1 queries on the memory chain detail page. The frontend `/memories/chain/$memoryId` route now calls this RPC directly, reducing sequential database roundtrips from 8+ to 1.

**Market Overview SSR**: Added optional `limit` parameter to `fetchMarketOverviewData` and constrained the SSR loader to `.limit(5)` for instant initial render. Applied `refetchOnMount: 'always'` to hydrate the full correlation matrix client-side after mount.

**Web Route Updates**: `routes/market-overview/index.tsx` now passes `{ limit: 5 }` in the loader and `{ limit: undefined }` in the client fetch function. `routes/memories/chain/$memoryId.tsx` replaced the paginated `fetchMemories` loop with a single `fetchMemoryChain` call.

**Testing**: Verified with 214 passing web tests including new unit tests in `fetch-market-overview.test.ts` and `fetch-memories.test.ts` asserting correct RPC and limit parameter application.

**Wiki Updates**: Revised `memory-feedback.md` Event Chain Graph Traversal section to describe the new RPC-based architecture. Added Recursive DB RPC pattern to `performance-auditing-strategy.md`.

**See**: [[concepts/memory-feedback]], [[concepts/performance-auditing-strategy]]

## [2026-06-03] optimization | Zero-Date Server Date Pre-Formatting & Hydration Fix for Event Chains

Eliminated React hydration errors and layout paint delays on the `/memories/chain/$memoryId` route by shifting date formatting to the server-side loader:
- **Server Date Pre-Formatting**: Updated the server-only `buildChain` utility to pre-compute formatted timestamps using a new centralized helper `formatEasternDateTimeWithYear`.
- **Zero-Date View Rendering**: Refactored the frontend `EventChainPage` component to render static, pre-rendered date strings. This locks display timezone parity to Eastern Time (America/New_York) and avoids browser-specific narrow non-breaking space warnings.
- **TDD Regression Suite**: Authored a hydration regression test checking `EventChainPage` symmetry in JSDOM, guaranteeing zero future hydration mismatches.

**See**: [[concepts/memory-feedback]], [[concepts/performance-auditing-strategy]]

## [2026-06-03] optimization | Hybrid SSR Refactor & Background Hydration for Event Chains

Optimized page loading performance and TTFB on the `/memories/chain/$memoryId` route using a Hybrid SSR architecture:
- **Fast Focus-Node SSR**: Refactored `$memoryId.tsx` loader to fetch only the focus memory (1 database row) via a new `fetchMemoryById` query. The server returns a lightweight initial HTML payload immediately.
- **Seamless Background Hydration**: Configured `eventChainQueries.detail` with `staleTime: 0` to trigger a client-side background query on mount, rendering the remaining parent/descendant event chain recursively post-hydration.
- **Hydration Testing**: Added `fetchMemoryById` unit tests to `fetch-memories.test.ts` and added a new integration hydration test case in `hydration.test.tsx` verifying that the event chain page hydrates flawlessly from a single focus node state.

**See**: [[concepts/performance-auditing-strategy]]

## [2026-06-03] doc | Documented Rendering Strategies & Hybrid SSR Design Matrix

Created the canonical wiki concept page outlining the application's client/server rendering methodologies:
- **Rendering Strategies Concept**: Authored `rendering-strategies.md` detailing the Decision Matrix for selecting Full SSR vs. Hybrid SSR vs. No SSR (CSR).
- **Architecture Guidelines**: Documented the "limit & background hydration" design patterns using the homepage (`/`) and the newly optimized "Chain of Thought" page (`/memories/chain/$memoryId`) as core examples.
- **Related Updates**: Updated the wiki index catalog (`index.md`) and cross-linked from the Performance Auditing Strategy page (`performance-auditing-strategy.md`).

**See**: [[concepts/rendering-strategies]], [[concepts/performance-auditing-strategy]]

## [2026-06-03] fix | Scenario Analysis Metadata Persistence & Database Retroactive Repair

Resolved a critical metadata persistence bug where the structured `scenarios` array was omitted during memory creation in the consensus promotion loop:
- **Consensus Loop Fix**: Modified the `add_memory` metadata dictionary inside `apps/engine/analysis/consensus.py` to include the `"scenarios": consensus_data.get("scenarios")` field. This ensures that the structured JSON list containing clean headers, probability percentages, outcomes, trading plans, and scenario-specific FMP assets is correctly saved to the Supabase database.
- **TDD Regression Tests**: Updated the pytest integration suite `test_consensus_structured.py` to assert that `mock_add_memory` is called with the structured `"scenarios"` list in its `metadata` parameter. Verified that the updated tests pass cleanly.
- **Database Retroactive Repair**: Developed and executed a robust matching script (`fix_historical_memories_robust.py`) utilizing a word-overlap comparison algorithm to locate corresponding synthesis logs in the `llm_reasoning_logs` table. Reconstructed and patched the metadata for the 5 affected memories in the live Supabase database since the schema launch, fixing the empty Scenario Analysis panel on the dashboard.
- **Documentation**: Updated the [[concepts/memory-feedback]] and [[entities/web-app]] wiki documentation to detail the metadata persistence fix and the database repair.

**See**: [[concepts/memory-feedback]], [[entities/web-app]]

## [2026-06-04] doc | Documented Model Context Protocol (MCP) Setup & Plugin Lifecycle
 
Created the canonical wiki concept page outlining MCP server configurations, global settings, plugins, and caching:
- **MCP Setup Concept**: Authored `mcp-setup.md` detailing Workspace vs. Global MCP configurations, managing plugins via `agy plugin`, and clearing cached tool schemas.
- **Related Updates**: Updated the wiki index catalog (`index.md`) and uninstalled/deleted the cached Netlify MCP global files and plugins.
 
**See**: [[concepts/mcp-setup]]

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
