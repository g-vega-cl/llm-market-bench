---
tags: [web, portfolios, ui, comparison, chart]
category: entity
---

# Portfolio Comparison Selector

A React component in `apps/web/src/features/portfolios/components/PortfolioComparisonSelector.tsx` that lets users choose which agents (portfolios) appear in the [[entities/web-app]] performance comparison chart. It enforces a hard cap of **5 simultaneously compared portfolios** and pairs with `PortfolioComparisonChart` to drive the rendered series.

## Purpose

The comparison chart can receive data for many portfolios, but rendering all of them makes the chart unreadable. The selector provides an explicit, user-controlled subset: by default the top 5 portfolios (those with performance data, falling back to the first 5) are shown, and the user can remove or add agents up to the limit.

## Behavior

- **Default selection** — the first `maxSelected` (default 5) portfolios that have performance data are selected on mount; if none have data, the first 5 overall are used.
- **Chips** — each selected portfolio renders as a chip showing its color swatch and formatted owner name (`ownerId` with hyphens replaced by spaces). Each chip has a remove button (`aria-label="Remove <owner> from comparison"`).
- **Add dropdown** — a `<select>` (`aria-label="Add agent to comparison"`) lists unselected portfolios. It is disabled once the selection reaches `maxSelected`, and its placeholder reads `+ Add Agent...` or `+ Add Agent (Max N)` when full.
- **Counter badge** — shows `selected / maxSelected` (e.g. `3 / 5`), switching to a warning color scheme at the limit.
- **Empty state** — when zero portfolios are selected, an italic hint prompts the user to choose up to `maxSelected` agents.
- **Reset** — when the current selection differs from the default top-5, a `Reset to Top 5` button restores the default selection.

## Integration with the Chart

`PortfolioComparisonChart` owns the selection state and passes it down:

- `selectedPortfolioIds` state is initialized from the default top-5 and pruned when portfolios disappear from the incoming data.
- `handleAddPortfolio` refuses additions beyond `maxSelected`; `handleRemovePortfolio` allows dropping below the cap (including to zero).
- Only `activeData` (the selected subset) is rendered as lines, legend entries, and tooltip values. Portfolio colors are assigned per selected portfolio so they stay stable across add/remove.
- When no portfolios are selected, the chart renders a centered message: *"No agents selected. Select up to 5 agents above to compare."*
- The crosshair tooltip is trimmed to the currently selected portfolios, and the chart's date range falls back to the benchmark's range when nothing is selected.

## Related

- [[entities/web-app]]
- [[entities/design-system]]
- [[concepts/zero-frontend-compute]]
