---
tags: [model, reliability, anomalies]
category: concept
---

# Model Anomalies

The platform continuously monitors LLM analysis output for anomalous behavior, including empty or malformed responses and zero decision generation. Tracking and documenting these patterns helps improve agent robustness, API failover strategies, and prompt engineering.

## Examples and Detection

Anomalies are flagged when model behavior violates expected output invariants. Common patterns include:

- **Empty JSON / Malformed Output**: The model returns unparseable JSON or empty objects `{}` when structured data is required.
  - *Example*: MiniMax 01 model returning empty JSON arrays for Market Feeling analysis.
  - *Detection*: Schema validation failure at the handler level (e.g., Pydantic validation errors).
- **Zero Decision Generation**: The model consistently produces zero trading decisions on high-volatility days where action is statistically expected, indicating over-alignment or prompt misalignment.
  - *Example*: Gemini-3.1-flash-lite returning zero trades during major macro shifts.
  - *Detection*: Post-analysis audit flagged when `len(decisions) == 0` for 3+ consecutive high-volatility days.

## Standard Operating Procedure (SOP)

When an anomaly is flagged, follow these resolution steps:

1. **Check Provider Status**: Verify if the LLM provider is experiencing an outage, high latency, or degraded service on their status page.
2. **Verify Context Window & Input**: Ensure the context payload (newsletters, market data) has not exceeded the model's actual maximum token limit or been truncated unexpectedly.
3. **Analyze Prompt Misalignment**: Check if recent prompt changes or auto-research ratchet updates caused the model to become overly conservative or confused.
4. **Failover**: If the issue is provider-side or persistent, manually switch the affected agent to a secondary provider (e.g., failover from Gemini to Claude) in the configuration.
5. **Document**: Record the anomaly, date, model version, and resolution in the incident log.

## Related

- [[concepts/reasoning]]
- [[entities/pipeline]]
