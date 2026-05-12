---
tags: [entity, auto-research, prompt-improvement]
category: entity
---

# Auto-Research Module

The `apps/engine/autoresearch/` module implements the Karpathy-style autonomous prompt improvement loop. It consists of:

- `program.md` — the meta-researcher's instructions (constraints and goals)
- `validator.py` — post-validation of proposed prompts (hard invariants only)
- `runner.py` — orchestrates the weekly evaluation and deployment cycle

## Key Design Decisions

- **Only the trading prompt is modified**: Tools, portfolio rules, execution logic, and verification prompts remain unchanged
- **Hard invariants only**: The validator blocks only dangerous patterns (empty, oversized, price-guessing prompts). No soft requirements — the prompt is an experiment space
- **Control portfolios benchmark**: The researcher is free to experiment; the control portfolios and safety checker provide the real guardrails

## Recent Changes

- **2025-04-04**: Removed soft invariant enforcement (calculate_buy_quantity, calculate_sell_quantity, 5 Whys). The validator now only checks hard invariants.
- **2026-05-12**: Fixed two query bugs:
  - `price_history` end-of-day filtering: VIXY/SPY regime queries and SPY benchmark queries now use `T23:59:59` instead of cutting off at midnight
  - `get_baseline_metrics()` ordering: changed from ascending (oldest first) to descending (most recent baseline first)

## Related

- [[concepts/auto-research-prompt-improver]] — the concept behind this module
- [[entities/engine]] — the parent engine
- [[concepts/tool-enforcement]] — why tool usage requirements are enforced at a higher level
