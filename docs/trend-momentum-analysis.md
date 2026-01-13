# Trend & Concept Momentum Analysis Walkthrough

The **Trend & Concept Momentum Analysis** is the 9th step in the AI Wall Street pipeline. It tracks the frequency and velocity of market "concepts" (e.g., "NVIDIA Blackwell Delay", "Fed Pivot", "AI Infrastructure Surge") to identify emerging trends that are gaining traction across news sources.

## How It Works

This stage analyzes every synthesized event promoted to the global timeline during the [Consensus Phase](./event-consensus-walkthrough.md):

### 1. Vectorized Frequency Tracking
Instead of simple keyword matching, the engine uses **Gemini Embeddings (`text-embedding-004`)** to perform a semantic similarity search against the `memories` table. This allows it to count mentions of a concept even if they are worded differently across different days or newsletters.

### 2. Momentum Scoring (Velocity)
The engine calculates a **Velocity Score** for each concept using the following formula:

$$Velocity = \frac{Recent Mentions (Last 24h)}{Average Daily Mentions (Previous 7 Days)}$$

- **High Velocity (> 2.0):** Indicates an "Emerging Trend" that is being mentioned significantly more today than its recent average.
- **Low Velocity (< 1.0):** Indicates a fading or stable concept.
- **Emerging Trends:** Concepts with no prior history receive a high initial score to flag them for immediate attention.

### 3. Trend Archeology
Each concept is tracked with:
- `first_mention_at`: The timestamp when the concept was first identified by any model.
- `last_mention_at`: The most recent appearance.
- `mention_count`: Cumulative number of times this specific semantic cluster has appeared.

## Data Schema & Storage

Metrics are stored in the `concept_metrics` table:

| Field | Description |
| --- | --- |
| `concept_name` | The synthesized name of the trend |
| `concept_vector` | 768-dimensional embedding for semantic matching |
| `mention_count` | Total cumulative appearances |
| `velocity_score` | The current 24h/7d acceleration score |
| `first_mention_at` | Discovery timestamp |

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
