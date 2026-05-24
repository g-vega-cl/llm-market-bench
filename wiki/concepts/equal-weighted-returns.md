---
tags: [metrics, auto-research, scoring, alpha]
category: concept
---

# Equal-Weighted Percentage Returns

A scoring methodology for the auto-research system where each agent's daily percentage return is computed independently from its own equity curve, then averaged across agents per day. This ensures that a $10K portfolio and a $5K portfolio have equal influence on the combined score — only percentage changes matter.

---

## Rationale & Mathematical Vulnerability

Under the previous **Equity-Weighted Return** methodology, the auto-research system summed absolute dollar equities across all agents per day before calculating return percentages:

$$\text{Daily Return}_{\text{pooled}} = \frac{\sum_{i} \text{Equity}_{i, t} - \sum_{i} \text{Equity}_{i, t-1}}{\sum_{i} \text{Equity}_{i, t-1}}$$

This created a severe systemic vulnerability:
- **Capital Scale Bias**: A portfolio initialized with higher starting capital (or experiencing high volatility) disproportionately dominated the aggregate score.
- **Noise Sensitivity**: A single lucky breakout or highly leveraged bet in a large portfolio could trigger or block a prompt revert cycle, forcing the meta-researcher's Karpathy Ratchet to operate on idiosyncratic noise rather than generalized prompt signal.

Equal-weighted daily returns correct this by standardizing each portfolio's contribution to exactly $1/N$ on any given day, ensuring only the prompt-driven percentage performance is optimized.

---

## Alternatives Considered

1. **Summing Absolute Dollar Gains**:
   - *Logic*: Maximize total dollar profit.
   - *Flaw*: Extreme scale bias. Completely penalizes safe/conservative strategies and ignores smaller portfolios, promoting reckless leverage on larger portfolios.
2. **Global Pool Time-Weighted Return (TWR)**:
   - *Logic*: Measure aggregate fund performance over time.
   - *Flaw*: Appropriate for single large funds, but obscures individual agent behavior and suffers from complex adjustments when agent capital allocations fluctuate.
3. **Equal-Weighted Daily Percentage Return (Selected)**:
   - *Logic*: Compute per-agent daily returns and average them.
   - *Advantage*: Neutralizes size and volatility outliers. Focuses prompt optimization entirely on generalizable, systemic trading logic that succeeds across all portfolios.

---

## Implementation

The change is isolated to `_daily_returns()` in `apps/engine/autoresearch/metrics.py`:
1. **Grouping**: Groups raw daily equity snapshots by `(owner_id, date)` using a `defaultdict(dict)`.
2. **Timeline Alignment**: Collects the set of all unique dates across all agents to construct a unified chronological timeline.
3. **Independent Computations**: For each date gap, computes each agent's percentage return independently.
4. **Daily Averaging**: Averages these independent percentage returns for each day in the timeline.

---

## Edge Cases & Resiliency

- **Missing Data / Off-cycle Snaps**: If an agent lacks an equity record for a given date, it is gracefully excluded from that day's average computation. The denominator is adjusted to the count of remaining active agents, preventing division-by-zero or default-value skew.
- **Single Agent**: Degrades gracefully to a standard single-portfolio percentage return calculation.

---

## Before/After Impact

- **Before**: Prompt evolution was highly volatile. The meta-researcher frequently ratcheted prompts based on the performance of a single outlier portfolio, leading to over-fitting and decay in other portfolios.
- **After**: The scoring signal is highly stable and smooth. Prompts are only ratified and saved as baselines by the Karpathy Ratchet if they produce consistent, generalized alpha across all portfolios in the experiment group.

---

## Related

- [[entities/autoresearch]] — the implementation module
- [[concepts/auto-research-prompt-improver]] — the evolutionary loop
- [[concepts/memory-feedback]] — post-mortem feedback architecture
