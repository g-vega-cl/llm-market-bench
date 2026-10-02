---
tags: [entity, laya, training, fine-tuning, experiments, calibration]
category: entity
---

# Laya Training Workbench

A standalone workbench at `experiments/laya-training/` for fine-tuning **Laya** (`convaiinnovations/laya-typed-decisions`) — a non-autoregressive System 1 decision engine built on `ModernBERT-large` — to predict intraday SPY direction (`UP`/`DOWN`) from full pre-market macro contexts (~5,000 tokens).

The workspace is completely decoupled from `apps/engine` and production workflows. It reads evaluated market sessions from Supabase (read-only) and produces LoRA adapters plus a calibration config, but nothing in the production pipeline depends on it.

## Directory Layout

```text
experiments/laya-training/
├── data/
│   ├── train.jsonl             # 78 training records (Apr 2026 → Sep 2026, 50/50 balance)
│   └── val.jsonl               # 20 validation records (Sep 2026 out-of-sample forward test)
├── output/                     # LoRA adapters and calibration config
├── export_dataset.py           # Supabase data extractor (read-only)
├── train.py                    # PyTorch + LoRA trainer with Platt scaling and temperature calibration
├── evaluate.py                 # Out-of-sample evaluator with Jev benchmark comparison
├── test_pipeline.py            # Unit tests for schema validation, leakage prevention, and calibration math
├── notebook.ipynb              # Self-contained Jupyter notebook for Google Colab / Kaggle
└── requirements.txt            # Isolated Python dependencies
```

## Pipeline

1. **Export** (`export_dataset.py`) — pulls `evaluated` rows from the `daily_predictions` table, deduplicates by `target_date`, and reconstructs context from `market_context` or falls back to `generated_newsletters` / `newsletter_snapshots`. Emits Laya's typed-decisions JSONL schema (`state`, `questions`, `gold`, `metadata`). Splits chronologically (no lookahead leakage) into `train.jsonl` / `val.jsonl`.
2. **Train** (`train.py`) — attaches LoRA adapters (`r=16`, `alpha=16`) to ModernBERT's attention and MLP projections (`Wqkv`, `Wo`, `Wi`), minimizes cross-entropy with `label_smoothing=0.05`, then fits post-hoc temperature and Platt scaling on the validation logits.
3. **Evaluate** (`evaluate.py`) — runs inference on `val.jsonl`, applies the saved calibration config, and prints a side-by-side table against historical arena models pulled from the same validation dates.
4. **Test** (`test_pipeline.py`) — verifies schema compliance, chronological-split leakage prevention, context reconstruction fallbacks, and calibration math.

## Calibration

The workbench supports two post-hoc calibration methods, both stored in `output/laya_calibration_config.json`:

- **Scalar temperature scaling** (`z / T`) — shrinks logit magnitude under an assumed 50/50 prior.
- **Platt scaling** (`P = σ(w · Δz + b)`) — fits an intercept `b` that captures market regime asymmetry, improving both calibration and accuracy. This is the default method.

See [[concepts/laya-decisions-model]] for the full benchmark table and technical findings (bfloat16 requirement, gradient checkpointing, overfitting dynamics, and the 7B–8B sequence-classifier scaling roadmap).

## Related

- [[concepts/laya-decisions-model]] — the Laya decision engine and its empirical fine-tuning results
- [[entities/daily-market-predictor]] — the production daily predictor whose evaluated sessions seed the training data
- [[entities/database]] — Supabase tables (`daily_predictions`, `generated_newsletters`, `newsletter_snapshots`) read by the exporter
