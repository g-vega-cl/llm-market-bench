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
- [ ] - Duolingo but with crypto? Take an app that already exists but "crypto"
- [ ] - Benchify: track specific governments with liquid enough stock markets like Canada and trade based on government deals and pipelines and government money
- [ ] - Erica said that in Canada you could have clear insider trading because there is a gradual buying leading to news, so we could tap into this.
- [ ] - An LLM that focuses only on government opportunities. - Like deals in pipeline, new reforms, under the radar things
- [ ] - Benchify: add institutional buying and Congress buying?
- [ ] - Benchify, time to add your own portfolio? What about your agents portfolio?
- [ ] - Benchify: market data free APIs?
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
- [ ] - Benchify: Toronto stock market
- [ ] - in finance is better to be 100% confident and right in one prediction that usually confident and right on many predictions/What's the best way to set up an autoresearcher about this?
- [ ] -  Benchify: an autoresearch autoresearcher?
- [ ] - Benchify: a bond trader?
- [ ] - Benchify : do we get volume alongside price? Volume deviations?
- [ ] - My site looks just like every other LLM-made site. Let's improve it.
- [ ] - Benchify: follow the crowd strategy? Like using options and volume data?
- [ ] - Benchify: train small model?
- [ ] - benchify: fine tune the autoresearcher rather than the model?
- [ ] - Benchify: 2 week sector predictor and check how different are the weekly/monthly/90d predictions from each other..
- [ ] - Benchify: avoid JS for designs, use CSS whenever possible. Grid flex are so good
- [ ] - Benchify: insider trading tracker, congress, CEO, whales , 13Fs?Canada insider trader specifically?
- [ ] - Benchify: publish your plan for marketing and results. Make it PostHog focused
- [ ] - Benchify: something I can autoresearch daily?
        Maybe 4h candles and statistics with news context? Maybe the news can be summarized from the newsletters and that can also be autoresearched optimized
- [ ] - Benchify: sector predictor prompt also separate into things that can change and things that shouldn't
- [ ] - Find if yoyu can set up any PEAD based strategy
- [ ] - Find if you can do a "MAx pain" strategy
- [ ] - I like the idea of a "finacial/trading" benchmark for agents.
- [ ] - Benchify: instead of daily up/down/ammount predictor. A "will it hit this option strike at any point during the day"? Like, will the option be ON The Money at any time? And which options? Maybe we can start with fixed? - Actually, might be kind of the same thing
- [ ] - Benchify: tool that can show the system portfolios to the daily predictor, portfolios, and autoresearch? Maybe it can grasp patterns like mean revertion, trends, continuity, etc...
- [ ] - Benchify : format better the newsletter section of: The Catalyst Radar & Key Levels.
- [ ] - Benchify, if you were to show this up as a portfolio project. What would you improve. - Lighthouse, design, maybe audit data fetching. CDNs? It should be lighting fast. SSR?
- [x] - Benchify: even though CPI was released at 8:30 and predictor/newsletter at 9:15, we still didn't get/fetch the result of the CPI
- [ ] - Benchify: I don't like the "collapse" in mobile.in my theme portfolios
- [ ] - Benchify: a tool that describes how the market/stock/spy moved during the day? Or one that brings you the daily prices?
- [ ] - Benchify: audit that the "sector trend" and others portfolios are set up.
- [ ] - Benchify : daily predictor prompt diff
- [ ] - Benchify : in the daily predictor. It shows as if the current new prompt had a score already
- [ ] - Benchify audit sector predictor portfolio. Seems like it's wrong
- [ ] - Benchify: daily autoresearcher "lesson learned"? Like, every day, when you check if you were right or wrong, also ask "why" and see if it's worth adding these insights as memories or as an special label for daily predictor
- [ ] - Benchify : intraday news? Like more intraday newsletters but with market moving news events?
- [ ] - Benchify: add a "this could be a trade or force in the future". Like, ABNB with world cup, or cybersecurity/infrastructure with AI, or some undervalued company going through a temporary rough patch.
- [ ] - Benchify: add "buffet sayings" tool? Like buy low sell high, buy when others are scared, etc....?
- [ ] - Benchify: prompt tool question, "how did markets react the last time XYZ happened?"
- [ ] - Benchify : find weekly /daily/monthly gainers and ask: why didn't we predict this?
- [ ] - Benchify : fun idea. Every morning do some kind of praying to the market God's funny tiktok video showing your prediction and kind of begging to the gambling gods allow you to win some money
- [ ] - Benchify: any way of tracking which tools were used?
- [x] - Benchify: daily portfolios but sell at 3:50ish, not when target is hit (added sys-daily-spy-close-* with 0.02% slippage).
- [ ] - Benchify: Right now we have in trades a single newsletter attribution usually but with AI more than one newsletter could have been the reason of the trade or even not newsletters and other thoughts how can we improve attribution"1

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
- [ ] **Refactor `apps/engine/execution/market_data.py`** (749 LOC, 66.7% bug fix ratio, CRITICAL)
  - Separate data provider clients, price caching, and transform logic into modular units.
