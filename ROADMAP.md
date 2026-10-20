# Roadmap

A living document of features and improvements in progress or planned for the platform.

---

## ⚡ Horizon 1: Immediate Focus (Now)

### Autoresearch & Prompt Evolution (Local Loop)

- [x] - Set up a local auto researcher with Qwen, Strata, and Jev. Evaluated across 10-batch (300 iterations) tournament on 2-year multi-regime dataset (507 days, 106 weeks). Revealed that unconstrained open-to-close daily direction caps at ~52% due to random walk noise and selectivity subsidy trap. Post-mortem documented at [[concepts/daily-directional-predictability-limits]].
- [ ] - Benchify: something I can autoresearch daily?
      Maybe 4h candles and statistics with news context? Maybe the news can be summarized from the newsletters and that can also be autoresearched optimized
  - [ ] - **Shorten Prediction Horizon (Opening Drive Alpha)**: Transition prediction target from 09:30 -> 16:00 ET (6.75 hours of unobserved intraday noise) to Opening Drive (09:30 -> 10:30 ET) or First-Hour Breakout where pre-market tape and overnight gap information carry maximum explanatory power before midday decay.
- [ ] - **Inject Quantitative Microstructure Features**: Ingest dealer options gamma positioning (GEX flip levels), morning NYSE Tick cumulative volume delta, and pre-open auction imbalances into the feature cache to provide genuine quantitative state-space beyond raw EOD bars.
- [ ] - Benchify: remove anti bias from frozen, those are not "format" instructions those affect the prediction so they should be able to be mutated

### Website Overhaul & UI/UX (PostHog / Voxel)

- [ ] - update my site so it feels like a proper-professional website, I have to overhaul the design system, the navbar, the pages themselves. So it has a clear objective, and users can use it intutively and so it can be an "impressive portfolio piece" and a "great business". and it must not feel designed like an "AI gebnerated" website. I like the "Voxel" style, or the "posthog" style, but let's discuss.
- [ ] - My site looks just like every other LLM-made site. Let's improve it.
- [ ] - Benchify: when remaking and updating design system. Make sure sidebar is only 4 items tops. Maybe change the items based on frequency of use?
- [ ] - Benchify: avoid JS for designs, use CSS whenever possible. Grid flex are so good
- [ ] - Benchify: use unlightouse to audit our whole site and fix.
- [ ] - Benchify: update today page
- [ ] - Benchify: today page how's the AI feeling is being crowded or confused by systematic portfolios
- [ ] - Benchify: improve the follow a single thought, add dates, the model process, adapt the card and carousel to proper size or remove it. Make it a real that you can change.
- [ ] - Benchify: update tanstack
- [ ] - Benchify : design rules cheat sheet to ground my design system

### Marketing & Building in Public

- [ ] - Benchify: start building in public. Maybe videos maybe blogs anything but start saying the things you think about that loud critique YouTube videos critique other creators or say something good about them too. Audit audit audit
- [ ] - Benchify: publish your plan for marketing and results. Make it PostHog focused
- [ ] - Benchify: a stream of an agent trading basically 24/7. The agent can't be the agent in my computer.
- [ ] - Benchify: let people give instructions to the 24/7 trader
- [ ] - Benchify; can you beat the agent game

---

## 🚀 Horizon 2: Near-Term Expansion (Next)

### Autoresearch Scaling & Local Models

- [ ] - add a local model?
- [p] - Benchify: set up Laya alongside JEV?
- [ ] - make an autoresearcher for the verifier
- [ ] - make autoresearcher with more variables and more "temperatures?" More portfolios too?
- [ ] - Benchify: find the cheapest models and make a little autoresearch army that uses weekly rolling to update.
- [ ] - benchify: fine tune the autoresearcher rather than the model?
- [ ] - in finance is better to be 100% confident and right in one prediction that usually confident and right on many predictions/What's the best way to set up an autoresearcher about this?

### Portfolio & Market Execution

- [ ] - Benchify: Allow portfolios to "invest cash" in "bonds" and get a return for unused cash.
- [ ] - **Market-Closed Activities** - Define valuable tasks for agents when markets are closed (research, backtesting, memory consolidation)
- [ ] - Benchify; the portfolios should all run with 10k and no margin. Easier to get and also no dealing with interest
- [ ] - Benchify, time to add your own portfolio? What about your agents portfolio?

### Database & Performance Polish

- [ ] - Benchify: Strip invisible vector egress (`embedding` column) from `apps/web`. Replace `.select('*')` with explicit scalar column projections across `memories` and `decisions` queries in `fetch-memories.ts`, `fetch-today-data.ts`, and `fetch-cause-and-effect.ts`.
- [ ] **Premium Semantic Memory Search (Approach 3)** - Implement server-side vector embedding (`text-embedding-004`) + `match_memories` pgvector RPC for thematic conceptual discovery ("rate cuts" -> "dovish Fed"). Caveat: Requires runtime LLM embedding API call per search query; reserve as a premium/pro tier capability.
- [ ] - Benchify: move all newsletters to dedicated email

---

## 🔬 Horizon 3: Quantitative & Alternative Alpha (Medium-Term)

### Quantitative Models & Statistical Alpha

- [ ] **Money Flow Model** - Make a model (based on financial papers) to track money flows.
- [ ] **Statistical Predictions** - Implement Monte Carlo simulations, Random Forest, and other ML-based prediction models
- [ ] - Look for statistical analysis for markets
- [ ] - Benchify: follow the crowd strategy? Like using options and volume data?
- [ ] - Benchify: instead of daily up/down/ammount predictor. A "will it hit this option strike at any point during the day"? Like, will the option be ON The Money at any time? And which options? Maybe we can start with fixed? - Actually, might be kind of the same thing
- [ ] - Benchify: an option targeter? A predictor that says "in X amount of time, this stock will move Y"
- [ ] - Benchify; a daily stock picker, which stocks will go up today? And pick 3 up and 3 down.
- [ ] - Benchify: train small model?

### Focused Assets (Single Ticker / ETF)

- [ ] - Single company focused llm - Did this with LIN, but I don't think it's working as expected. REVISIT. - [ ] - Benchify: "hyperfocus on a mid size company? - [ ] - Benchify: just trade one ETF on one auto researcher. Maybe the Focus on a single company related to this?

### Government, Fiscal & Alternative Data

- [ ] - add money printing/creation/fiscal deficits of governments to the sytem. Track government spending and deficits closely. Same with corporate spending.
- [ ] - Try to track government stuff again, but make it explicit, make it maybe outside ingestion and consensus.
- [ ] - Benchify: track specific governments with liquid enough stock markets like Canada and trade based on government deals and pipelines and government money
- [ ] - Erica said that in Canada you could have clear insider trading because there is a gradual buying leading to news, so we could tap into this.
- [ ] - An LLM that focuses only on government opportunities. - Like deals in pipeline, new reforms, under the radar things
- [ ] - Benchify: add institutional buying and Congress buying?
- [ ] - Benchify: Toronto stock market

### Multimodal & Visual Market Prediction

- [ ] - What about a "visual" screenshot of charts and ask for candlestick/trading patterns?
- [ ] - visual predictor- Somethuing like https://huggingface.co/foduucom/stockmarket-pattern-detection-yolov8 or even a minute-by-minute/ or short time x short time predictor of the market. Not necessarily visual, but it would be great to compare results of visual/non-visual.

---

## 🌐 Horizon 4: Product, Platform & Community (Long-Term)

### Community & Multi-Tenant Features

- [ ] - Benchify allow people to use their own models/keys/prompts and compete.
- [ ] - Benchify: per user log and reasons tracker. This ties to the LLM chat. Each user can track their own trades too and their reasoning.
- [ ] - I like the idea of a "finacial/trading" benchmark for agents.
- [ ] - Benchify: What about making a benchmark for day trading/investing?
- [ ] - Benchify: market data free APIs?
- [ ] - Benchify: free APIs to the LLMs chat?
- [ ] - Benchify, time to add your own portfolio? What about your agents portfolio?

### Gamifying

- [ ] - Benchify: a stream of an agent trading basically 24/7. The agent can't be the agent in my computer.
  - [ ] - Benchify: let people give instructions to the 24/7 trader
- [ ] - Benchify; can you beat the agent game
  - [ ] - Benchify: challenge people to predict daily weekly etc to produce sectors to predict etc better than you and if they consistently win give them money and they get half and you get half or you can just like a little fee and to get something etc

### Autonomous Agents & Meta-Intelligence

- [ ] - Benchify: start a "CEO" agent. With a self-loop
- [ ] - Benchify: an autoresearch autoresearcher?
- [ ] **A programming/business buddy?**
  - Clippy (I already have something similar ) but that suggests improvements to the app. Just brainstorming the concept

---

## 🎨 Horizon 5: Creative Labs & Experiments (Moonshots)

- [ ] - Duolingo but with crypto? Take an app that already exists but "crypto"
- [ ] - General: Make a "my style" coder that is AI-detection proof.
  - same with text
- [ ] - Benchify : fun idea. Every morning do some kind of praying to the market God's funny tiktok video showing your prediction and kind of begging to the gambling gods allow you to win some money.

---

## ✅ Completed & Evaluated (Archive)
