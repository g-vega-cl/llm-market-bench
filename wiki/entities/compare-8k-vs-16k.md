---
tags: [autoresearch, benchmark, strata, reasoning-budget, head-to-head]
category: entity
---

# compare_8k_vs_16k

`apps/engine/local_autoresearch/compare_8k_vs_16k.py` is a head-to-head benchmark that runs the production `DAILY_PREDICTOR_PROMPT` against Strata ORCA at two `max_tokens` settings — 8,192 and 16,384 — over 20 strictly non-continuous, pre-market ground-truth sessions.

## Purpose

It isolates the effect of reasoning-token budget on directional accuracy, latency, and agreement. Both runs use `reasoning_budget_tokens: -1` (unconstrained reasoning) and `temperature: 0.3`. Strata reserves `max_tokens // 4` for the answer, so the effective thinking budgets are roughly 6,144 and 12,288 tokens.

## Session Selection

`select_non_continuous_sessions(db_path='.live_production_sessions.db', count=20)` reads `live_sessions` ordered by `target_date` and picks evenly spaced indices across the dataset. It enforces a gap of at least two indices between selected sessions so no two sessions are adjacent, then clamps the tail to stay in range. This avoids evaluating on a contiguous regime block.

## Streaming Query

`query_strata_stream` posts to the OpenAI-compatible `/chat/completions` endpoint with `stream: true`. It counts `reasoning_content` deltas as thinking chunks, accumulates `content` deltas, and returns `(raw_content, elapsed_sec, thinking_chunks)`. Streaming avoids read timeouts during long reasoning runs; timeouts are 360s for 8k and 550s for 16k.

## Evaluation & Resume

Each run is parsed with `extract_daily_prediction` and scored with `evaluate_prediction_record` from [[concepts/single-prompt-ratchet]], producing direction, confidence, Brier score, and intraday hit flags. Results are written incrementally to `.compare_8k_vs_16k_results.json` with per-session entries and running summaries. On restart, completed `target_date` values are loaded and skipped, so the benchmark resumes where it stopped.

## Output

The results file tracks `summary_8k` and `summary_16k` (win rate, balanced accuracy, MCC, average latency), `agreement_pct`, and per-session `run_8k` / `run_16k` records. The final console report prints both configurations side by side plus directional agreement.

## Related

- [[concepts/single-prompt-ratchet]] — evaluation helpers and prompt under test
- [[entities/local-autoresearch]] — Strata ORCA runtime and reasoning-budget calibration
- [[concepts/sized-trading-pnl]] — downstream quant scoring of prediction records
