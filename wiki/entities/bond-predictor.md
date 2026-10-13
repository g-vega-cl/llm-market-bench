---
tags: [entity, bond, predictor, tlt, daily-predictions]
category: entity
---

# Bond Predictor

`apps/engine/tasks/bond_predictor.py` produces daily directional predictions for
Treasury bonds (default ticker `TLT`). It runs a reasoning-model tool loop to
reason over bond context, then performs a structured extraction into a
`BondPredictionOutput` schema and persists the result to the `daily_predictions`
table.

## Reasoning Model Path

`predict_bond_with_reasoning_model` supports two providers:

- **openai** — uses `get_openai_client()`
- **deepseek** — uses `get_deepseek_client()`

The tool loop (`openai.run_tool_loop` / `deepseek.run_tool_loop`) is invoked with
the **raw** underlying client, unwrapped via `getattr(client, "client", client)`.
The instructor-wrapped client exposes the raw SDK client on its `.client`
attribute; passing the wrapper directly to the tool loop is incorrect, so the
raw client is extracted first.

After the tool loop completes, the same client is reused for the final
structured extraction (`instructor_client = client or ...`), falling back to a
freshly constructed client only if none was created.

### Structured Extraction Options

- **deepseek** — `extra_body={"thinking": {"type": "enabled"}}`
- **openai** — `reasoning_effort="none"`

The OpenAI structured extraction uses `reasoning_effort="none"` because the
reasoning models reject the request with a 400 error when a non-`none` effort is
supplied alongside the instructor structured-output call.

## Persistence

`run_daily_bond_prediction` writes each model's prediction to the
`daily_predictions` table using an **upsert** keyed on
`on_conflict="target_date,ticker,model_name"`. This makes re-runs idempotent —
re-predicting the same ticker/model/date overwrites the prior row instead of
creating duplicates.

The payload includes both `prediction_date` and `target_date` (both set to the
current day), satisfying the `prediction_date` NOT NULL constraint on the table.

## Related

- [[entities/daily-bond-trading]]
- [[concepts/daily-tlt-live-trading]]
- [[entities/daily-market-predictor]]
- [[entities/database]]
