# Qwen 3.8 27B Market Predictor Workbench

Standalone workbench for fine-tuning **Qwen 3.8 27B** with Unsloth 4-bit QLoRA on historical market data.

This workspace is completely decoupled from `apps/engine` and production pipelines.

---

## Directory layout

```text
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
```

---

## Google Colab Pro setup & Drive checkpointing

To prevent progress loss from unexpected Colab disconnects, the notebook is configured with continuous checkpoint persistence to Google Drive:

1. Open `experiments/qwen-training/notebook.ipynb` in Google Colab.
2. Select runtime: **Runtime -> Change runtime type -> A100 GPU (High-RAM)**.
3. Upload `experiments/qwen-training/data/train.jsonl` and `val.jsonl` into the Colab file browser, or copy them into your Google Drive.
4. Run all cells:
   - Cell 1 mounts Google Drive and establishes `/content/drive/MyDrive/qwen3.8-predictor-checkpoints`.
   - Cell 5 configures checkpoints to save every 10 steps, keeping the latest 3 checkpoints.
   - An adapter sync callback saves the LoRA adapter to Google Drive on every checkpoint.
   - If Colab drops connection or restarts, re-executing Cell 6 automatically detects existing checkpoints in your Drive and resumes training seamlessly.
   - Cell 9 exports the model to `q4_k_m` GGUF directly inside your Google Drive.

---

## Local inference on 12GB VRAM + 48GB DDR5 RAM

Once training completes and GGUF weights are generated:

1. Download the exported `qwen3.8-27b-predictor-q4_k_m.gguf` from your Google Drive into `experiments/qwen-training/`.
2. Register the model with Ollama:
   ```bash
   cd experiments/qwen-training
   ollama create qwen3.8-predictor -f Modelfile
   ```
3. Run test predictions against the local model:
   ```bash
   python test_inference.py --endpoint http://localhost:11434/v1 --model qwen3.8-predictor
   ```
Ollama will allocate approximately 18 to 20 transformer layers into your 12 GB VRAM GPU and offload the remaining layers into your 48 GB DDR5 system RAM, achieving fast local inference.
