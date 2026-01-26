# Trend & Concept Momentum Analysis Walkthrough

The **Trend & Concept Momentum Analysis** is the 9th step in the AI Wall Street pipeline. It tracks the frequency and velocity of market "concepts" (e.g., "NVIDIA Blackwell Delay", "Fed Pivot", "AI Infrastructure Surge") to identify emerging trends that are gaining traction across news sources.

## How It Works

This stage analyzes every synthesized event promoted to the global timeline during the [Consensus Phase](./event-consensus-walkthrough.md):

### 1. Vectorized Frequency Tracking
Instead of simple keyword matching, the engine uses **Gemini Embeddings (`text-embedding-004`)** to perform a semantic similarity search against the `memories` table. This allows it to count mentions of a concept even if they are worded differently across different days or newsletters.

### 2. Momentum Scoring (Velocity)
The engine calculates a **Velocity Score** for each concept using the following formula:

$$Velocity = \frac{Recent Mentions (Last 7 Days)}{Average Daily Mentions (Previous 30 Days)}$$

- **High Velocity (> 2.0):** Indicates an "Emerging Trend" that is being mentioned significantly more in the last 7 days than its 30-day average.
- **Low Velocity (< 1.0):** Indicates a fading or stable concept.
- **Emerging Trends:** Concepts with no prior history receive a high initial score to flag them for immediate attention.

### 3. Semantic Concept Merging
To prevent data fragmentation (e.g., tracking "Fed Rate Hike" and "Interest Rate Increase" as two different trends), the engine performs a semantic search on the `concept_metrics` table before updating.
- If an existing concept has **> 90% semantic similarity**, the new mention is merged into the existing entry.
- This ensures a clean, consolidated "Global Timeline" where related news clusters under a single master concept.

### 4. Trend Archeology & 90-Day History
The engine tracks concepts over a rolling **90-day window**:
- `first_mention_at`: Discovery timestamp of the absolute first occurrence of the concept cluster.
- `last_mention_at`: Timestamp of the most recent occurrence.
- `mention_count`: Total cumulative count of semantic appearances across all tracked newsletters.
- **Extended Context**: Future RAG queries leverage this history to understand the longevity and evolution of a market theme.

## Configuration & Tuning

Key thresholds and lookback windows can be tuned in `apps/engine/core/config.py`:
- `MOMENTUM_SIMILARITY_THRESHOLD`: Sensitivity for counting mentions (default 0.85).
- `MOMENTUM_CONCEPT_MERGE_THRESHOLD`: Sensitivity for merging two concept names (default 0.90).
- `MOMENTUM_BASELINE_DAYS`: The historical window size for velocity calculation (default 30 days).

## Data Schema & Storage

Metrics are stored in the `concept_metrics` table:

| Field | Description |
| --- | --- |
| `concept_name` | The synthesized name of the trend |
| `concept_vector` | 768-dimensional embedding for semantic matching |
| `mention_count` | Total cumulative appearances |
| `velocity_score` | The current 24h/7d acceleration score |
| `first_mention_at` | Discovery timestamp |
| `pca_x` | 2D coordinate (Principal Component 1) for visualization |
| `pca_y` | 2D coordinate (Principal Component 2) for visualization |

## Verification

### Logs
You can monitor trend updates in the engine logs:
```text
INFO: Analyzing momentum for 3 concepts...
INFO: Updated concept metrics for 'AI Infrastructure Surge' (Velocity: 4.50)
INFO: Updated concept metrics for 'Rate Cut Expectations' (Velocity: 0.85)
```

### Tests
Unit tests for the momentum logic are located at `apps/engine/tests/test_momentum.py`.
