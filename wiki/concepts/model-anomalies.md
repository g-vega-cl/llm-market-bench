---
tags: [model, reliability, anomalies]
category: concept
---

# Model Anomalies

The platform continuously monitors LLM analysis output for an anomalous behavior including empty or malformed responses, zero decision generation. When agents return empty JSON responses (as seen with MiniMax market feeling analysis) or produce zero trading decisions (as observed with Gemini-3.1-flash-lite), these are flagged for investigation. Such anomalies can indicate model-specific issues, prompt misalignment, capacity limits, or API reliability problems. Tracking and documenting these patterns helps improve agent robustness and prompt engineering.

## Related

- [[concepts/reasoning]]
- [[entities/pipeline]]
- [[entities/pipeline]]
