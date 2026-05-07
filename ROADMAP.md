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
- [ ] **Revisit the concepts map** -
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
- [ ] **Kaparthy method would improve my rag?**
- [ ] **I like the chatgpt setup of "ask the next best question" like**. Show me a couple of options of what the next best thing to ask would be
- [ ] **Make sure we save the historical correlation/returns table/matrix**
- [ ] **Include extra sources of "true" not subjective data? Satellite images, weather, etc... research what's usually used for this.**
- [ ] **Company earnings not really (that's a different point) but a way of predicting the earnings?**
- [ ] **A tracker of your chats with LLMs to track productivity. Enterprise Software?** Openrouter might already have this.
- [ ] **In my comparision chart, the dotted line had some weird vertical lines that shouldn't be there**
- [x] **Add design system code vertical.** — Implemented in `packages/ui-design-system/`. See [DESIGN_SYSTEM.md](./docs/web/DESIGN_SYSTEM.md).
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
- [x] - benchify: Make a "style vibe" ... — The design system (semantic gradients, typography: Space Grotesk + Satoshi + JetBrains Mono, component primitives) is in `packages/ui-design-system/`. Applied across all feature pages. See [DESIGN_SYSTEM.md](./docs/web/DESIGN_SYSTEM.md).

## Under Consideration

- **Market-Closed Activities** - Define valuable tasks for agents when markets are closed (research, backtesting, memory consolidation)
