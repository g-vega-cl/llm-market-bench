# Roadmap

A living document of features and improvements in progress or planned for the platform.

## Active Development

- [ ] **Money Flow Model** - Make a model (based on financial papers) to track money flows.
- [ ] **Reliable Market-Open Ingestion Scheduler** - Migrate or supplement GitHub Actions' native schedule cron (`.github/workflows/ingest.yml`) with an external scheduler/webhook (e.g. AWS EventBridge, Modal, or external HTTP trigger via `repository_dispatch`) to eliminate GitHub Actions public runner queue delays and silent skips of 9:35 AM and 10:35 AM ET runs.
- [ ] **Investment Chat Gateway** - Gated "Should I invest in this stock?" chat interface connecting users with LLM agents and their memories (e.g., research NVO). Requires backend infrastructure with potential home server deployment
- [ ] **Code Hotspot Finder** - Automated tool to identify code areas needing refactoring or optimization
- [ ] **Statistical Predictions** - Implement Monte Carlo simulations, Random Forest, and other ML-based prediction models
- [ ] **Review lessons learned and the learning loop** -
- [ ] **Canary deployment** - Make sure you can roll out to X% of users or get a staging env.
- [ ] **Larn why it hallucinates numbers so much And how to fix.** - Maybe some kind of calculation forward tool. Like, give the price up front and ask it "is this a good number to buy", rather than asking it to come up with the number itself.
- [x] **A proactive codebase checker and task maker connected to Posthog?** - An agent that's a user that gives feedback and proposes improvements running 24/7
  - This is basically what "Jules" does already, and I don not like Jules results....
- [ ] **Best way to simulate a QA department**
  - We could use backStopJS and other tools, but for now it's not necessary.
- [ ] **Roll out/deploy a branch to prod. But not master? Like % deployment?**
- [x] **Find trading papers not just investing** - But low sell high?
  - Couldn't find any.
- [ ] **A programming buddy?**
  - Clippy (I already have something similar ) but that suggests improvements to the app. Just brainstorming the concept
- [ ] **An "AI" debate or consensus on different ways to invest in different events?**
- [ ] **Post trade analysis re-visit.** And add the model that made it. And more details of memory. Make it so it's easy to use as learning.
- [ ] **Recheck calendar events**
- [x] **Setup local agent managing dashboard? Split screens and stuff in vim or terminals**
  - Decided it was a bit inconvenient and not worth it.
- [ ] **When building something, ask for three ways this could work. Also, when brainstorming and building something, ask for the next ten things on how this could be made or the next five things after the first question.**
- [ ] **I like the chatgpt setup of "ask the next best question" like**. Show me a couple of options of what the next best thing to ask would be
- [ ] **Include extra sources of "true" not subjective data? Satellite images, weather, etc... research what's usually used for this.**
- [ ] **Company earnings not really (that's a different point) but a way of predicting the earnings?**
- [ ] **Some kind of small/mid-cap ETF, but that doesn't remove the companies that grow. Custom, probably.**
- [ ] **Set up a 'global' agent hook/env for my projects?**
- [ ] A live suggestion maker in chat? - recording like granola but that suggests questions or finds werid things live and shows it as some kind of popup dialogue. - What I'm envisioning is chat suggestions for what best ask next like chatgpt does. <- Might have been for pocket. But could be used for LLM chat once I have that too. - Maybe add a button that adds suggestion.
- [ ] **LLM chat, but for everywhere? Like click on a memory card and load that into context and start the chat then and there.** Allow it to make database fetches/etc...
- [x] add metrics add CAPE, PE, forward PE, book-to-market Etc.... ? Do I already have them? P/free cash flow
- [x] manage prompt size with increasing memory/lessons learned database.
- [ ] - Benchify : include reasons for rejections in the audit and make sure we improve why we are getting so many rejections for trades
- [ ] - Both poket, benchify, and terminal: Send whole convo to agent so it suggests best next questions/prompts.
- [ ] - Benchify: LLMs struggle with numbers/limit prices, how can I fix
- [x] - benchify: Make a "style vibe" ... — The design system (semantic gradients, typography: Space Grotesk + Satoshi + JetBrains Mono, component primitives) is in `packages/ui-design-system/`. Applied across all feature pages. See [DESIGN_SYSTEM.md](./raw/docs/web/DESIGN_SYSTEM.md).
- [ ] - check if this repo would help: https://github.com/anthropics/financial-services
- [ ] - alongside Karpathy wiki https://claude.com/blog/new-in-claude-managed-agents https://platform.claude.com/docs/en/managed-agents/define-outcomes
- [ ] - add a local model?
- [ ] - can I add how much I have spent in each provider? Would be fun to visualize
- [ ] - rate answers from 1-5 and then use that feedback to run an external agent asking "What was good from this".
- [ ] - Revisit alpaca trades.
- [ ] **Audit the Wiki Lint pipeline.** —
- [ ] **Wiki Lint Remediation (from 2026-05-16 Audit)** — [Issue #20](https://github.com/g-vega-cl/llm-market-bench/issues/20)
  - [x] [Medium] Confirm terminal state of legacy `PENDING` orders and simplify `concepts/alpaca-order-sync.md`.
- [ ] -benchify: a second website where the code is managed by AI mostly autonomously?
- [x] -Benchify: audit price fetching and how we pass it to LLMs
- [ ] - Benchify: for the "question answerer LLM.that I want to implement, what's the best way of RAG?"
- [x] Benchify: audit the verifier.
- [ ] - Benchify: Allow portfolios to "invest cash" in "bonds" and get a return for unused cash.
- [x] - Audit memories and make sure they are added to the agents in the best way possible. Maybe aufit the RAG too.
- [ ] - Benchify allow people yo use their own models/keys/prompts and compete.
- [ ] - Benchify : add opportunity costs to sells? Like, oh, if you held you would have made more/less? Maybe not worth because lookback bias?
- [ ] - Benchify : audit that memories are still being correlated to each other
- [ ] - Events/Consensus events : tend to be a bit ambiguous, maybe click and show the source of the event? The news that prompted it?
- [ ] - Benchify: uncorrelated high return sectors this week do well for next week check
- [ ] - Benchify: search bar for memories
- [ ] - Benchify and QMD; connect pre hook with local LLM chat convos
- [ ] - Benchify: start a "CEO" agent. With a self-loop
- [ ] - Implement Redis?
- [ ] - **Market-Closed Activities** - Define valuable tasks for agents when markets are closed (research, backtesting, memory consolidation)
- [ ] - add money printing/creation/fiscal deficits of governments to the sytem. Track government spending and deficits closely. Same with corporate spending.
- [ ] - add memories sorting by importance or filter by date too.
- [x] - Benchify: lighthouse CLI/performance audit.
- [ ] - Benchify: update autoresearch scoring display in FE. How to keep them synced?
- [ ] - Benchify: add which ticker corresponds to each scenario in memories possible scenarios
- [ ] - Benchify: historical parallel more details - goes well with LLM chat.
- [ ] - Benchify: keep and expose my DB locally too? So I can offload data from supabase and use both DBs?
- [ ] - Weekly audit for ingestion & consensus?
- [ ] - Benchify: a "keep an eye" section? It's the culmination of concepts + calendar?
- [ ] - Benchify: audit the ad stripping llm
- [ ] - Benchify: improve the follow a single thought, add dates, the model process, adapt the card and carousel to proper size or remove it. Make it a real that you can change.
- [ ] - Benchify: use unlightouse to audit our whole site and fix.
- [x] - I don't see lightouse in CI
- [ ] - Benchify: make agents think "what's going to happen tomorrow? What will happen next week?" How can I profit from that? Your scenario analysis and calendar should be useful for this. Pass it the exact date and time when making choices?

Make autoresearcher with more variables and more "temperatures?" More portfolios too?

Allow the LLM to decide what to bring to context?

Many of these things should be able to be picked up by autoresearch, I guess the loop is quite slow. How to speed up the loop?

- [ ] - Benchify: find the cheapest models and make a little autoresearch army that uses weekly rolling to update.
- [ ] - Benchify: per user log and reasons tracker. This ties to the LLM chat. Each user can track their own trades too and their reasoning.
- [ ] - Benchify: it's stock analysis also part of my sources?
- [ ] - Get option information. Like Greeks, implied volatility, etc... Maybe from FMP?
- [ ] - Benchify: check if "today vibes" also includes the emails. Also maybe add the FMP summary to it too.
- [ ] - Benchify: Autoresearch, make it so it can decide if it should remove data from emails or others. Allow it to see the input blocks and decide if it should remove or add inputs.
- [ ] - Try to track government stuff again, but make it explicit, make it maybe outside ingestion and consensus.
- [ ] - Think about how tools are defined and used.
- [ ] - Benchify: you don't have to trade ultra-high caps, feel free to dabble on mediumer caps. But still liquid
- [ ] - Benchify: LLMs existed for a while before they exploded, same with crypto, what other techs are like this? Quantum?
- [ ] - Benchify: fed watch api like but free?: https://share.gemini.google/iul3v5Q9C3AE
- [ ] - Benchify: add institutional buying and Congress buying?
- [ ] - Duolingo but with crypto? Take an app that already exists but "crypto"
- [ ] - Benchify: make sure El Niño is saved in memory
- [ ] - Benchify: predict S&P for the day
- [ ] - Benchify: track specific governments with liquid enough stock markets like Canada and trade based on government deals and pipelines and government money
- [ ] - Erica said that in Canada you could have clear insider trading because there is a gradual buying leading to news, so we could tap into this.
- [ ] - An LLM that focuses only on government opportunities. - Like deals in pipeline, new reforms, under the radar things
- [ ] - Benchify: add institutional buying and Congress buying?
- [ ] - Benchify, time to add your own portfolio? What about your agents portfolio?
- [ ] - Benchify: free APIs?
- [ ] - Benchify: What about making a benchmark for day trading/investing for users?
- [ ] - Benchify: is AI better working with many small files for separation of concerns and avoid side effects? Islands?
- [ ] - Benchify: fed watch api like but free? - https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html - https://share.gemini.google/iul3v5Q9C3AE
- [ ] - Benchify: free APIs to the LLMs chat?
- [ ] - Benchify, time to add your own portfolio? What about your agents portfolio?
- [ ] - Benchify: What about making a benchmark for day trading/investing?
- [ ] - Benchify: is AI better working with many small files for separation of concerns and avoid side effects? Islands?
- [ ] - Benchify: let winners run? cut losers concept?
- [ ] - Statistically, in X regime, indicated by X indicator. What percentage of X timeframe candles are X% up vs X% down vs not reaching that %? And can that be made a strategy?

Feels like I have done that before to no avail

- [ ] - Benchify; make an statistic if any of our buys were ever profitable. Like what if I followed my agent's buys and decide on the sells myself?
- [ ] - Benchify: I might already have something like this, try to predict earnings movement. Maybe just up/down from beginning of trading day?
- [ ] - benchify: memory consensus events check if the predictions came true, if the scenarios worked as expected
- [ ] - When a card says "resolved" show which scenario "won" or show more details on why it was resolved, and what resolved
- [ ] - Benchify: I really need to set the read LLM helper
- [ ] - Chart based on candle volatility not time
- [ ] - Single company focused llm
- [ ] - Look for statistical analysis for markets
- [x] - Predict daily S&P or whichever move, either up or down.
- [ ] - Add more LLMs to sector researcher.
- [ ] - backtest sector researcher.
- [ ] - What about a "visual" screenshot of charts and ask for candlestick/trading patterns?
