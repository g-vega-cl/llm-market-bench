---
tags: [autoresearch, prompt-improvement, meta-prompt, confidence, magnitude]
category: concept
---

# Auto-Research Prompt Improver

The daily autoresearch loop (`apps/engine/tasks/daily_autoresearch.py`) evaluates live trading performance and mutates the trading prompt. The meta-prompt (`generate_new_daily_prompt`) instructs the researcher on which dimensions to optimize.

## Accuracy Block Weights

The meta-prompt describes the composite accuracy block, including conviction points and magnitude calibration. Magnitude calibration is weighted at 10% of the accuracy block and measures how accurately `expected_return_pct` captures realized price movement.

## Zero Prescriptive Confidence Heuristics (Principle 8)

The meta-prompt no longer prescribes confidence ranges or magnitude targets. Removed guidance included:

- "When pre-market signals converge cleanly, express higher conviction (65%-80%)..."
- "When signals conflict or tape is flat, assign 50%-55% to hold safely."
- "When high-impact catalysts or strong trend conditions align, be more confident and aggressive in expected_return_pct magnitude..."
- "On rangebound, ambiguous, or high-VIX days, keep expected_return_pct conservative..."

The researcher now receives only the objective metric definitions and must discover confidence/magnitude rules empirically. This upholds Principle 8 (zero prescriptive confidence heuristics) and prevents the meta-prompt from hardcoding heuristics that the ratchet should learn.

## Related

- [[concepts/magnitude-calibration]] — magnitude scoring
- [[concepts/conviction-points]] — conviction scoring
- [[entities/autoresearch]] — autoresearch engine
- [[concepts/auto-research-prompt-improver]] — this page
