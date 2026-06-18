---
tags: [market-feeling, sentiment, analysis, newsletters, barometer, prediction-markets, price-swings]
category: concept
---

# Market Feeling Analysis

The **Market Feeling Analysis** module generates the "How I'm feeling and why" sentiment analysis for the Today page and Home page. It runs multiple times daily during US market hours and once on the weekend to summarize overall market sentiment.

## Architecture & Data Ingest

The module gathers data from the trading session and calls the MiniMax LLM to generate structured sentiment JSON:

1. **Trades Executed**: Combined log of executed trades (buys/sells) and total capital traded.
2. **Rejected Attempts**: Log of rejected trade orders (e.g. margin/hallucination rejections) indicating agent conviction.
3. **Lessons Learned**: Historical `LESSON_LEARNED` memories from recent post-mortems.
4. **Market Events**: High-importance macro indicators and promoted consensus memories.
5. **Decisions & Reasoning**: Real-time reasoning logs and confidence ratings from the parallel analysis runs.

### Grounded Context Fields

To prevent the LLM from overreacting solely to the actions of other LLMs, the analysis is grounded in external realities:

- **Financial Newsletters** (`newsletter_snapshots`): Formatted metadata (sender, subject) and clean text snippets of all newsletters ingested during the session.
- **S&P 500 Market Health Barometer** (`market_barometer_history`): Broader market multiples (Trailing P/E, Forward P/E, P/B, P/S) and corporate earnings surprise beat rates.
- **Prediction Markets** (`prediction_market_snapshots`): Active, high-volume sentiment odds from Polymarket and Kalshi.
- **Ticker Price Swings** (`price_history`): Dynamically computed return percentages (price swings) for all tickers proposed or traded during the session.

## Running Modes

- **Weekday Mode** (`weekend_mode = False`): Analyzes the current day's trades, events, and price action to generate active market sentiment.
- **Weekend Mode** (`weekend_mode = True`): Gathers the past week's trading logs, newsletters, and price action to generate a weekend recap sentiment summary. No new trades are calculated in this mode.

## Database Storage

The output is stored in the `market_feeling` table (retained for 30 days):
- `sentiment_label` (e.g. Cautiously Optimistic, Risk-Off)
- `sentiment_emoji` (e.g. 📈, 🛡️)
- `confidence_score` (0-100 scale)
- `why_explanation` (2-3 sentence overview)
- `market_direction` (BULLISH, BEARISH, NEUTRAL)
- `primary_concern` / `secondary_concern`

## Related

- [[entities/pipeline]]
- [[entities/database]]
- [[concepts/fundamental-analysis]]
- [[concepts/ingestion]]
