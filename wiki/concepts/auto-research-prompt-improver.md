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
4. **Hypothesize** — Meta-researcher LLM proposes prompt changes, building *on top of the post-revert baseline*.
5. **Deploy** — Always activate the new variant generated in step 4. Save it as a new database row with empty metrics (`{}`), status `active`, and scheduled for the upcoming week (advanced by 7 days from the prior week). No gate. Every week iterates.
6. **Track** — If score > baseline, this prompt becomes the new baseline.

## Score

```
hurdle_pct     = bond_return_pct  (compounded 10-year Treasury yield)
opp_cost       = max(0.0, hurdle_pct - portfolio_return%)
excess_return  = (portfolio_return% - SPY_return%) + (portfolio_return% - do_nothing_return%)
score          = excess_return - opp_cost - (max_drawdown% × 0.3)
```

A single transparent number. The meta-researcher sees all components (portfolio return, SPY return, bond hurdle, opportunity cost penalty, drawdown) plus the baseline and Δ.

The **Do-Nothing Return** represents the theoretical return of holding the initial portfolio positions throughout the week without making any trades. To ensure pricing accuracy and prevent calculation drift from stale values:
1. **On-Demand Synchronization**: The evaluation engine dynamically pre-populates/updates `price_history` for all held assets at evaluation time via `MarketDataManager.get_history()`. This pulls fresh close prices from the financial provider (FMP), ensuring both active portfolio-specific tickers and legacy positions are correctly valued at the end of the week (`week_end`).
2. **Freshness Guardrail**: The pricing query retrieves the last known price up to `week_end` individually for each asset. It actively validates the age of the retrieved price and logs a `CRITICAL METRIC ERROR` if the price timestamp (`fetched_at`) is older than 4 days before `week_end`, preventing any silent database omissions or stale valuation errors.

The 10-year Treasury yield is the sole active risk-free hurdle — the portfolio must clear it to avoid an opportunity cost penalty. The US Dollar Index (DXY/UUP) return is fetched and shown in the weekly report for macroeconomic context but does **not** affect the score.


## Baseline

The baseline is the **highest score achieved so far**, tied to its prompt. The meta-researcher's goal is to propose a prompt that beats the baseline. When it does, that prompt+score becomes the new baseline. When it doesn't, the old baseline holds.

```
Week 1: score=1.5 → Baseline: 1.5 (new best)    → deploy
Week 2: score=2.0 → Baseline: 2.0 (Δ: +0.50) ✓  → deploy
Week 3: score=1.8 → Baseline: 2.0 (Δ: -0.20) ✗  → deploy (baseline stays)
Week 4: score=2.5 → Baseline: 2.5 (Δ: +0.50) ✓  → deploy
```

## Constraints

The researcher's `program.md` specifies:
- Only modify the `CORE_ANALYSIS_SYSTEM_PROMPT`
- Do NOT remove tool usage requirements
- Do NOT add instructions to output price fields (prices are system-provided)
- Keep the prompt under 1000 words
- Compatible with Gemini Flash and DeepSeek Flash

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
