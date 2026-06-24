---
tags: [ui, dashboard, sentiment, today-page]
category: entity
---

# AI Feeling Card

The `AIFeelingCard` component renders the "How is the AI Feeling?" section on the Today dashboard. It displays the latest market sentiment analysis from the `market_feelings` table — sentiment label, emoji, direction badge, confidence bar, why-explanation, primary concern, buy/sell trade split, last-analyzed timestamp, and model name — all in a single card with a subtle gradient background accent.

## Data Sources

The component consumes data already present on the `TodayData` type:
- `marketFeeling` — the latest `MarketFeeling` row (with optional `formattedTime`)
- `trades` — today's trades with `portfolios.owner_id` for owner attribution
- `isSentimentStale` — boolean flag indicating data is older than 4 hours

No additional fetching is required; the data is passed from the parent `TodayPage`.

## Sub-Components

To keep cognitive complexity ≤ 15 (Biome rule), the card is split into three internal sub-components:

- **`SentimentHeader`** — Renders the emoji (with `animate-float`), sentiment label with direction-based color (`text-neon-green-500` for BULLISH, `text-alert-red-500` for BEARISH), direction `Badge`, and optional STALE warning pill.
- **`TradeSplit`** — A 2-column grid showing buy/sell counts with neon-green and alert-red themed boxes. Only renders when `totalTrades > 0`.
- **`CardFooter`** — Renders the last-analyzed timestamp (or "Waiting for analysis..." fallback), model name, and a link to the full `/market-overview` page.

## Color Scheme Helpers

Three utility functions map data to design-system color schemes:
- `getDirectionColor(direction)` — returns Tailwind text color class
- `getDirectionColorScheme(direction)` — returns `ColorScheme` for `Badge` component
- `getConfidenceColorScheme(score)` — returns `ColorScheme` for `ConfidenceBar` (≥70 success, ≥40 warning, <40 danger)

## Empty State

When `marketFeeling` is `null`, the card renders:
- Sentiment label: "Analyzing..."
- Emoji: "🤔"
- Timestamp: "Waiting for analysis..."
- No STALE warning (even if `isSentimentStale` is `true`)
- No trade split, no confidence bar, no why-explanation, no primary concern

## Related

- [[entities/web-app]] — Today page layout and key pages
- [[concepts/market-feeling]] — Market sentiment analysis concept
- [[entities/design-system]] — Shared UI components (Card, Badge, ConfidenceBar, SectionHeading)
