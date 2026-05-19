# Roadmap

A living document of features and improvements in progress or planned for the platform.

## Active Development

- [ ] **LLM Ranking Tool** - Build a screening system to evaluate and rank LLMs based on trading performance, reasoning quality, and consistency
- [ ] **Money Flow Model** - Make a model (based on financial papers) to track money flows.
- [ ] **Investment Chat Gateway** - Gated "Should I invest in this stock?" chat interface connecting users with LLM agents and their memories (e.g., research NVO). Requires backend infrastructure with potential home server deployment
- [ ] **Code Hotspot Finder** - Automated tool to identify code areas needing refactoring or optimization
- [ ] **Finance Papers RAG** - Add academic finance papers to memory system using Retrieval-Augmented Generation
- [ ] **Statistical Predictions** - Implement Monte Carlo simulations, Random Forest, and other ML-based prediction models
- [ ] **Whole market earnings estimates** - Add whole market earnings estimates to the system. Compare with historical if possible.
- [ ] **Review lessons learned and the learning loop** -
- [ ] **Revisit the concepts map** - It should be something like "this new trend is comming up or leaving"
- [ ] **Add statistics** - Check current price changes in big indexes to gauge market moves today. And other indicators like stdev etc. if the market has moved 1% up today. Why? Is that normal?
  - Pass the price of many indexes to the LLM from the beginning (Add them to price update step) (This is part of the global macro tracker)
- [ ] **Canary deployment** - Make sure you can roll out to X% of users or get a staging env.
- [ ] **Posthog** - Make sure it's working - I need to add a reverse proxy.
- [ ] **Larn why it hallucinates numbers so much And how to fix.** - Maybe some kind of calculation forward tool. Like, give the price up front and ask it "is this a good number to buy", rather than asking it to come up with the number itself.
- [ ] **A proactive codebase checker and task maker connected to Posthog?** - An agent that's a user that gives feedback and proposes improvements running 24/7
- [ ] **More context on what lead to certain memory**
- [ ] **Best way to simulate a QA department**
- [ ] **Roll out/deploy a branch to prod. But not master? Like % deployment?**
- [ ] **Find trading papers not just investing** - But low sell high?
- [ ] **Fix asset discovery.** Go step by step, dedicated agent maybe
- [ ] **Make sure CI/CD tests behave same as local tests**
- [ ] **Use frontend skills to improve frontend**
- [ ] **Sector leaderboard**
- [ ] **A famous financial anomaly is that the stock market mostly goes up when it's closed:** -goes along with papers
- [ ] **Re-check asset discovery**
- [ ] **A programming buddy?**
  - Clippy (I already have something similar ) but that suggests improvements to the app. Just brainstorming the concept
- [ ] **I don't see percentages in scenarios anymore**
- [ ] **Fix investable assets title as well..and make sure you highlight which investable assets belong to each scenario.**
- [ ] **An "AI" debate or consensus on different ways to invest in different events?**
- [ ] **Improve investable assets again?**
- [ ] **Post trade analysis re-visit.** And add the model that made it. And more details of memory. Make it so it's easy to use as learning.
- [ ] **Add "learning from failures" to what I'm feeling right now.**
- [ ] **Add 5 Whys in some flow, not sure if we already have it somewhere. I want a "root cause method". MECE?**
- [ ] **Audit that alpaca is working as intended**
- [ ] **Recheck calendar events**
- [ ] **Also check alternative plays function**
- [ ] **Setup local agent managing dashboard? Split screens and stuff in vim or terminals**
- [ ] **When building something, ask for three ways this could work. Also, when brainstorming and building something, ask for the next ten things on how this could be made or the next five things after the first question.**
- [x] **Karpathy method for prompt improvement.** — Implemented `apps/engine/autoresearch/`: weekly autonomous meta-researcher LLM evaluates live trading performance across 4 dimensions (Wall Street metrics, decision quality, structural analysis, local minima escape) and iteratively improves the prompt. Gemini + DeepSeek agents are the experiment group; OpenAI + Claude serve as control. See [[entities/autoresearch]] and [[concepts/auto-research-prompt-improver]].
- [ ] **I like the chatgpt setup of "ask the next best question" like**. Show me a couple of options of what the next best thing to ask would be
- [ ] **Make sure we save the historical correlation/returns table/matrix**
- [ ] **Include extra sources of "true" not subjective data? Satellite images, weather, etc... research what's usually used for this.**
- [ ] **Company earnings not really (that's a different point) but a way of predicting the earnings?**
- [ ] **A tracker of your chats with LLMs to track productivity. Enterprise Software?** Openrouter might already have this.
- [ ] **In my comparision chart, the dotted line had some weird vertical lines that shouldn't be there**
- [x] **Add design system code vertical.** — Implemented in `packages/ui-design-system/`. See [DESIGN_SYSTEM.md](./raw/docs/web/DESIGN_SYSTEM.md).
  - [x] The design system primitives (Button, Card, Badge) and patterns (SectionHeading, ConfidenceBar, StatPill, etc.) are now used across all feature pages.
- [ ] **Some kind of small/mid-cap ETF, but that doesn't remove the companies that grow. Custom, probably.**
- [ ] **Add past market events and their resolution? Like the resolution of the market events you showed before**
- [ ] **Set up a 'global' agent hook/env for my projects?**
- [ ] A live suggestion maker in chat? - recording like granola but that suggests questions or finds werid things live and shows it as some kind of popup dialogue. - What I'm envisioning is chat suggestions for what best ask next like chatgpt does. <- Might have been for pocket. But could be used for LLM chat once I have that too. - Maybe add a button that adds suggestion.
- [ ] **LLM chat, but for everywhere? Like click on a memory card and load that into context and start the chat then and there.** Allow it to make database fetches/etc...
- [x] **Supabase push/migrate programmatically?** - Resolved: remote DB is source of truth. Use `npx supabase db push --linked` for new migrations. See `AGENTS.md`.
- [ ] **add metrics** add CAPE, PE, forward PE Etc.... ? Do I already have them? P/free cash flow
- [ ] manage prompt size with increasing memory/lessons learned database.
- [ ] - Benchify : include reasons for rejections in the audit and make sure we improve why we are getting so many rejections for trades
- [ ] - Both poket, benchify, and terminal: Send whole convo to agent so it suggests best next questions/prompts.
- [ ] - Move to openrouter?
- [ ] - Retry server errors?
- [ ] - Benchify: focus on making good tool-calling, stock researching agents. Rather than an info dump.
- [ ] - Benchify: LLMs struggle with numbers/limit prices, how can I fix
- [ ] - Set up a linter for web app
- [x] - benchify: Make a "style vibe" ... — The design system (semantic gradients, typography: Space Grotesk + Satoshi + JetBrains Mono, component primitives) is in `packages/ui-design-system/`. Applied across all feature pages. See [DESIGN_SYSTEM.md](./raw/docs/web/DESIGN_SYSTEM.md).
- [ ] - check if this repo would help: https://github.com/anthropics/financial-services
- [ ] - alongside Karpathy wiki https://claude.com/blog/new-in-claude-managed-agents https://platform.claude.com/docs/en/managed-agents/define-outcomes
- [ ] - add a local model?
- [x] **Comprehensive Logging Audit & Traceback Hardening.** — Refactored engine, proxy, and provider logging to use `logger.exception` for full traceback capture. Enhanced log format with module names and added granular pipeline progress tracking. This enables the automated LLM log analyzer to perform root-cause analysis on ingestion and execution failures.
- [ ] - scenario analysis still empty
- [ ] - can I add how much I have spent in each provider? Would be fun to visualize
- [ ] - Benchify: improve get sector alternatives tool
- [ ] - Benchify: use html for documentation?
- [ ] - Always keep constant/steady instructions in the beginning of prompts, that way they get cached better. Keep the changing parts at the bottom.
- [ ] - rate answers from 1-5 and then use that feedback to run an external agent asking "What was good from this".
- [ ] - Benchify: include copper in sector analysis.
- [ ] - Benchify: add Reddit, polymarket, kalshi odds?
- [ ] - Revisit alpaca trades.
- [ ] - INVESTIGATE: MiniMax market feeling analysis — empty JSON response
- [ ] - Gemini-3.1-flash-lite generated 0 decisions.
- [ ] - Fix DeepSeek Verifier empty responses: Update 'prepare_messages_for_instructor' in verification loop to handle 'reasoning_content' properly and add JSON recovery prompt.
- [ ] - Remove yfinance as backup? It's unreliable as well? At least let's log it thoroughly.
- [x] **Audit the Wiki Lint pipeline.** — Successfully stabilized `wiki_lint_llm.py` with 75k character context cap and DeepSeek V4 Pro. First run identified 8 semantic findings. [Issue #20](https://github.com/g-vega-cl/llm-market-bench/issues/20).
- [ ] **Wiki Lint Remediation (from 2026-05-16 Audit)** — [Issue #20](https://github.com/g-vega-cl/llm-market-bench/issues/20)
  - [ ] [High] Resolve Karpathy ratchet contradiction: Reverting to baseline then immediately deploying a new variant makes the revert ineffective. Clarify if generation should be gated or if it must build strictly from the reset baseline.
  - [ ] [Medium] Standardize Source ID generation (MD5[:8]) between `concepts/ingestion.md` and `entities/pipeline.md`.
  - [ ] [Medium] Update `concepts/project-linting.md`: Reflect that Biome is now a blocking pre-commit hook.
  - [ ] [Medium] Confirm terminal state of legacy `PENDING` orders and simplify `concepts/alpaca-order-sync.md`.
  - [ ] [Low] Enhance "thin" and "data-gap" pages: `model-anomalies.md` (add examples) and `entities/cleanup.md` (add schedule).
  - [ ] [Low] Fix weak cross-references: Link `type-safety.md` to `biome-linter.md` and `engine.md` to `correlation-matrix-source`.
- [ ] - Benchify: have a portfolio without verificator. Just make sure price is okay and go at it my boy. \
- [ ] -benchify: a second website where the code is managed by AI mostly autonomously?
- [ ] -Benchify: audit price fetching and how we pass it to LLMs
- [ ] - Benchify: for the "question answerer LLM.that I want to implement, what's the best way of RAG?"
- [ ] -Benchify: check if pre-commit hooks work in Jules (qmd)?
- [ ] - Benchify: improve doc summarization/deletion, audit auto wiki. I might have too many docs.

Maybe even separate logs into many files to avoid overloading context. It's "immutable" as in we shouldn't delete from it anyways.

Maybe only use a tool to append to the logs?

- [ ] Benchify: try to predict the next sectors that will perform well?
- [ ] Benchify: audit the verifier.
- [ ] Benchify: have a portfolio without verificator. Just make sure price is okay and go at it my boy.
- [ ] - Show badges for the portfolios with auto-research
- [ ] Benchify: show progression of autoresearch, show the prompt, the score and show historical progress. Show also how we calculate it.

## Under Consideration

- [ ] Benchify: Benchify: mark the portfolios that use autoresearch

- **Market-Closed Activities** - Define valuable tasks for agents when markets are closed (research, backtesting, memory consolidation)
