## [2026-06-19] feature | Resolved memories linking and performance playbook integration

Resolved a gap in the memories feedback loop by linking resolved events with their resolutions and cause-and-effect outcomes in the frontend Memories dashboard:
- **Child Resolution Traversal**: Implemented `fetchChildResolutionEvent` to locate child memory items linked via `parent_id` and `relationship_type = 'RESOLUTION'`.
- **Cause-and-Effect Aggregation**: Created `fetchCauseAndEffectByEventId` and updated the `MemoryCard.tsx` component to fetch and merge outcome data from both the parent resolved event and the child resolution event.
- **Consolidated UI Panel**: Designed and integrated the "Resolution & Market Performance" panel, rendering a link to the resolution event's timeline, actual price performance results, confidence level, the LLM's causal playbook analysis, and associated topic tags.
- **Documentation & TDD**: Added test coverage verifying the integrated queries and elements in `MemoryCard.test.tsx` and resolved tab-switching list query conflicts in `MemoriesList.test.tsx`. Documented the loop mechanics on the `memory-feedback.md` concept page.

**See**: [[concepts/memory-feedback]], [MemoryCard.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/memories/components/MemoryCard.tsx), [MemoryCard.test.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/memories/components/MemoryCard.test.tsx), [MemoriesList.test.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/memories/components/MemoriesList.test.tsx)

## [2026-06-18] feature | Seed empirical market anomalies database and document in wiki

Expanded the core empirical database and documentation with 9 structural, calendar, and behavioral market anomalies, plus the Fama-French 5-Factor asset pricing model:
- **Database Expansion**: Updated `seed_academic_papers.py` to seed 10 new high-importance, non-decaying `ACADEMIC_PAPER` memories into Supabase (`The Overnight Return Anomaly`, `The Turn-of-the-Month Effect`, `The Pre-Holiday Liquidity Vacuum`, `The January Effect`, `The Weekend Effect`, `Post-Earnings-Announcement Drift`, `Pre-FOMC Announcement Drift`, `The Index Inclusion Effect`, `Options Expiration Pinning`, and `A Five-Factor Asset Pricing Model`).
- **Seeder Execution**: Ran the seeding script successfully, adding the 10 new papers to the active database.
- **Academic Paper Seeding Test**: Updated the test suite `test_seed_academic_papers.py` to dynamically assert the size of the seeded collection (now 20 papers total).
- **Concept Page**: Added `wiki/concepts/market-anomalies.md` documenting the phenomena, mechanisms, reference papers, and actionable trading agent applications.
- **Documentation Update**: Refactored `wiki/entities/academic-paper-seeding.md` to update paper counts and align classification under the first-class `ACADEMIC_PAPER` memory type rather than the old `LESSON_LEARNED` mapping.
- **Index Reference**: Linked the new page in `wiki/index.md`.

**See**: [[concepts/market-anomalies]], [[entities/academic-paper-seeding]], [seed_academic_papers.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/scripts/seed_academic_papers.py), [test_seed_academic_papers.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_seed_academic_papers.py)

## [2026-06-18] bugfix | Add loading indicator to Event Chain Explorer page

Introduced a loading indicator and timeline loading cards to `EventChainPage` to notify the user that other memories in the chain are being fetched in the background:
- **Background Refetch Detection**: Destructured `isFetching` from the `useSuspenseQuery` hook.
- **Stale Cache Forcing**: Added `initialDataUpdatedAt: 0` to query options to force TanStack Query to immediately refetch the event chain on client mount, updating the single-item server-rendered page.
- **Inline Loading Badge**: Added a loading badge with a spinner next to the page subtitle when `isFetching` is true.
- **Placeholder Card**: Added a dashed placeholder loading card at the bottom of the timeline if `chain.length === 1 && isFetching` is true, indicating other memories in the chain are loading.
- **TDD Verification**: Created `EventChainPage.test.tsx` verifying that the loading indicators appear during active fetches and disappear when query resolution finishes.

**See**: [[entities/web-app]], [EventChainPage.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/memories/pages/EventChainPage.tsx), [EventChainPage.test.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/memories/pages/EventChainPage.test.tsx)

## [2026-06-18] bugfix | Hide "Other Investable Assets" section when remaining assets is empty

Resolved a UI rendering issue in `MemoryCard.tsx` where an empty "Other Investable Assets" section containing a confusing static placeholder was rendered for newly generated events:
- **Conditional Visibility**: Updated the rendering logic to only show the "Other Investable Assets" container if there are unmapped assets (`remainingAssets.length > 0`).
- **Cleaned Up Placeholder**: Removed the redundant empty/fallback placeholder branch to keep the layout concise.
- **TDD Regression Guard**: Created a Vitest test case verifying that the section hides when all discovered assets are successfully mapped directly to structured scenarios, even if the legacy metadata contains the text `"Investable Assets"`.

**See**: [[concepts/memory-feedback]], [MemoryCard.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/memories/components/MemoryCard.tsx), [MemoryCard.test.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/memories/components/MemoryCard.test.tsx)

## [2026-06-18] feature | Link Concept Tracker Table inline expansion to relevant memories and event chains

Enhanced the interactive Concept Tracker table on the `/concepts` page to fetch and display semantically related memories and raw sources when a row is expanded:
- **On-Demand Vector Query**: Implemented `fetchConceptMemories` to fetch the concept's vector and call `match_memories` RPC on Supabase, retrieving the top 5 most similar memories.
- **Rich Memory Cards**: Rendered matched memories inside the expanded details panel showing matching similarity percentage, sentiment impact badge (`BULLISH` / `BEARISH` / `NEUTRAL`), and full content.
- **Dynamic Event Chain Navigation**: Linked each memory card to its respective event chain explorer page (`/memories/chain/$memoryId`), establishing a bidirectional navigation trail between trending concepts and historical cognitive memories.
- **Type Safety & TDD**: Consolidated typescript type-safety for nested JSONB metadata, wrapped Vitest RTL tests in a custom `QueryClientProvider`, and added assertions to verify loading state, memory content rendering, and navigation link correctness.

**See**: [[entities/web-app]], [ConceptMap.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/concepts/components/ConceptMap.tsx), [ConceptMap.test.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/concepts/components/ConceptMap.test.tsx), [fetch-concepts.ts](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/concepts/api/fetch-concepts.ts)

## [2026-06-18] feature | Replace D3 PCA Concept Map with Interactive Concept Tracker Table

Refactored the complex and unintuitive D3-based PCA concept map visualization on the `/concepts` page into an interactive, high-fidelity tabbed table:
- **Interactive Tabs**: Implemented three sorting modes: "Trending" (momentum velocity), "Most Mentioned" (citation counts), and "Newest" (chronological discovery date).
- **Search Filtering**: Added real-time client-side search filtering by concept name.
- **Inline Expansion**: Enabled expanding rows to inspect timeline activity (First/Last Seen dates), lifespan active duration, and original semantic PCA coordinates.
- **TDD & Design System**: Rewrote unit tests in `ConceptMap.test.tsx` to assert search, tab switching, and expansion; used standard design system primitives (`Table`, `Badge`, `Button`, `Input`).
- **PostHog Tracking**: Captured `concept_tab_changed` and `concept_row_expanded` events for usage analytics.

**See**: [[entities/web-app]], [ConceptMap.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/concepts/components/ConceptMap.tsx), [ConceptMap.test.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/concepts/components/ConceptMap.test.tsx), [ConceptsPage.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/concepts/pages/ConceptsPage.tsx)

## [2026-06-18] feature | Ground How I'm Feeling LLM with Newsletters, S&P 500 Barometer, Prediction Markets, and Ticker Price Swings

Grounded the "How I'm Feeling" sentiment generation engine in external market and macro contexts to prevent it from overreacting solely to the trading decisions of other LLM agents:
- **Newsletter Ingestion**: Integrated today's/this week's clean newsletter snapshots (`sender`, `subject`, `content` snippets) into the sentiment analysis prompt context.
- **S&P 500 Barometer**: Added the latest S&P 500 valuation multiples and earnings surprise momentum snapshot from `market_barometer_history`.
- **Prediction Markets**: Incorporated active Polymarket and Kalshi odds sorted by volume from `prediction_market_snapshots`.
- **Price Swings**: Calculated price return percentages for all tickers traded or proposed today based on `price_history` and formatted them into the prompt.
- **TDD Enforcement**: Added a robust test case `test_prompt_includes_grounding_data` inside `TestBuildPrompt` to ensure prompt formatting is stable and correct.

**See**: [market_feeling.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/analysis/market_feeling.py), [test_market_feeling.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_market_feeling.py)

## [2026-06-17] bugfix | Fix Barometer Audit Page compilation and routing type safety

Resolved TypeScript compiler errors in the web application around the S&P 500 Market Health Barometer Audit route:
- **Search Parameter Optionality**: Updated `validateSearch` in `routes/barometer-audit.tsx` to return `{ date?: string }`, resolving a compiler error where links to `/barometer-audit` were complaining about missing the required `search` prop.
- **Bound useNavigate Context**: Contextually bound `useNavigate` to `/barometer-audit` inside `BarometerAuditPage.tsx` via `useNavigate({ from: '/barometer-audit' })`. This types the navigation search state modifier function (`(prev) => ...`) correctly and prevents generic router/root parameter conflicts.
- **Test Mock Schema Alignment**: Appended the missing `constituents_data` property to the mock barometer data in `HomePage.test.tsx` to conform to the `MarketBarometer` type definition introduced by the database layer for constituent audit logs.

**See**: [[entities/web-app]], [barometer-audit route](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/routes/barometer-audit.tsx), [BarometerAuditPage](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/home/pages/BarometerAuditPage.tsx), [HomePage.test.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/home/pages/HomePage.test.tsx)

## [2026-06-17] feature | Self-Correction Retry Loop for Missing Tool Calls & Sequence Constraint Rule

Implemented a post-hoc retry mechanism inside `analyze_with_provider` in the execution engine to handle cases where LLMs recommend trade actions (BUY/SELL) but fail to execute the required quantity calculation tools (`calculate_buy_quantity`/`calculate_sell_quantity`).
- **Correction Request & Retry**: The engine detects missing tool calls from the conversation history, appends a detailed correction prompt requesting immediate execution, and performs a single-attempt retry loop on the provider-specific tool runner.
- **Sequence Constraint Rule**: Added a strict Ordering rule (6) to the immutable `SYSTEM_PROMPT_CONSTRAINTS_HEADER` prompt to explicitly instruct models to execute all calculation tools before outputting their final structured JSON decision block.
- **TDD Enforcement**: Added `test_gemini_sell_tool_missing_triggers_retry` verifying the retry mechanism for the Gemini handler. Updated existing OpenAI and Gemini tool loop tests to avoid false retries during unit testing.

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

## [2026-06-16] feature | Terminal-Friendly Visual Planning Framework

Implemented a terminal-native visual planning framework to allow agents to generate rich, visual, Markdown-compliant plans:
- **Concept Page**: Created [[concepts/visual-planning]] detailing Unicode box-drawing, ASCII flowcharts, progress trackers, and UI mockups.
- **Mandatory Agent Guideline**: Updated the Plan First instructions in [[entities/gemini]] and [[concepts/agent-workflow]] to require visual planning for all non-trivial tasks.
- **Wiki Integration**: Indexed and cross-linked the new planning page within the wiki index.

**See**: [[concepts/visual-planning]], [[concepts/agent-workflow]], [[entities/gemini]]

## [2026-06-16] documentation | Document Supabase Google OAuth Redirect Whitelisting

Created a concept page to detail how Supabase Auth whitelisting and fallback logic handles requested redirects. Documents the difference between local dev ports (Netlify dev 3000 vs. Vite 3005) and production deployment whitelists, providing step-by-step instructions to prevent redirect-loop fallbacks to localhost:3000.

**See**: [[concepts/supabase-redirect-whitelisting]], [[entities/web-app]]

## [2026-06-17] feature | Prediction Market Tools and Database Schema

Added prediction market capabilities to the engine:
- New DB table `prediction_market_snapshots` for storing Polymarket/Kalshi odds
- Two new LLM tools: `search_prediction_markets` (DB search) and `get_prediction_market_odds` (live API fetch)
- Tool definitions registered across all providers (OpenAI, Anthropic, Gemini)
- Execution handlers with dispatcher routing
- Unit tests for search, live odds, and handler dispatch
- Wiki updates: agents, database, ingestion pages updated
- ROADMAP.md: added options/info item

## [2026-06-17] refactor | Remove progress bar from visual planning framework

Refactored the visual planning framework:
- **Removed Progress Bar**: Removed the 0%-100% Unicode progress bars from `wiki/concepts/visual-planning.md` instructions, tables, and templates.
- **Status Board**: Renamed "Progress Board" and "Progress Tracker" to "Status Board", focusing exclusively on the active phase rather than completion percentages.

**See**: [[concepts/visual-planning]]

## [2026-06-17] feature | LLM Leaderboard & Screening Tool

Implemented a comprehensive screening and ranking leaderboard for comparing LLMs based on trading performance, reasoning quality, and consistency:
- **Database Layer**: Deployed Supabase migration `20260618000000_create_llm_leaderboard_rpc.sql` creating the `get_llm_leaderboard_metrics` function to dynamically calculate returns, realized P&L, win rates, verifier approval rates, average confidence, and consistency scores over selected timeframes (7d, 30d, 90d, All-Time).
- **TypeScript Integration**: Added `LLMLeaderboardRow` types to `@llm-market-bench/database`.
- **API Fetcher**: Created `fetch-leaderboard.ts` to execute RPC queries from the TanStack Start server layer.
- **Visual Page & Routing**: Added new route `/leaderboard` and created the `LeaderboardPage` hub with a timeframe switcher.
- **Aesthetic Components**: Designed a Bloomberg-meets-Wired podium layout (`LeaderboardPodium.tsx`), a sortable data grid (`LeaderboardTable.tsx`), and a side-by-side comparative diagnostics utility (`ModelComparison.tsx`) using the design system's glass Cards, Tables, and Badges.
- **TDD & Quality**: Created `fetch-leaderboard.test.ts` and `LeaderboardPage.test.tsx` verifying data aggregation, metrics calculations, UI rendering, and comparison interactions. Passed 100% of test suites with zero lint or formatting errors.

**See**: [leaderboard route](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/routes/leaderboard/index.tsx), [fetch-leaderboard.ts](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/leaderboard/api/fetch-leaderboard.ts)

## [2026-06-17] feature | LLM Leaderboard & Screening Tool

Implemented a comprehensive screening and ranking leaderboard for comparing LLMs based on trading performance, reasoning quality, and consistency:
- **Database Layer**: Deployed Supabase migration `20260618000000_create_llm_leaderboard_rpc.sql` creating the `get_llm_leaderboard_metrics` function to dynamically calculate returns, realized P&L, win rates, verifier approval rates, average confidence, and consistency scores over selected timeframes (7d, 30d, 90d, All-Time).
- **TypeScript Integration**: Added `LLMLeaderboardRow` types to `@llm-market-bench/database`.
- **API Fetcher**: Created `fetch-leaderboard.ts` to execute RPC queries from the TanStack Start server layer.
- **Visual Page & Routing**: Added new route `/leaderboard` and created the `LeaderboardPage` hub with a timeframe switcher.
- **Aesthetic Components**: Designed a Bloomberg-meets-Wired podium layout (`LeaderboardPodium.tsx`), a sortable data grid (`LeaderboardTable.tsx`), and a side-by-side comparative diagnostics utility (`ModelComparison.tsx`) using the design system's glass Cards, Tables, and Badges.
- **TDD & Quality**: Created `fetch-leaderboard.test.ts` and `LeaderboardPage.test.tsx` verifying data aggregation, metrics calculations, UI rendering, and comparison interactions. Passed 100% of test suites with zero lint or formatting errors.

## [2026-06-17] feature | Leaderboard MiniMax Bypass & Card Height Fixes

Updated the LLM Leaderboard to ignore verifier metrics for MiniMax-M3 and fix card height overflow:
- **Database Layer**: Added migration `20260618000001_update_llm_leaderboard_rpc_minimax.sql` that sets `verifier_approval_rate` to NULL and bases reasoning quality and composite scores solely on confidence for MiniMax-M3.
- **Frontend Filtering**: Modified `fetch-leaderboard.ts` to filter out old/inactive models not present in the active `MODELS` config.
- **Card Styling & Height**: Replaced fixed height `md:h-[...]` with dynamic `md:min-h-[...] h-auto` on the Podium cards to prevent floating text overflow, extracting `PodiumCard` to resolve Biome complexity warnings.
- **UI Logic**: Handled null verifier approval rates gracefully with an em-dash (`—`) and disabled win/loss highlighting for it in side-by-side comparison.
- **Type Safety**: Updated `LLMLeaderboardRow` definition to allow `verifier_approval_rate` to be `number | null`.
- **TDD Tests**: Updated tests to verify null-safety, em-dash display, and filtering of inactive models.

**See**: [[entities/llm-leaderboard]], [LeaderboardPodium.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/leaderboard/components/LeaderboardPodium.tsx), [fetch-leaderboard.ts](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/leaderboard/api/fetch-leaderboard.ts)

## [2026-06-17] feature | S&P 500 Market Health Barometer & Company Earnings Tools

Added two new LLM agent tools (`get_market_health_barometer` and `get_earnings_history`) and a daily S&P 500 barometer aggregator script. The barometer computes cap-weighted Trailing P/E, Forward P/E, P/S, P/B, and earnings beat rate from top 100 S&P 500 constituents, stores daily snapshots in `market_barometer_history`, and injects the latest snapshot into the global macro context. The earnings tool fetches ticker-specific earnings history (actuals vs estimates, surprise %, upcoming dates) via FMP and yfinance. Both tools are registered across Anthropic, Gemini, and OpenAI handlers. The barometer is displayed on the HomePage dashboard with a glassmorphism widget and animated beat rate gauge.

**See**: [[concepts/fundamental-analysis]], [[entities/web-app]], [[entities/macro-tracker]]

## [2026-06-17] feature | S&P 500 Market Health Barometer Audit Page & transparent constituent tracking

Implemented constituent-level audit tracking for S&P 500 Market Health Barometer:
- **Database Layer**: Added migration `20260620000000_add_constituents_data_to_barometer.sql` introducing a `constituents_data` JSONB column to the `market_barometer_history` table to store atomic daily constituent snapshot weights. Manually updated `supabase-types.ts` Row, Insert, and Update interface definitions.
- **Data Engine**: Updated the daily calculation script `update_market_barometer.py` to extract `companyName` and construct/persist the serialized array of constituent valuation metrics (market cap, price, trailing/forward P/E, P/B, P/S, earnings beat status) alongside the aggregates.
- **Frontend APIs**: Added `fetchMarketBarometerDates` and `fetchMarketBarometerForDate` loader functions in `fetch-barometer.ts` to retrieve historical dates and daily snapshots.
- **Audit View Routing**: Created the `/barometer-audit` route with TanStack Start's URL search params loader schema mapping, making selecting historical dates fully shareable and refreshable without client-side state.
- **High-Density Audit Dashboard**: Created `BarometerAuditPage.tsx` outlining standard formulas (cap-weighted averages) and presenting a high-density constituent table with reactive client-side search, column sorting, and beat-status filtering. Added an "Audit Data" link to the dashboard's barometer header.
- **TDD & Code Quality**: Updated Python backend tests to verify constituent snapshot generation. Created Vitest frontend test `barometer-audit.test.tsx` verifying data filtering, search, sorting, and fallback notice behaviors. Re-organized TS imports and refactored helper functions to fully comply with Biome's strict formatting and cognitive complexity constraints.

**See**: [[entities/web-app]], [BarometerAuditPage.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/home/pages/BarometerAuditPage.tsx), [update_market_barometer.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/scripts/update_market_barometer.py)

## [2026-06-18] fix | DeepSeek / Anthropic Hard Enforcement and MiniMax JSON Repair Bugs

Resolved two critical bugs in the LLM analysis and consensus pipeline:
- **DeepSeek/Anthropic Message Preservation**: Fixed a bug where `unflattened_messages` was captured *after* provider-specific message preparations (such as DeepSeek's `prepare_messages_for_instructor` or Anthropic's flattening) had already run and stripped `tool_calls` from the messages. The copy is now captured immediately after the tool execution loops run, preserving full `tool_calls` history for Layer 3 Hard Tool Enforcement validation.
- **MiniMax JSON Repair**: Improved `_repair_json_string` in `analysis.py` to identify and escape unescaped single backslashes that mistakenly escape closing JSON delimiter quotes (e.g. `basis\"}` resulting from trailing markdown/backslash content), preventing `JSONDecodeError` on MiniMax and other raw JSON-response models.
- **TDD verification**: Added new tests `test_deepseek_first_run_tool_check_preserves_calls` in `test_tool_enforcement.py` and `test_try_parse_json_with_trailing_backslash_escape` in `test_minimax_repair_bug.py`. Verified that the complete 773-test engine suite passes.

**See**: [[concepts/tool-enforcement]], [analysis.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/analysis.py), [test_tool_enforcement.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_tool_enforcement.py), [test_minimax_repair_bug.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_minimax_repair_bug.py)

## [2026-06-18] feature | Memories inline newsletter snippet citations and secure RPC


Implemented secure, lazy-loaded inline newsletter source citations for memories:
- **Database Layer**: Deployed Supabase migration `20260621000000_add_referenced_newsletters_rpc.sql` creating the `get_referenced_newsletter_snapshots` function with `SECURITY DEFINER` access. This securely exposes only those newsletter snippets that are explicitly linked inside a promoted memory's `metadata.source_ids`.
- **API Fetcher**: Added `fetchReferencedNewsletters` in `fetch-memories.ts` to call the new RPC.
- **Frontend Integration**: Updated `MemoryCard.tsx` to extract `source_ids` and query for their content on-demand via TanStack Query (`useQuery`) when a card is expanded.
- **Aesthetic UI**: Rendered source cards inside the expanded panel showing sender, subject, formatted date, and a scrollable viewport of the original news chunk.
- **TDD & Code Quality**: Created integration test `test_referenced_newsletters.py` verifying correct database RPC filters, added unit tests in `fetch-memories.test.ts`, and updated `MemoryCard.test.tsx` and `MemoriesList.test.tsx` to provide `QueryClientProvider` context. All tests pass with zero Biome/Ruff linting warnings.

**See**: [[concepts/memory-feedback]], [[entities/web-app]], [MemoryCard.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/memories/components/MemoryCard.tsx), [test_referenced_newsletters.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_referenced_newsletters.py)

## [2026-06-19] feature | Add Price-to-FCF (P/FCF) metric to backend engine, LLM tools, and web barometer

Added Price-to-Free-Cash-Flow (P/FCF) metric across the entire stack:
- **Database Layer**: Created migration `20260621100000_add_pfcf_to_barometer.sql` to add `pfcf_ratio` column to the `market_barometer_history` table in Supabase. Manually updated `supabase-types.ts` Row, Insert, and Update interface definitions.
- **Backend Provider & Tools**: Updated `FMPProvider` and `YFinanceProvider` to mathematically calculate constituent-level `priceToFreeCashFlowsRatio` from FCF yields (`1 / freeCashFlowYield`). Updated `execute_key_metrics_tool` and `execute_market_health_barometer_tool` to format and output P/FCF to the LLMs.
- **Barometer Aggregator**: Updated `update_market_barometer.py` to retrieve constituent P/FCF, calculate the cap-weighted Index P/FCF, exclude companies with negative or zero free cash flow to prevent multiple distortion, and save index-level and constituent-level results to Supabase.
- **Frontend Dashboard & Audit**: Updated `HomePage.tsx` to render the aggregate Price-to-FCF ratio on the S&P 500 Market Health Barometer glassmorphism card. Updated `BarometerAuditPage.tsx` to display aggregate P/FCF, include a P/FCF column in the constituent weightings table, and support sorting by P/FCF.
- **TDD & Code Quality**: Added unit tests verifying `priceToFreeCashFlowsRatio` retrieval and formatting in `test_key_metrics_tool.py`. Updated `test_market_barometer.py` to verify cap-weighted index P/FCF calculation and negative FCF exclusion logic. Updated Vitest suite in `barometer-audit.test.tsx` to verify P/FCF rendering on the audit dashboard. All frontend and backend lints and tests pass.

**See**: [[concepts/fundamental-analysis]], [[entities/web-app]], [HomePage.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/home/pages/HomePage.tsx), [BarometerAuditPage.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/home/pages/BarometerAuditPage.tsx), [update_market_barometer.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/scripts/update_market_barometer.py)

