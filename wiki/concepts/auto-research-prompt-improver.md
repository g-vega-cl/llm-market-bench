---
tags: [concept, autoresearch, prompt-improver, meta-research]
category: concept
---

# Auto-Research Prompt Improver

Weekly autonomous prompt iteration via a meta-researcher LLM. The system evaluates live trading performance over the past week and generates an improved trading prompt for the next week.

## Mechanism

1. The meta-researcher (`apps/engine/autoresearch/researcher.py`) receives the current trading prompt, recent performance metrics, and the list of available tools and modular prompt blocks.
2. It proposes changes: which tools to include, which prompt blocks to enable, and a free-form change description.
3. The new prompt and block selection are persisted to the database for the next trading cycle.

## Modifiable Elements

The researcher can toggle:

- **Pull tools**: The list of non-execution tools available to the analysis agent (e.g., `get_portfolio_ledger`, `get_todays_news_menu`, `get_ticker_news`, `web_search`, and many more). Execution tools (`calculate_buy_quantity`, `calculate_sell_quantity`) are force-injected and not togglable.
- **Prompt blocks**: Enable/disable any of the modular discipline blocks (`let_winners_run`, `cut_losers_fast`, `catalyst_expiry_timer`, `five_whys_causal`, `mece_risk_partition`, `options_vol_discipline`, `macro_regime_routing`, `disconfirming_evidence_gate`, `catalyst_radar_discipline`, `forward_calendar_scenario_anticipation`, `ticker_news_verification`).

## Related

- [[concepts/modular-prompt-blocks]]
- [[entities/autoresearch]]
