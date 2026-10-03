---
tags: [experiment, fine-tuning, qwen, market-predictor, training]
category: entity
---

# Qwen Training Workbench

A standalone workbench at `experiments/qwen-training/` for fine-tuning **Qwen 3.8 27B** with Unsloth 4-bit QLoRA on historical SPY intraday outcomes. It is completely decoupled from `apps/engine` and the production pipelines — it reads from Supabase but never writes to production tables or participates in the live trading loop.

The goal is a locally-runnable model that predicts whether SPY closes UP or DOWN versus the 9:30 AM ET open, trained on the same morning-context inputs the production [[entities/daily-market-predictor]] consumes.

## Directory Layout

text
experiments/qwen-training/
├── data/
│   ├── train.jsonl             # 79 training sessions (Apr 2026 -> Sep 2026, 40 UP / 39 DOWN)
│   └── val.jsonl               # 20 validation sessions (Sep 2026 -> Oct 2026 out-of-sample forward test)
├── export_dataset.py           # Standalone dataset extractor targeting true market closes
├── test_export.py              # Hermetic unit tests verifying extraction and formatting
├── notebook.ipynb              # Google Colab Pro notebook with continuous Google Drive checkpointing
├── Modelfile                   # Ollama configuration for local inference
├── test_inference.py           # Test runner verifying predictions against Ollama
└── requirements.txt            # Isolated environment dependencies


## Dataset Extraction

`export_dataset.py` pulls evaluated rows from the Supabase `daily_predictions` table (`status = 'evaluated'`), deduplicates by `target_date`, and pairs each session's pre-market context with the realized close outcome.

- **Context source**: the row's `market_context` if present, otherwise a fallback to `generated_newsletters` (preferring the `open` session) and finally `newsletter_snapshots`.
- **Target**: `actual_direction` plus `expected_return_pct` computed as `(close - open) / open * 100`, rounded to two decimals.
- **Split**: chronological — the most recent `val_ratio` (default 20%) of sessions become the out-of-sample validation set, so validation is a true forward test.

Each record is emitted in ChatML message format (`system` / `user` / `assistant`) with a `metadata` block carrying `target_date`, `ticker`, `actual_direction`, `open_price`, `close_price`, and `actual_return_pct`. The system prompt enforces a strict JSON output contract (`predicted_direction`, `expected_return_pct`) with no Markdown.

## Training

`notebook.ipynb` runs on a Google Colab Pro A100 (High-RAM) runtime:

- Loads `Qwen/Qwen3.8-27B` in 4-bit via `FastLanguageModel` with `max_seq_length = 16384` and bfloat16.
- Applies LoRA adapters (`r=16`, `lora_alpha=32`, all attention and MLP projections, Unsloth gradient checkpointing).
- Trains with `SFTTrainer` (3 epochs, `adamw_8bit`, cosine schedule, effective batch size 8 via gradient accumulation).
- `assistant_only_loss=False` because the Qwen 3.8 architecture is classified as a VLM.

### Drive Checkpointing

To survive Colab disconnects, the notebook mounts Google Drive and persists to `/content/drive/MyDrive/qwen3.8-predictor-checkpoints`:

- Checkpoints save every 10 steps, keeping the latest 3.
- A `GoogleDriveAdapterSyncCallback` writes the LoRA adapter and tokenizer on every checkpoint.
- The training cell auto-detects existing `checkpoint-*` directories and resumes from the latest one.
- Final LoRA weights and the `q4_k_m` GGUF export are written directly into the Drive folder.

## Local Inference

After exporting the GGUF, the model is registered with Ollama via the bundled `Modelfile` (temperature 0.1, top_p 0.9, `num_ctx` 16384):

bash
cd experiments/qwen-training
ollama create qwen3.8-predictor -f Modelfile
python test_inference.py --endpoint http://localhost:11434/v1 --model qwen3.8-predictor


On a 12 GB VRAM GPU with 48 GB DDR5 system RAM, Ollama offloads roughly 18–20 transformer layers to the GPU and the remainder to system RAM.

## Evaluation

`test_inference.py` benchmarks against the OpenAI-compatible endpoint (Ollama or vLLM) and reports:

- **JSON format compliance** — share of responses that parse as valid JSON.
- **Directional accuracy** — hit rate against `actual_direction`.
- **Average Brier score** — derived from token logprobs. `extract_confidence_from_logprobs` normalizes the probability of the predicted direction token against the opposite direction token, falling back to an uninformative 50% prior when logprobs are unavailable.
- **Mean absolute return error** — average deviation of `expected_return_pct` from the realized return.

Run `--all` for the full 20-session forward benchmark, or `--sample-index` for a single session. The notebook's final cell performs the same benchmark directly on the A100.

## Related

- [[entities/daily-market-predictor]] — the production predictor this experiment mirrors
- [[entities/daily-predictor-backtest-arena]] — backtesting harness for the production predictor
- [[concepts/brier-score]] — the calibration metric used in evaluation
- [[entities/database]] — source of `daily_predictions`, `generated_newsletters`, and `newsletter_snapshots`
