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
- **Smooth Benchmark Switching**: The comparison chart avoids flash/remount when switching benchmarks by using `placeholderData: keepPreviousData` (keeps old data visible during the fetch) and omitting `key={selectedBenchmark}` (lets D3 re-draw in-place). A 350ms `easeQuadInOut` fade-in transition is applied to all chart paths on each redraw, giving a polished animated handoff.
- **Thinking Process Expansion**: Every trade or position row expands to reveal the underlying AI reasoning, providing full transparency.

## Related

- [[entities/web-app]]
- [[concepts/execution]]
