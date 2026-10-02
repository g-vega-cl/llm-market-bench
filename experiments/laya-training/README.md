# Laya Training Workbench

Standalone workbench for fine-tuning **Laya** (`convaiinnovations/laya-typed-decisions`), a non-autoregressive System 1 decision engine based on `ModernBERT-large`, on pre-market macro context data.

This workspace is completely decoupled from `apps/engine` and production workflows.

---

## Directory layout

```text
experiments/laya-training/
├── data/
│   ├── train.jsonl             # 78 training records (Apr 2026 -> Sep 2026, 50/50 balance)
│   └── val.jsonl               # 20 validation records (Sep 2026 out-of-sample forward test)
├── output/                     # LoRA adapters and calibration config
├── export_dataset.py           # Supabase data extractor (read-only)
├── train.py                    # PyTorch + LoRA trainer with Platt scaling and temperature calibration
├── evaluate.py                 # Out-of-sample evaluator with Jev benchmark comparison
├── test_pipeline.py            # Unit tests for schema validation, leakage prevention, and calibration math
├── notebook.ipynb              # Self-contained Jupyter notebook for Google Colab / Kaggle
└── requirements.txt            # Isolated Python dependencies
```

---

## Empirical findings & benchmark results

The fine-tuning experiments conducted on an 80 GB A100 GPU over full pre-market contexts (~5,000 tokens) yielded the following out-of-sample results on the 20-session forward test (September 2026):

| Model / Calibration Stage | Accuracy | Brier Score | Notes |
|---|---|---|---|
| Random Guess Baseline | 50.0% | 0.2500 | Theoretical uninformative baseline |
| Zero-shot / Under-trained (10 epochs, lr=3e-5) | 45.0% | 0.2844 | Stalled at loss ~0.695 due to learning rate floor |
| Overfit Checkpoint (25 epochs, no label smoothing) | 55.0% | 0.3559 | Train loss collapsed to 0.048; logit explosion blew up Brier |
| **Best LoRA Checkpoint (Epoch 17 + Label Smoothing)** | **60.0%** | **0.3100** | Stable training loss ~0.117; zero memorization explosion |
| Temperature Scaled ($T=2.096$) | 60.0% | 0.2654 | Deflated overconfident logits toward 50/50 |
| **Platt Calibrated ($w=0.485, b=-0.182$)** | **65.0%** | **0.2250** | **Learned 60/40 directional regime; flipped borderline error** |

### Key technical takeaways

1. **Hardware precision:** On Ampere/Hopper architectures (A100, H100), `torch.bfloat16` is mandatory. Standard `float16` overflows with Rotary Position Embeddings (RoPE) across 5,000 tokens, causing `nan` loss. `bfloat16` matches `float32` dynamic range while halving memory and accelerating Tensor Core math.
2. **Gradient checkpointing:** Keeping `base_model.gradient_checkpointing_enable()` active drops peak VRAM from >14 GB down to ~2.6 GB for batch size 1, allowing `batch_size=4` with `GRAD_ACCUM=2` to run comfortably in cloud environments.
3. **Overfitting prevention:** On small financial datasets (78 days), a 421M parameter model with 7.2M LoRA parameters can easily memorize every training session. Adding `label_smoothing=0.05` and evaluating validation Brier per epoch prevents runaway logit growth.
4. **Platt scaling vs single temperature:** Scalar temperature scaling ($z / T$) only shrinks logit magnitude under an assumed 50/50 prior. Platt scaling ($P = \sigma(w \cdot \Delta z + b)$) fits an intercept $b$ that captures market regime asymmetry (September had 12 DOWN and 8 UP days), improving both calibration and accuracy.

---

## Architectural limitations & scaling roadmap

While Laya achieves 65% accuracy and a 0.2250 Brier score on this sample, scaling it to larger contexts exposes three structural bottlenecks:

1. **Mean pooling dilution:** ModernBERT averages all token hidden states across the sequence (`classifier_pooling: "mean"`). Averaging 5,000 to 15,000 tokens dilutes specific catalyst sentences with background table boilerplate.
2. **Model capacity ceiling:** Macroeconomic forecasting requires synthesizing multi-asset relationships across changing regimes. A 421M parameter encoder has limited expressiveness compared to multi-billion parameter foundation models.
3. **The path to 7B-8B sequence classifiers:** For larger contexts (16k to 128k tokens), the recommended successor is **Qwen-2.5-7B** or **Llama-3.1-8B** loaded as a sequence classifier (`AutoModelForSequenceClassification`). Causal attention pools from the final token, preserving sharp catalysts across the document while retaining Laya's non-autoregressive, calibrated probability interface.

---

## Quickstart

### 1. Extract fresh training data from Supabase

```bash
# Uses existing environment variables from apps/engine/.env or .env
python export_dataset.py --output-dir data --val-ratio 0.2
```

### 2. Set up the dedicated environment

```bash
cd experiments/laya-training
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run training with Platt calibration

```bash
python train.py \
  --model-name answerdotai/ModernBERT-large \
  --data-dir data \
  --output-dir output \
  --epochs 20 \
  --batch-size 4 \
  --grad-accum-steps 2 \
  --learning-rate 1e-4
```

### 4. Evaluate against historical arena benchmarks

```bash
python evaluate.py --model-dir output --val-file data/val.jsonl
```

### 5. Run unit tests

```bash
pytest test_pipeline.py
```
