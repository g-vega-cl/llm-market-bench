---
tags: [web, ui, portfolios]
category: source
---

# Source: Portfolios UI & Logic

Synthesized from `raw/docs/web/portfolios-ui.md`.

## Takeaways

- **Active vs Retired Classification**: Portfolios are classified based on the current `models.json` configuration. Retired portfolios are preserved for auditability but visually de-emphasized.
- **D3 Performance Charts**: Uses D3 for highly-customizable, dependency-light equity curves with inline data displays for better mobile usability.
- **Benchmark Normalization**: Allows direct comparison with major indices by normalizing both the portfolio and the benchmark to 0% at the start of the window.
- **Smooth Client-side Benchmark & Timeframe Switching**: The comparison chart avoids flash/remount when switching benchmarks or timeframes. All 4 benchmarks and full portfolios history are loaded in a single initial query on page mount. Slicing dates and re-normalizing performance to 0% is done dynamically on the client in a `useMemo` block, enabling 0ms instantaneous switches with zero visual flash, layout shift, or network fetches.
- **Thinking Process Expansion**: Every trade or position row expands to reveal the underlying AI reasoning, providing full transparency.

## Related

- [[entities/web-app]]
- [[concepts/execution]]
