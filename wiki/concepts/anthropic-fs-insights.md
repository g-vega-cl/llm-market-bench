---
tags: [architecture, tools, predictor, autoresearch, synthesis, insights]
category: concept
---

# Anthropic FSI Insights & Tool-First Implementation Architecture

Synthesized insights from Anthropic's [`financial-services`](https://github.com/anthropics/financial-services) repository and the strategic plan for integrating domain analytics into `llm-market-bench` while upholding our **Tool-First, Agency-Driven Architecture**.

## 1. Core Architectural Principle: Tools Over Prompt Forcing

A foundational pillar of `llm-market-bench` is **Information Auditability and Agentic Autonomy**:

1. **Anti-Prompt-Forcing**: We do NOT bloat system prompts by pre-injecting massive static tables of unrequested data. Pre-injecting 50+ raw metrics causes attention dilution ("Lost in the Middle"), inflates token cost, and prevents the model from developing hypothesis-driven exploration.
2. **Tools as Units of Discovery**: Capabilities are packaged as callable tools in the canonical tool registry (`packages/config/tools.json` and `apps/engine/core/llm/tools.py`). The LLM is provided with a lean context and decides *which* tools to call based on the problem at hand.
3. **Autoresearch-Driven Tool Adoption**: In the Karpathy autoresearch loop, the meta-researcher tests and discovers tool-usage patterns via modular prompt blocks (`apps/engine/autoresearch/prompt_blocks.py`). The autoresearcher iteratively proves whether adopting a tool improves the composite Ratchet Score, Brier calibration, and magnitude capture.

---

## 2. Tool Packaging Plan: Translating FSI Insights into Discoverable Tools

Rather than hardcoding calculations into prompt text, we package Anthropic's best financial analytical patterns as 4 specialized tools:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             CANONICAL TOOL REGISTRY                         │
│                           (packages/config/tools.json)                      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         │                             │                             │
┌────────▼──────────────┐   ┌──────────▼───────────┐   ┌─────────────▼──────────────┐
│ get_options_vol_surface│   │ get_yield_curve_regime│  │ track_thesis_pillars      │
│ • ATM IV & Realized Vol│   │ • 2Y/10Y, 3M/10Y Slopes│  │ • Multi-day Thesis Ledger  │
│ • Implied Vol Premium  │   │ • 4-Regime Taxonomy   │  │ • Disconfirming Evidence   │
│ • Daily Move Cone      │   │ • Historical Beta Map │  │ • Conviction Transitions   │
│ • 25d Skew & Smile     │   │                       │  │                            │
└───────────────────────┘   └──────────────────────┘   └────────────────────────────┘
```

### A. `get_options_vol_surface(ticker: str)`
* **Inspiration**: `plugins/partner-built/lseg/skills/option-vol-analysis`
* **Functionality**:
  - Calculates ATM IV, 20d & 60d historical realized volatility, and the Implied Volatility Premium ($IV - RV_{20\text{d}}$).
  - Calculates the **Options-Implied Daily Move**:
    $$\text{Daily Implied Move} = \text{Spot} \times \left(\frac{\sigma_{\text{ATM}}}{\sqrt{252}}\right)$$
  - Returns 25-delta Risk Reversal (skew) and 25-delta Butterfly (smile curvature/tail hedging).
* **Agent Usage**: Analysis and prediction agents call this tool when calibrating price targets or checking whether an intraday breakout has options market backing.

### B. `get_yield_curve_regime()`
* **Inspiration**: `plugins/partner-built/lseg/skills/macro-rates-monitor`
* **Functionality**:
  - Evaluates FRED and market Treasury yields (3M, 2Y, 5Y, 10Y, 30Y).
  - Computes curve slope dynamics and 5-day delta.
  - Classifies the macroeconomic regime into: `BULL_STEEPENER`, `BEAR_STEEPENER`, `BULL_FLATTENER`, or `BEAR_FLATTENER`.
  - Maps regime-specific sector rotation tendencies (Growth vs Value, Small vs Large Cap).
* **Agent Usage**: Agents call this tool during macro news releases or morning planning to align sector bets with monetary flow regimes.

### C. `track_thesis_pillars(ticker: str, action: "get" | "update" | "disconfirm", ...)`
* **Inspiration**: `plugins/vertical-plugins/equity-research/skills/thesis-tracker`
* **Functionality**:
  - Reads or updates persistent multi-day thesis cards in `memories` / `cause_and_effect` tables.
  - Enforces 3–5 falsifiable pillars and a mandatory check for **disconfirming evidence**.
  - Tracks conviction status (`CONFIRMED`, `WEAKENED`, `INVALIDATED`).
* **Agent Usage**: Long-horizon trading agents invoke this tool to prevent recency bias and test if existing holdings should be held, trimmed, or exited.

### D. `get_scenario_bounds(ticker: str)`
* **Inspiration**: `plugins/vertical-plugins/equity-research/skills/earnings-preview`
* **Functionality**:
  - Computes conditional Bull / Base / Bear scenarios using implied move, VWAP standard deviation bands, and trailing ATR.
  - Returns asymmetric risk-reward bounds.

---

## 3. Autoresearch Integration: Modular Prompt Blocks

To allow the Karpathy autoresearch loop to discover and adopt these tools organically, we create modular prompt blocks in `apps/engine/autoresearch/prompt_blocks.py`:

1. `BLOCK_OPTIONS_VOL_DISCIPLINE`: Instructs the agent to call `get_options_vol_surface` before issuing price targets to enforce bounds checking against market-implied standard deviation cones.
2. `BLOCK_MACRO_REGIME_ROUTING`: Teaches the agent to query `get_yield_curve_regime` when macro/Fed catalysts are active.
3. `BLOCK_DISCONFIRMING_EVIDENCE_GATE`: Requires the agent to query `track_thesis_pillars` and state at least one disconfirming factor before increasing exposure.

The auto-researcher tests prompt variations with and without these blocks, measuring their empirical impact on the multi-factor ratchet score:
$$\text{Ratchet Score} = (0.55 \times \text{close\_acc}) + (0.35 \times \text{target\_hit}) + (0.10 \times \text{magnitude\_cap}) - (\text{mean\_brier} \times 50.0)$$

---

## 4. Web UI & Investment Chat Enhancements

1. **High-Density Ticker Tear Sheets (`/tickers/$ticker`)**: Visualizes fundamental multiples, PEAD/SUE signals, Sloan accruals, volatility cones, and model consensus in an institutional 4-quadrant layout.
2. **Scenario Matrix & Volatility Cones**: Renders interactive Bull / Base / Bear target cones on prediction cards.
3. **Attribution Waterfall Cards**: Root-cause post-mortems classifying prediction misses into Macro Shock, Gap Exhaustion, or Magnitude Overshoot.
4. **Chat Gateway Slash Commands**: Interactive slash commands in `/chat` (`/vol SPY`, `/regime`, `/thesis AAPL`, `/pead`) executing the exact same backend tools.

---

## 5. Market Fit Strategy

1. **LMSYS Chatbot Arena for Finance**: Establish `llm-market-bench` as the definitive, forward-tested benchmark for LLM financial reasoning with live Brier calibration and zero data contamination.
2. **Open MCP Quantitative Endpoints**: Expose our quantitative engines (PEAD, Macro Regime, Barometer, Autoresearch) as standard MCP servers (`mcp.llmmarketbench.com`), enabling enterprise Claude/ChatGPT users to connect to our platform.
3. **Commercial Briefings API**: Monetize automated morning/evening consensus newsletters and bellwether alerts via webhooks and email subscriptions.

## Related

- [[sources/anthropic-financial-services-source]] — Upstream repository analysis
- [[entities/tool-registry]] — Canonical tool registry
- [[entities/daily-market-predictor]] — Daily S&P 500 predictor
- [[entities/sector-predictor-arena]] — Sector predictor arena
- [[entities/autoresearch]] — Autonomous prompt mutation engine
- [[entities/investment-chat-gateway]] — Gated conversational terminal
