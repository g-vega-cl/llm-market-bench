# Roadmap

A living document of features and improvements in progress or planned for the platform.

---

## ⚡ Horizon 1: Immediate Focus (Now)

### Autoresearch & Prompt Evolution (Local Loop)
- [ ] - Set up a local auto researcher with Qwaen and Strava and jev. That means that since Jeb is so cheap, I can just run it all night with Qwen and Strava running locally in my computer and it iterating over and over until my prompt is excellent and it can predict the daily movement with great accuracy and no overfitting. It's basically an attempt to improve my prompt consistently with autoresearch. The qwen autoresearcher should have access to my database and tools. It should also be able to create memories itself, (although maybe with some tag that says it comes from autoresearch, and maybe also store it on my local db so it doesn't cram supabase while autoresearching since some memories mught prove counterproductive and need to be deleted)
- [ ] - Benchify: jev + Qwen autoresearcher? Jev can do so many things like judge, decide which prompt is better, check for over fitting, check if the input is correct, etc
- [ ] - Benchify: could jev work for my autoresearcher?

    Speculative Fanout: Ask multiple questions in a single query and get all of them answered in parallel. For example: triage a support ticket and assess its type, severity, frustration level etc.

    Confidence Gated Routing: Jev can generate confidence scores that can be used to route to different actions. If you are highly confident you can take the action directly, or if you have low confidence, you can add a user prompt to clarify.

    Composite Scoring: Give Jev a rubric, and it can give a composite score to all
- [ ] - Many of these things should be able to be picked up by autoresearch, I guess the loop is quite slow. How to speed up the loop?
- [ ] - Benchify: Autoresearch, make it so it can decide if it should remove data from emails or others. Allow it to see the input blocks and decide if it should remove or add inputs.
- [ ] - Benchify: something I can autoresearch daily?
        Maybe 4h candles and statistics with news context? Maybe the news can be summarized from the newsletters and that can also be autoresearched optimized

### Website Overhaul & UI/UX (PostHog / Voxel)
- [ ] - update my site so it feels like a proper-professional website, I have to overhaul the design system, the navbar, the pages themselves. So it has a clear objective, and users can use it intutively and so it can be an "impressive portfolio piece" and a "great business". and it must not feel designed like an "AI gebnerated" website. I like the "Voxel" style, or the "posthog" style, but let's discuss.
- [ ] - My site looks just like every other LLM-made site. Let's improve it.
- [ ] - Benchify: when remaking and updating design system. Make sure sidebar is only 4 items tops. Maybe change the items based on frequency of use?
- [ ] - Benchify: Our portfolios comparision graph shows the names of the portfolios twice, once at the selection and once at the top of the chart. We just need to have it once.
- [ ] - Benchify: avoid JS for designs, use CSS whenever possible. Grid flex are so good
- [ ] - Benchify: use unlightouse to audit our whole site and fix.
- [ ] - Benchify: update today page
- [ ] - Benchify: today page how's the AI feeling is being crowded or confused by systematic portfolios
- [ ] - Benchify: improve the follow a single thought, add dates, the model process, adapt the card and carousel to proper size or remove it. Make it a real that you can change.

### Marketing & Building in Public
- [ ] - Benchify: start building in public. Maybe videos maybe blogs anything but start saying the things you think about that loud critique YouTube videos critique other creators or say something good about them too. Audit audit audit
- [ ] - Benchify: publish your plan for marketing and results. Make it PostHog focused

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
- [ ] - Benchify: a bond trader?
- [ ] - **Market-Closed Activities** - Define valuable tasks for agents when markets are closed (research, backtesting, memory consolidation)
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
- [ ] - Benchify: train small model?

### Focused Assets (Single Ticker / ETF)
- [ ] - Single company focused llm - Did this with LIN, but I don't think it's working as expected. REVISIT.
        - [ ] - Benchify: "hyperfocus on a mid size company?
        - [ ] - Benchify: just trade one ETF on one auto researcher. Maybe the Focus on a single company related to this?

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

- [x] **Find trading papers not just investing** - But low sell high?
  - Couldn't find any.
- [x] - benchify: Make a "style vibe" ... — The design system (semantic gradients, typography: Space Grotesk + Satoshi + JetBrains Mono, component primitives) is in `packages/ui-design-system/`. Applied across all feature pages. See [DESIGN_SYSTEM.md](./raw/docs/web/DESIGN_SYSTEM.md).
- [x] - Benchify: Enforce "Zero Compute on Frontend" in `searchMemories()` (`apps/web/src/features/memories/api/fetch-memories.ts`). Replace the unpaginated full-table query (3,144 rows + embeddings = ~18.8MB) and client-side Levenshtein loop with database-level text filtering and pagination.
- [x] - Benchify; make an statistic if any of our buys were ever profitable. Like what if I followed my agent's buys and decide on the sells myself?
    - Did this, I think it was basically a 50/50 bet. Even I checked if it ever touched something like .5% or .1% and it didn't change it much.
- [x] - Benchify: I might already have something like this, try to predict earnings movement. Maybe just up/down from beginning of trading day?
    - Built Day-1 Earnings Movement Predictor Arena benchmarking GPT Luna (gpt-5.6-luna), DeepSeek Flash (deepseek-chat), and TypeSafe Jev (~typesafe/jev-latest) on Regular Trading Hours Open-to-Close (09:30 to 16:00 ET) continuation vs fade reactions. Created `earnings_predictions` table, `earnings_predictor.py`, `evaluate_earnings_predictions.py`, and `EarningsArenaTab` UI in `/earnings-audit`.
- [x] - Benchify: 2 week sector predictor and check how different are the weekly/monthly/90d predictions from each other..
      - Did this.  It's mostly the same.
