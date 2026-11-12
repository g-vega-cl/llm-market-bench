# Roadmap

A living document of features and improvements in progress or planned for the platform.

---

## ⚡ Horizon 1: Immediate Focus (Now)

### Autoresearch & Prompt Evolution (Local Loop)

- [x] - Set up a local auto researcher with Qwen, Strata, and Jev. Evaluated across 10-batch (300 iterations) tournament on 2-year multi-regime dataset (507 days, 106 weeks). Revealed that unconstrained open-to-close daily direction caps at ~52% due to random walk noise and selectivity subsidy trap. Post-mortem documented at [[concepts/daily-directional-predictability-limits]].
- [ ] - Benchify: something I can autoresearch daily?
      Maybe 4h candles and statistics with news context? Maybe the news can be summarized from the newsletters and that can also be autoresearched optimized
- [ ] - **Inject Quantitative Microstructure Features**: Ingest dealer options gamma positioning (GEX flip levels), morning NYSE Tick cumulative volume delta, and pre-open auction imbalances into the feature cache to provide genuine quantitative state-space beyond raw EOD bars.

### Website Overhaul & UI/UX (PostHog / Voxel)

- [ ] - My site looks just like every other LLM-made site. Let's improve it.
- [x] - Benchify: use unlightouse to audit our whole site and fix.
 - Do consistently, last time Done 2026/11/06

### Marketing & Building in Public

- [ ] - Benchify: start building in public. Maybe videos maybe blogs anything but start saying the things you think about that loud critique YouTube videos critique other creators or say something good about them too. Audit audit audit
- [ ] - Benchify: publish your plan for marketing and results. Make it PostHog focused
- [ ] - Benchify; can you beat the agent game
  - [ ] - Benchify: challenge people to predict daily weekly etc to produce sectors to predict etc better than you and if they consistently win give them money and they get half and you get half or you can just like a little fee and to get something etc

---

## 🚀 Horizon 2: Near-Term Expansion (Next)

### Autoresearch Scaling & Local Models

- [x] - in finance is better to be 100% confident and right in one prediction that usually confident and right on many predictions/What's the best way to set up an autoresearcher about this?
- [x] - So allow hold? improve the confidence number?

### Portfolio & Market Execution

- [ ] - **Market-Closed Activities** - Define valuable tasks for agents when markets are closed (research, backtesting, memory consolidation)
 - This is kindof part of the pivot I'm looking to do, maybe a different category?

### Database & Performance Polish

- [ ] **Premium Semantic Memory Search (Approach 3)** - Implement server-side vector embedding (`text-embedding-004`) + `match_memories` pgvector RPC for thematic conceptual discovery ("rate cuts" -> "dovish Fed"). Caveat: Requires runtime LLM embedding API call per search query; reserve as a premium/pro tier capability.
- [ ] - Benchify: move all newsletters to dedicated email
- [ ] - Benchify: scrape news from all time (historical backfill).
- [x] - Benchify: research every stock/sector mentioned in newsletters individually and decide if it would be worth investing in it. Save all these research reports in a DB where users could "look up all information about X company"

---

## 🔬 Horizon 3: Quantitative & Alternative Alpha (Medium-Term)

### Quantitative Models & Statistical Alpha

- [ ] **Money Flow Model** - Make a model (based on financial papers) to track money flows.
- [ ] **Statistical Predictions** - Implement Monte Carlo simulations, Random Forest, and other ML-based prediction models
- [ ] - Look for statistical analysis for markets
- [x] - Benchify; a daily stock picker, which stocks will go up today? And pick 3 up and 3 down.
- [ ] - Benchify: train small model?

### Focused Assets (Single Ticker / ETF)

- [ ] - Single company focused llm - Did this with LIN, but I don't think it's working as expected. REVISIT. - [ ] - Benchify: "hyperfocus on a mid size company? - [ ] - Benchify: just trade one ETF on one auto researcher. Maybe the Focus on a single company related to this?

### Government, Fiscal & Alternative Data

- [ ] - audit all government information you have and how you are using it.
- [ ] - Benchify: Toronto stock market

### Multimodal & Visual Market Prediction

---

## 🌐 Horizon 4: Product, Platform & Community (Long-Term)

### Community & Multi-Tenant Features

- [ ] - Benchify allow people to use their own models/keys/prompts and compete.
- [ ] - Benchify: per user log and reasons tracker. This ties to the LLM chat. Each user can track their own trades too and their reasoning.
- [ ] - I like the idea of a "finacial/trading" benchmark for agents.
- [ ] - Benchify: What about making a benchmark for day trading/investing?
- [ ] - Benchify: build your AI trading strategy online (algobuilder.com, switchmarkets.com?)
  - [ ] - Kind of like a visual Unsloth dashboard?

### Gamifying

- [ ] - Benchify; can you beat the agent game
  - [ ] - Benchify: challenge people to predict daily weekly etc to produce sectors to predict etc better than you and if they consistently win give them money and they get half and you get half or you can just like a little fee and to get something etc

### Autonomous Agents & Meta-Intelligence

- [ ] - Benchify: start a "CEO" agent. With a self-loop
- [x] - Strata: 24/7 business fit researcher
- [ ] **A programming/business buddy?**
  - Clippy (I already have something similar ) but that suggests improvements to the app. Just brainstorming the concept

---

## 🎨 Horizon 5: Creative Labs & Experiments (Moonshots)

- [ ] - Duolingo but with crypto? Take an app that already exists but "crypto"
- [ ] - Other: build my own job applier/aggregator.
- [ ] - General: Make a "my style" coder that is AI-detection proof.
  - same with text
- [ ] - Benchify : fun idea. Every morning do some kind of praying to the market God's funny tiktok video showing your prediction and kind of begging to the gambling gods allow you to win some money.
- [ ] - Random: Toronto rank councilors and what they do and categorize them
- [ ] - Benchify: research pivot? Maybe stock prediction is way over my head. But maybe I can mix my other loves - policy, economics, socials in real life, supplements, games/strategy,  chemical engineering, anti nepotism, writing/cinema/art/books, history, gym, AI, etc...

---

