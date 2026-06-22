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
- **Smooth Client-side Benchmark & Timeframe Switching**: The comparison chart avoids flash/remount when switching benchmarks or timeframes. All available benchmarks (defined dynamically by `BENCHMARK_OPTIONS` on the frontend, including S&P 500, Nasdaq 100, Gold, Bitcoin, etc.) and the full portfolios history are preloaded in the route loader. Slicing dates and re-normalizing performance to 0% is done dynamically on the client in a `useMemo` block, enabling 0ms instantaneous switches with zero visual flash, layout shift, or network fetches.
- **Paginated Database Fetching**: Since the total price history records for all benchmarks over the portfolios' entire lifecycle exceeds the default 1,000-row limit in the Supabase API (Postgrest), `fetchBenchmarkHistory` uses sequential `.range()` pagination in a loop. This bypasses the result-capping limit, ensuring recent price data (e.g. for 7d and 30d timeframes) is fully loaded without truncation.
- **Infinite Caching for Historical Data**: To minimize database overhead, both the comparison and benchmark history queries configure `staleTime: Number.POSITIVE_INFINITY`. Because historical stock prices and closed daily performance never change retroactively, this caches the data globally for the session, preventing redundant API calls.
- **Thinking Process Expansion**: Every trade or position row expands to reveal the underlying AI reasoning, providing full transparency.

## Related

- [[entities/web-app]]
- [[concepts/execution]]
