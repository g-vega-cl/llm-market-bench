# Roadmap

A living document of features and improvements in progress or planned for the platform.

## Active Development

- [ ] **Money Flow Model** - Make a model (based on financial papers) to track money flows.
- [ ] **Statistical Predictions** - Implement Monte Carlo simulations, Random Forest, and other ML-based prediction models
- [x] **Find trading papers not just investing** - But low sell high?
  - Couldn't find any.
- [ ] **A programming/business buddy?**
  - Clippy (I already have something similar ) but that suggests improvements to the app. Just brainstorming the concept
- [x] - benchify: Make a "style vibe" ... — The design system (semantic gradients, typography: Space Grotesk + Satoshi + JetBrains Mono, component primitives) is in `packages/ui-design-system/`. Applied across all feature pages. See [DESIGN_SYSTEM.md](./raw/docs/web/DESIGN_SYSTEM.md).
- [ ] - add a local model?
- [ ] - make an autoresearcher for the verifier
- [ ] - Benchify: Allow portfolios to "invest cash" in "bonds" and get a return for unused cash.
- [ ] - Benchify allow people yo use their own models/keys/prompts and compete.
- [ ] - Benchify: start a "CEO" agent. With a self-loop
- [ ] - **Market-Closed Activities** - Define valuable tasks for agents when markets are closed (research, backtesting, memory consolidation)
- [ ] - add money printing/creation/fiscal deficits of governments to the sytem. Track government spending and deficits closely. Same with corporate spending.
- [ ] - Benchify: Enforce "Zero Compute on Frontend" in `searchMemories()` (`apps/web/src/features/memories/api/fetch-memories.ts`). Replace the unpaginated full-table query (3,144 rows + embeddings = ~18.8MB) and client-side Levenshtein loop with database-level text filtering and pagination.
- [ ] - Benchify: Strip invisible vector egress (`embedding` column) from `apps/web`. Replace `.select('*')` with explicit scalar column projections across `memories` and `decisions` queries in `fetch-memories.ts`, `fetch-today-data.ts`, and `fetch-cause-and-effect.ts`.
- [ ] - Benchify: improve the follow a single thought, add dates, the model process, adapt the card and carousel to proper size or remove it. Make it a real that you can change.
- [ ] - Benchify: use unlightouse to audit our whole site and fix.

- [ ] - make autoresearcher with more variables and more "temperatures?" More portfolios too?

- [ ] - Many of these things should be able to be picked up by autoresearch, I guess the loop is quite slow. How to speed up the loop?

- [ ] - Benchify: find the cheapest models and make a little autoresearch army that uses weekly rolling to update.
- [ ] - Benchify: per user log and reasons tracker. This ties to the LLM chat. Each user can track their own trades too and their reasoning.
- [ ] - Benchify: Autoresearch, make it so it can decide if it should remove data from emails or others. Allow it to see the input blocks and decide if it should remove or add inputs.
- [ ] - Try to track government stuff again, but make it explicit, make it maybe outside ingestion and consensus.
- [ ] - Benchify: add institutional buying and Congress buying?
- [ ] - Duolingo but with crypto? Take an app that already exists but "crypto"
- [ ] - Benchify: track specific governments with liquid enough stock markets like Canada and trade based on government deals and pipelines and government money
- [ ] - Erica said that in Canada you could have clear insider trading because there is a gradual buying leading to news, so we could tap into this.
- [ ] - An LLM that focuses only on government opportunities. - Like deals in pipeline, new reforms, under the radar things
- [ ] - Benchify: add institutional buying and Congress buying?
- [ ] - Benchify, time to add your own portfolio? What about your agents portfolio?
- [ ] - Benchify: market data free APIs?
- [x] - Benchify: is AI better working with many small files for separation of concerns and avoid side effects? Islands?
    - Confirmed with git forensics: AI agents perform best with vertical slice islands (100 to 300 LOC) and colocated tests, while files over 700 LOC have 40% to 66% bug ratios. Avoided hyper-fragmented micro-files. Codified as Principle 10 and 11 in `GEMINI.md` and created `[[concepts/vertical-slice-islands]]`.
- [ ] - Benchify: free APIs to the LLMs chat?
- [ ] - Benchify, time to add your own portfolio? What about your agents portfolio?
- [ ] - Benchify: What about making a benchmark for day trading/investing?
- [x] - Benchify; make an statistic if any of our buys were ever profitable. Like what if I followed my agent's buys and decide on the sells myself?
    - Did this, I think it was basically a 50/50 bet. Even I checked if it ever touched something like .5% or .1% and it didn't change it much.
- [ ] - Benchify: I might already have something like this, try to predict earnings movement. Maybe just up/down from beginning of trading day?
- [ ] - Single company focused llm - Did this with LIN, but I don't think it's working as expected. REVISIT.
        - [ ] - Benchify: "hyperfocus on a mid size company?
        - [ ] - Benchify: just trade one ETF on one auto researcher. Maybe the Focus on a single company related to this?
- [ ] - Look for statistical analysis for markets
- [ ] - What about a "visual" screenshot of charts and ask for candlestick/trading patterns?
- [ ] - Benchify: move all newsletters to dedicated email
- [ ] - https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/honcho.md
- [ ] - Benchify: Toronto stock market
- [ ] - in finance is better to be 100% confident and right in one prediction that usually confident and right on many predictions/What's the best way to set up an autoresearcher about this?
- [x] - check if the daily SPY and sector portfolios are working
    - Audited historical trades and portfolios: identified duplicate SPY trades on 2026-09-01 caused by re-evaluation without trade deduplication.
    - Removed duplicate trade pair in DB and corrected cash balances for DeepSeek ($9,876.50) and MiniMax ($10,025.41).
    - Added idempotency guardrails in `execute_system_daily_trade()`, `execute_system_sector_rebalance()`, and `execute_mechanical_sector_rebalance()`.
    - Added strict 7-day timeframe filter in `evaluate_predictions.py` to isolate weekly system portfolios from longer-horizon predictions.
- [ ] -  Benchify: an autoresearch autoresearcher?
- [x] - Benchify: pass daily newsletter to daily predictor? Or give it a tool that can access it? And run it after the newsletter. And same for the portfolio autoresearch
    - Added canonical `fetch_daily_newsletter` tool in `core/llm/tools.py` for trading LLMs (OpenAI, Claude, Gemini).
    - Added `query_past_newsletters` in `autoresearch/tools.py` for the weekly Autoresearch meta-agent.
    - Updated `get_daily_market_context` in `daily_predictor.py` to fetch today's morning briefing with graceful fallback.
    - Updated `DAILY_PREDICTOR_PROMPT` constraints header to document synthesized newsletter context.
    - Updated Cron Dispatcher to trigger `generate-newsletter.yml` at 9:12 AM ET with automatic chained downstream dispatch to `daily-predictor.yml`.
- [ ] - Benchify: daily trades for sector predictor audit
- [ ] - Benchify: a bond trader?
- [ ] - Benchify : do we get volume alongside price? Volume deviations?
- [x] - Benchify, audit with alpaca. Like, a single portfolio see if it matches alpaca moves and equity movement
- [ ] - My site looks just like every other LLM-made site. Let's improve it.
- [ ] - Give autoresearch a way to make "memories" 
- [ ] - Benchify: follow the crowd strategy? Like using options and volume data?
- [ ] - Benchify: in today page, make the default price shower show a mix of important indicators like bond yields, equity, international, gold, wti, vix
- [ ] - Benchify: train small model?
- [ ] - benchify: fine tune the autoresearcher rather than the model?
- [ ] - Benchify: 2 week sector predictor and check how different are the weekly/monthly/90d predictions from each other..
- [ ] - Benchify: should autoresearch ingest newsletters?
- [ ] - Benchify: avoid JS for designs, use CSS whenever possible. Grid flex are so good
- [ ] - Benchify: insider trading tracker, congress, CEO, whales , 13Fs?Canada insider trader specifically?
- [ ] - Benchify: publish your plan for marketing and results. Make it PostHog focused
- [ ] - Benchify; tool for think about related winners? Memory/energy/etc... in AI, clothes GLP, etc...
- [ ] - Benchify: something I can autoresearch daily?
        Maybe 4h candles and statistics with news context? Maybe the news can be summarized from the newsletters and that can also be autoresearched optimized
- [ ] - Benchify: sector predictor prompt also separate into things that can change and things that shouldn't
- [ ] - Find if yoyu can set up any PEAD based strategy
- [ ] - I like the idea of a "finacial/trading" benchmark for agents.
- [ ] - Make sure my agents are thinking agents.

## Hotspot Refactoring (Vertical Slice Islands)

Decompose critical monolithic hotspots identified by churn forensics into isolated modules (target 100 to 300 LOC) with colocated tests.

- [ ] **Refactor `apps/engine/core/llm/tools.py`** (3,128 LOC)
  - Decompose the monolithic tool registry into domain modules (`tools/market_data.py`, `tools/technicals.py`, `tools/sec_filings.py`, `tools/portfolio.py`) with a thin dispatcher barrel.
- [ ] **Refactor `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx`** (1,471 LOC, 20.0% fix ratio)
  - Extract page sub-components (chart panels, variant sidebars, score modals, history tables) into colocated components under `features/daily-predictions/components/` under 300 LOC each.
- [ ] **Refactor `apps/engine/core/llm/analysis.py`** (1,150 LOC, 63.6% bug fix ratio, CRITICAL)
  - Split prompt assembly, response parsing, and validation into separate vertical modules to eliminate patch search collisions and regression cascades.
- [ ] **Refactor `apps/engine/main.py`** (949 LOC, 40.7% bug fix ratio, CRITICAL)
  - Decompose the monolithic CLI entry point into sub-command routers under `apps/engine/cli/` to keep entry points under 200 LOC.
- [ ] **Refactor `apps/web/src/features/autoresearch/components/DailyScoreDisplay.tsx`** (912 LOC, 55.6% bug fix ratio, HIGH)
  - Break metric calculations, ratchet comparisons, and breakdown charts into isolated UI primitives.
- [ ] **Refactor `apps/engine/execution/market_data.py`** (749 LOC, 66.7% bug fix ratio, CRITICAL)
  - Separate data provider clients, price caching, and transform logic into modular units.
