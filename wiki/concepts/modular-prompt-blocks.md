---
tags: [concept, prompt, modular-blocks, autoresearch]
category: concept
---

# Modular Prompt Blocks

Reusable trading discipline and reasoning blocks dynamically toggled by the Auto-Researcher LLM to test prompt variations. Each block is registered in `AVAILABLE_PROMPT_BLOCKS` and corresponds to a distinct reasoning pattern, risk check, or catalyst verification step.

## Available Blocks

| Block ID | Purpose |
|----------|---------|
| `let_winners_run` | Enforce trailing stop relaxation for high-momentum positions |
| `cut_losers_fast` | Aggressive loss-tightening below VWAP or key MA |
| `catalyst_expiry_timer` | Explicit expiry date tracking for event-driven positions |
| `five_whys_causal` | Deep causal drilldown on drawdowns and reversals |
| `mece_risk_partition` | MECE partitioning of portfolio risk factors |
| `options_vol_discipline` | Options-specific volatility bounding and IV rank checks |
| `macro_regime_routing` | Sector rotation based on macro regime signals |
| `disconfirming_evidence_gate` | Explicit disconfirming evidence checks and conviction downgrades |
| `catalyst_radar_discipline` | Pre-trade catalyst scan and asymmetric event volatility timing |
| `forward_calendar_scenario_anticipation` | Forward-looking positioning for scheduled catalysts with scenario plans |
| `ticker_news_verification` | On-demand ticker news verification for candidate assets before committing capital, filtering noise from concrete material catalysts |

## Implementation

Blocks live in `apps/engine/autoresearch/prompt_blocks.py` as dict entries with `title` and `content` keys. The researcher selects a subset via `selected_prompt_blocks` field in `PromptResearchResult`.

## Related

- [[concepts/auto-research-prompt-improver]]
- [[concepts/modular-prompt-blocks]]
