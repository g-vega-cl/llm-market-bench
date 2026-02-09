# Trend & Concept Momentum Analysis Walkthrough

The **Trend & Concept Momentum Analysis** is the 9th step in the AI Wall Street pipeline. It tracks the frequency and velocity of market "concepts" (e.g., "NVIDIA Blackwell Delay", "Fed Pivot", "AI Infrastructure Surge") to identify emerging trends that are gaining traction across news sources.

## How It Works

This stage analyzes every synthesized event promoted to the global timeline during the [Consensus Phase](./event-consensus-walkthrough.md):

### 1. Vectorized Frequency Tracking
Instead of simple keyword matching, the engine uses **Gemini Embeddings (`gemini-embedding-001`)** to perform a semantic similarity search against the `memories` table. This allows it to count mentions of a concept even if they are worded differently across different days or newsletters.

### 2. Momentum Scoring (Hybrid)
The engine calculates a **Momentum Score** for each concept using a hybrid formula that balances current relevance (volume) with trending growth (acceleration):

$$\text{Momentum} = \text{Intensity} \times \text{Growth}$$

- **Intensity (Volume):** Rewards sheer relevance using a log scale: $\ln(\text{Recent Mentions} + 1) + 1.0$. This ensures that high-volume, established topics (like "Iran Tensions") maintain a high score even if their growth rate is stable.
- **Growth (Acceleration):** Rewards recent "burstiness" by comparing the daily average of the last 7 days against the daily average of the previous 30 days.

#### Scoring Interpretation:
- **High Momentum (> 5.0):** Indicates a "Hot Topic" with either massive volume or extreme acceleration.
- **Stable Momentum (1.0 - 5.0):** Indicates a consistently relevant topic that is neither exploding nor fading.
- **Low Momentum (< 1.0):** Indicates a fading or stale concept.

### 3. Semantic Concept Merging & Prefixing
To ensure high-precision matching, the engine performs two additional steps:
- **Search Prefixing:** Before searching, the concept name is prefixed with `"MARKET EVENT:"` (e.g., `"MARKET EVENT: NVIDIA Blackwell Delay"`). This aligns the search query with the exact content format stored in the `memories` table, drastically improving cosine similarity.
- **Deduplication:** To prevent data fragmentation (e.g., tracking "Fed Rate Hike" and "Interest Rate Increase" separately), the engine merges new mentions into existing concepts if they share **> 75% semantic similarity**.

### 4. Trend Archeology & 90-Day History
The engine tracks concepts over a rolling **90-day window**:
- `first_mention_at`: Discovery timestamp of the absolute first occurrence of the concept cluster.
- `last_mention_at`: Timestamp of the most recent occurrence.
- `mention_count`: Total cumulative count of semantic appearances across all tracked newsletters.
- **Half-Life Decay**: Stale concepts have their Momentum Scores reduced by 50% every 28 days if no new mentions occur, preventing outdated "ghost" trends from clogging the map.

## Configuration & Tuning

Key thresholds and lookback windows can be tuned in `apps/engine/core/config.py`:
- `MOMENTUM_SIMILARITY_THRESHOLD`: Sensitivity for counting mentions (default 0.75).
- `MOMENTUM_CONCEPT_MERGE_THRESHOLD`: Sensitivity for merging two concept names (default 0.75).
- `MOMENTUM_BASELINE_DAYS`: The historical window size (default 30 days).

## Data Schema & Storage

Metrics are stored in the `concept_metrics` table:

| Field | Description |
| --- | --- |
| `concept_name` | The synthesized name of the trend |
| `concept_vector` | 768-dimensional embedding (prefixed with "MARKET EVENT:") |
| `mention_count` | Total cumulative appearances |
| `velocity_score` | Used to store the Hybrid Momentum Score |
| `first_mention_at` | Discovery timestamp |
| `last_mention_at` | Timestamp of most recent occurrence |
| `pca_x`, `pca_y` | 2D coordinates for the Cluster Map (auto-calculated) |

## Visualization: PCA Coordinate Calculation

After momentum analysis completes, the daily pipeline automatically calculates 2D PCA (Principal Component Analysis) coordinates for all concepts. This dimensionality reduction transforms the 768-dimensional embeddings into 2D coordinates (`pca_x`, `pca_y`) that can be visualized on the [Concept Cluster Map](../../apps/web/src/routes/concepts/index.tsx).

**Implementation:** The PCA calculation is handled by `apps/engine/analysis/pca_utils.py` and is automatically invoked at the end of the `run_ingest` pipeline in `main.py`.

**Manual Trigger:** If you need to recalculate coordinates outside the daily pipeline (e.g., after a database migration), you can run:
```bash
cd apps/engine
python update_concepts.py
```

## Verification

### Logs
You can monitor trend updates in the engine logs:
```text
INFO: Analyzing momentum for 3 concepts...
INFO: Updated concept metrics for 'AI Infrastructure Surge' (Momentum: 18.42)
INFO: Updated concept metrics for 'Rate Cut Expectations' (Momentum: 2.15)
```

### Tests
Unit tests for the momentum logic are located at `apps/engine/tests/test_momentum.py`.
