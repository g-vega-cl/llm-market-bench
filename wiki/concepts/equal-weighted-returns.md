---
tags: [metrics, auto-research, scoring]
category: concept
---

# Equal-Weighted Percentage Returns

A scoring methodology for the auto-research system where each agent's daily percentage return is computed independently from its own equity curve, then averaged across agents per day. This ensures that a $10K portfolio and a $5K portfolio have equal influence on the combined score — only percentage changes matter.

## Motivation

Previously, `_daily_returns()` summed total equity across all agents per day before computing returns, which gave larger portfolios disproportionate influence. Equal-weighted percentage returns correct this by treating each agent's performance as equally important regardless of portfolio size.

## Implementation

The change was isolated to the `_daily_returns()` function in `autoresearch/metrics.py`:

1. Group equity by `(owner_id, date)` using a `defaultdict(dict)`
2. Collect all unique dates across all agents
3. For each day gap, compute each agent's percentage return independently
4. Average the per-agent returns for that day gap

## Edge Cases

- **Missing data**: If an agent has no equity record for a given date, it is excluded from that day's average. The remaining agents' returns are averaged normally.
- **Single agent**: Degrades to standard percentage return calculation (no averaging distortion).

## Related

- [[entities/autoresearch]]
- [[concepts/auto-research-prompt-improver]]
- [[concepts/memory-feedback]]
