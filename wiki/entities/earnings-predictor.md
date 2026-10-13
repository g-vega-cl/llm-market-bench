---
tags: [entity, earnings, predictor, openai]
category: entity
---

# Earnings Predictor

`apps/engine/tasks/earnings_predictor.py` generates directional earnings
predictions for candidate tickers using an OpenAI reasoning model.

## Luna Prediction Path

`predict_with_luna` calls the OpenAI client with
`response_model=EarningsPredictionOutput` for structured output. The call passes
`reasoning_effort="none"` — the reasoning models reject structured-output
requests that specify a non-`none` reasoning effort with a 400 error, so the
effort is disabled for this extraction step.

## Related

- [[entities/earnings-alpha]]
- [[entities/earnings-audit]]
- [[concepts/earnings-prediction-strategies]]
