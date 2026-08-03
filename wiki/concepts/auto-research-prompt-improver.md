---
tags: [auto-research, prompt-improvement, meta-learning]
category: concept
---

# Auto-Research Prompt Improver

A meta-researcher LLM evaluates weekly live trading performance and iteratively improves the trading prompt, following Karpathy's autonomous research pattern. The system modifies only the `CORE_ANALYSIS_SYSTEM_PROMPT` — the system prompt that drives all trading agents.

## Architecture

The auto-research loop runs weekly:
1. **Safety check** — < 2 trades? Revert to previous prompt.
2. **Evaluate** — Compute single score from weekly trading data. Record this score directly on the prompt variant (`P_active`) that actually ran during the week. Find the baseline (best score so far).
3. **Revert on failure** — If score < baseline, revert the active prompt to the baseline. This enforces the Karpathy ratchet: the meta-researcher always builds from the known-good foundation, never from a failed experiment. **Note:** This revert happens chronologically **before** generating the new prompt in Step 4.
4. **Hypothesize** — Meta-researcher LLM proposes prompt changes, building *on top of the post-revert baseline*. **Non-Duplicate Validation**: `run_research()` enforces that `new_prompt_text` MUST NOT be 100% identical to the baseline text. If the LLM proposes an unmutated copy of the baseline (e.g. misinterpreting a revert as outputting duplicate text), the engine retries with feedback demanding a novel mutation or radical alternative so a new hypothesis is always tested on every turn.
5. **Deploy** — Always activate the new variant generated in step 4. Save it as a new database row with empty metrics (`{}`), status `active`, and scheduled for the upcoming week (advanced by 7 days from the prior week). No gate. Every week iterates.
6. **Track** — If score > baseline, this prompt becomes the new baseline.

## Score

```
excess_vs_spy        = portfolio_return% - SPY_return%
excess_vs_donothing  = portfolio_return% - do_nothing_return%
excess_vs_bond       = portfolio_return% - bond_return%
composite_excess     = 0.4 * excess_vs_spy + 0.4 * excess_vs_donothing + 0.2 * excess_vs_bond
score                = composite_excess - (max_drawdown% × 0.3)
```

A single transparent number based on a **Benchmark-Triad Weighted Model**. The meta-researcher evaluates performance against a 100% composite benchmark (40% SPY market, 40% Do-Nothing strategy inertia, 20% 10-year Treasury bond yield), eliminating double penalties while providing a clean 1:1 return optimization signal.

The **Do-Nothing Return** represents the theoretical return of holding the initial portfolio positions throughout the week without making any trades. To ensure pricing accuracy and prevent calculation drift from stale values:
1. **On-Demand Synchronization**: The evaluation engine dynamically pre-populates/updates `price_history` for all held assets at evaluation time via `MarketDataManager.get_history()`. This pulls fresh close prices from the financial provider (FMP), ensuring both active portfolio-specific tickers and legacy positions are correctly valued at the end of the week (`week_end`).
2. **Freshness Guardrail**: The pricing query retrieves the last known price up to `week_end` individually for each asset. It actively validates the age of the retrieved price and logs a `CRITICAL METRIC ERROR` if the price timestamp (`fetched_at`) is older than 4 days before `week_end`, preventing any silent database omissions or stale valuation errors.
3. **Factual Audit Ledger**: The engine compiles a granular ledger of positions (`portfolio_details`) including quantity (`qty`), starting price (`start_price`), starting value (`start_value`), ending price (`end_price`), and ending value (`end_value`). Additionally, it parses the exact fetched dates and hours (`YYYY-MM-DD HH:MM`) of when each start and end price was recorded in the database, allowing users to verify price factualness and account for weekends or market holidays.

The 10-year Treasury yield forms the 20% risk-free component of the triad composite benchmark. The US Dollar Index (DXY/UUP) return is fetched and shown in the weekly report for macroeconomic context but does **not** affect the score.


## Baseline

The baseline is the **highest score achieved so far**, tied to its prompt. The meta-researcher's goal is to propose a prompt that beats the baseline. When it does, that prompt+score becomes the new baseline. When it doesn't, the old baseline holds.

```
Week 1: score=1.5 → Baseline: 1.5 (new best)    → deploy
Week 2: score=2.0 → Baseline: 2.0 (Δ: +0.50) ✓  → deploy
Week 3: score=1.8 → Baseline: 2.0 (Δ: -0.20) ✗  → deploy (baseline stays)
Week 4: score=2.5 → Baseline: 2.5 (Δ: +0.50) ✓  → deploy
```

## Constraints

To protect system stability and parse compatibility, constraints and output formatting rules are frozen. The auto-research runner extracts only the mutable strategy section from the prompt variants and presents it to the researcher. The proposed strategy improvements are automatically recombined with the frozen header/footer constraints (defined in [prompts.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/prompts.py)) before deployment.

The researcher's instructions in [program.md](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/autoresearch/program.md) specify:
- Only modify the strategy and analysis rules section of the prompt
- Keep the prompt under 1000 words
- Compatible with Gemini Flash and DeepSeek Flash

## Pull-Based Tool Selection

To optimize agent prompt length and keep reasoning context concise, the auto-research system operates under a **pull-based** paradigm:
- Rather than pre-injecting the full news list and raw portfolio ledger XML into the user message template, the agent receives a minimal trigger prompt `EXPERIMENT_USER_PROMPT_TEMPLATE` with today's headlines summary menu.
- The agent must use tools like `get_portfolio_ledger` and `get_todays_news_menu` to pull detailed raw contents on-demand.
- The meta-researcher optimizes the agent's strategy and *also* chooses which cognitive tools are enabled for the trading agent during the upcoming week by outputting a list of string names in `selected_tools`.
- **Default Baseline & Fallbacks**: The initial bootstrapped baseline prompt in `bootstrap.py` is configured with default pull tools (`["get_portfolio_ledger", "get_todays_news_menu", "web_search"]`). If an active prompt variant in the database fails to specify a tools list, the engine automatically defaults tool routing to these baseline pull tools to guarantee operational safety.
- **Pull Baseline Isolation**: `get_all_time_baseline()` in `prompt_store.py` explicitly filters candidate variants to require a non-empty `selected_tools` list in `research_output`. This isolates the pull-based evolution cycle from pre-pull legacy push variants (such as `v20260705-221937`), ensuring the meta-researcher always builds on top of pull-native prompt text and tool configurations.

## Isolated Research Loops

While the primary loop targets the `CORE_ANALYSIS_SYSTEM_PROMPT` to refine full-portfolio strategies, the auto-research runner supports fully isolated prompt evaluation cycles. 
Specifically, the **AI Sector Predictor and Model Arena** uses the prompt name `SECTOR_PREDICTOR_PROMPT`. The predictor-specific evaluation and meta-evolution loops only retrieve, mutate, and store variants belonging to this tag, preventing strategy leaks or baseline dilution between different autonomous engines.

## Design Philosophy

- **Always explore**: Every week deploys a new prompt. The meta-researcher always gets to test its ideas.
- **Hard ratchet**: When an experiment fails to beat the baseline, the active prompt is reverted to the baseline BEFORE the next experiment runs. The meta-researcher always builds from the known-good foundation — never from a failed experiment. This is enforced at the code level in `runner.py`, not just as instructions to the LLM.
- **Baseline only moves up**: The target is the best score achieved. No chasing regressed targets.
- **Trust the process**: No validator. The safety checker catches crashes; control portfolios provide reference. The meta-researcher learns from outcomes.
- **Single metric**: One number to optimize eliminates gaming of composite weights.
- **Transparent components**: The LLM sees why the score moved, not just that it moved.

## Related

- [[entities/autoresearch]] — the implementation module
- [[entities/engine]] — the parent engine
