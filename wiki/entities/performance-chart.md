---
tags: [web, portfolios, ui, chart, d3]
category: entity
---

# Performance Chart

A D3-based line/area chart in `apps/web/src/features/portfolios/components/PerformanceChart.tsx` that renders a single portfolio's performance series alongside an optional benchmark (e.g. SPY). It is the single-portfolio counterpart to the multi-agent [[entities/portfolio-comparison-selector]] chart.

## Rendering

- Draws the portfolio series as a monotone-X line (`#0ea5e9`) plus a gradient-filled area beneath it.
- When a `selectedBenchmark` is supplied and `benchmarkData[selectedBenchmark]` exists, an amber (`#f59e0b`) benchmark line is overlaid.
- All paths are clipped to the plot area via a `<clipPath id="performance-chart-clip">` rect sized to the SVG `width`/`height`, so lines never bleed past the chart bounds.

## Benchmark bounding

The benchmark series is strictly filtered to the active portfolio date range before rendering:

- The min/max dates are computed from the portfolio's parsed data (`d3.extent`).
- Benchmark points outside `[minTime, maxTime]` are dropped, so a benchmark whose raw history predates the portfolio's first data point (common in 90D/All timeframes) does not extend the line beyond the visible window.
- The same `clip-path` is applied to the benchmark path as an additional guard.

## Related

- [[entities/portfolio-comparison-selector]] — multi-agent comparison chart with the same benchmark-bounding pattern
- [[entities/web-app]]
- [[concepts/zero-frontend-compute]]
