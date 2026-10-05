---
tags: [laya, open-source, system-one, decisions-model, modernbert, self-hosted, predictor, daily-predictor]
category: concept
---

# Laya Decisions Model

**Laya** (`convaiinnovations/laya-typed-decisions`, Convai Innovations) is an open-source, non-autoregressive *System One* probability classifier and decision engine based on a 421M-parameter **ModernBERT-large** backbone. Like TypeSafe Jev (`[[concepts/jev-decisions-model]]`), Laya accepts a market `state` (context/ticker) and typed questions with structured criteria, returning mathematically calibrated probabilities in a single forward pass without autoregressive text generation or hallucination risk.

Unlike Jev—which is a closed, proprietary model hosted via OpenRouter's Decisions API—Laya is released under the **Apache 2.0** license with open weights, designed to be self-hosted on dedicated GPU infrastructure or in lightweight containers.

---

## Comparison: Laya vs. TypeSafe Jev

| Feature / Metric | TypeSafe Jev 1.13.0 | Convai Laya (`typed-decisions`) | Advantage |
| :--- | :--- | :--- | :--- |
| **Weights & License** | Closed API | **Apache 2.0 Open Weights** | Privacy, zero API token cost, self-hostable |
| **Hosting Model** | OpenRouter Alpha Decisions API | **Self-hosted** (`laya-serve` or in-process) | Full local control |
| **Backbone Architecture** | Proprietary Classifier | **ModernBERT-large** (421M params) | Open research & fine-tuning |
| **Context Window** | **32,000 tokens** | 1,024 tokens (up to 8,192 with RoPE) | Jev leads on long context (transcripts, multi-statement history) |
| **Inference Latency** | 236–276 ms (remote network p50) | **~32.8–39.5 ms** (local GPU forward pass) | **~7x faster** execution |
| **Typed Decisions Accuracy** | 0.727 | **0.766** (clears teacher ceiling of 0.735) | +0.039 on typed decisions |
| **Brier Score / Calibration** | 0.148 Brier / 0.144 ECE | **0.062 Brier / 0.081 ECE** (fitted) | Sharper probabilistic calibration |
| **High Cardinality (>20 options)** | **0.870** (Banking77, 72 options) | 0.425 (due to token head sharing) | Jev leads on >20 options |

For binary market direction classification (`UP` vs `DOWN`), option cardinality is small (2 options), making Laya exceptionally well suited for low-latency, zero-cost System One predictions.

---

## Self-Hosting Outside This Repo

Because Laya requires a PyTorch/CUDA runtime and model weights (~800 MB), hosting it outside the main repository environment keeps `apps/engine` lightweight and decoupled from local machine drivers.

### 1. Direct Python Microservice (`laya-serve`)

Laya includes a built-in server that natively implements the **Jev-compatible `POST /v1/systemone` API**.

```bash
# In an isolated virtualenv outside llm-market-bench
python3 -m venv ~/.local/share/laya-env
~/.local/share/laya-env/bin/pip install -U "laya[serve]" torch

# Run with CUDA acceleration (preloads checkpoints for instant ~33ms response)
LAYA_DEVICE=cuda LAYA_PRELOAD=1 ~/.local/share/laya-env/bin/laya-serve --host 0.0.0.0 --port 8000
```

### 2. Systemd Background Service (`/etc/systemd/system/laya.service`)

To run Laya as a permanent background service on your local GPU:

```ini
[Unit]
Description=Laya Decision Model Inference Server
After=network.target

[Service]
Type=simple
User=cv
WorkingDirectory=/home/cv
Environment=LAYA_DEVICE=cuda
Environment=LAYA_PRELOAD=1
Environment=LAYA_MODEL=typed-decisions
ExecStart=/home/cv/.local/share/laya-env/bin/laya-serve --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now laya
```

### 3. Docker Container

Alternatively, run Laya in a GPU-accelerated Docker container:

```bash
docker run -d \
  --name laya-server \
  --gpus all \
  --restart unless-stopped \
  -p 8000:8000 \
  -e LAYA_DEVICE=cuda \
  -e LAYA_PRELOAD=1 \
  ghcr.io/nandhakishorm/laya:latest
```

### 4. Remote / CI Access via Tunnel

When production daily predictions run in GitHub Actions (`.github/workflows/daily-predictor.yml`), the CI runner needs an HTTP path to reach your self-hosted instance. You can expose your local port 8000 securely with Cloudflare Tunnel, Tailscale Funnel, or ngrok:

```bash
# Example with Cloudflare Tunnel:
cloudflared tunnel --url http://localhost:8000
```

Add an optional authentication token by launching `laya-serve` with:
```bash
LAYA_API_KEY="your-secret-token" laya-serve --port 8000
```
Requests must then pass `Authorization: Bearer <your-secret-token>`.

---

## API Contract (Jev-Compatible)

`laya-serve` accepts the exact same question structure and payload as Jev:

### Request
`POST http://localhost:8000/v1/systemone`
```json
{
  "state": {
    "ticker": "SPY",
    "market_context": "Pre-market S&P futures +0.45%, VIX 14.8, 10Y Treasury yield flat at 4.12%."
  },
  "questions": {
    "direction": {
      "type": "choice",
      "instructions": "Will SPY close HIGHER (UP) or LOWER (DOWN) at 4:00 PM ET vs the 9:30 AM ET Open?",
      "criteria": {
        "UP": "Gap open holds above 20-day SMA, declining VIX, strong breadth.",
        "DOWN": "Pre-market gap rejection, rising bond yields, negative macro catalyst."
      }
    }
  }
}
```

### Response
```json
{
  "answers": {
    "direction": {
      "type": "choice",
      "choice": "UP",
      "confidence": 0.814,
      "probabilities": {
        "UP": 0.814,
        "DOWN": 0.186
      }
    }
  },
  "routing": {
    "model": "typed-decisions"
  }
}
```

---

## Empirical Fine-Tuning & Calibration Findings (`experiments/laya-training/`)

In October 2026, an experimental workbench fine-tuned ModernBERT-large (`convaiinnovations/laya-typed-decisions`) on 78 historical pre-market macro contexts (~5,000 tokens) with out-of-sample forward testing across 20 September 2026 trading sessions.

### Benchmark Performance

| Evaluation Stage | Out-of-Sample Accuracy | Brier Score | Notes |
|---|---|---|---|
| Random Guess Baseline | 50.0% | 0.2500 | Theoretical uninformative baseline |
| Zero-shot / Under-trained (10 epochs, lr=3e-5) | 45.0% | 0.2844 | Stalled at loss ~0.695 due to learning rate floor |
| Overfit Checkpoint (25 epochs, no label smoothing) | 55.0% | 0.3559 | Train loss collapsed to 0.048; logit explosion ruined Brier |
| Best LoRA Checkpoint (Epoch 17 + Label Smoothing) | 60.0% | 0.3100 | Stable train loss ~0.117; prevented logit explosion |
| Temperature Scaled ($T=2.096$) | 60.0% | 0.2654 | Deflated overconfident logits toward 50/50 |
| **Platt Calibrated ($w=0.485, b=-0.182$)** | **65.0%** | **0.2250** | **Learned 60/40 directional regime; flipped borderline error** |

### Key Technical Findings

1. **Hardware precision requirements:** On Ampere and Hopper architectures (A100, H100), `torch.bfloat16` is required. Standard `float16` overflows with Rotary Position Embeddings (RoPE) across 5,000 tokens, generating `nan` loss. `bfloat16` matches `float32` range while cutting VRAM in half.
2. **Gradient checkpointing:** Calling `base_model.gradient_checkpointing_enable()` drops peak forward/backward VRAM from >14 GB to 2.6 GB for batch size 1, permitting batch sizes of 4 to 8.
3. **Overfitting dynamics on small sample sizes:** With 78 training days, a 421M parameter model with 7.2M LoRA parameters can easily memorize the dataset within 20 epochs. Adding `label_smoothing=0.05` and evaluating validation Brier score per epoch prevents logit explosion and locks in peak generalization.
4. **Platt scaling vs scalar temperature:** Scalar temperature scaling ($z / T$) assumes an exact 50/50 market prior. Platt scaling ($P = \sigma(w \cdot \Delta z + b)$) learns an intercept $b$ that reflects market regime asymmetry (September had 12 DOWN and 8 UP sessions), shifting borderline predictions into the higher-probability regime.

### Architectural Limits & Future Horizon

ModernBERT-large is currently the largest open bidirectional encoder available. However, scaling market context from 5,000 to 30,000+ tokens introduces structural constraints:

1. **Mean pooling dilution:** ModernBERT averages all token vectors (`classifier_pooling: "mean"`). Averaging tens of thousands of tokens dilutes catalyst sentences with background table noise.
2. **Model capacity:** Macroeconomic forecasting requires synthesizing multi-asset relationships across changing interest rate, inflation, and liquidity regimes. A 421M parameter model faces capacity constraints on complex market dynamics.
3. **7B-8B sequence classifiers:** For larger contexts (16k to 128k tokens), the recommended successor is **Qwen-2.5-7B** or **Llama-3.1-8B** loaded as a sequence classifier (`AutoModelForSequenceClassification`). Causal attention pools from the final token, preserving sharp catalysts while retaining Laya's non-autoregressive, calibrated probability interface.

---

## Planned Engine Integration (`llm-market-bench`)

When ready to wire Laya into the repository as a 4th contestant:

1. **Environment Variables**:
   - `LAYA_SERVER_URL`: URL of the self-hosted endpoint (e.g. `http://localhost:8000` or public tunnel URL).
   - `LAYA_API_KEY`: Optional Bearer token.
2. **Graceful Fallback**:
   - If `LAYA_SERVER_URL` is unreachable or offline, the prediction task logs a warning and skips Laya, allowing DeepSeek, MiniMax, and Jev to execute uninterrupted.
3. **Arena & Systematic Trading**:
   - Participates in `sys-daily-spy-close-laya-typed-decisions` (close-exit portfolio trading directional bias with zero expected return target).
4. **Autoresearch**:
   - Independent criteria lineage evolved weekly by OpenAI Luna (`gpt-5.6-luna`), maintaining symmetric rules for `UP` and `DOWN`.

---

## Related

- [[concepts/jev-decisions-model]] — OpenRouter hosted System One decision model
- [[entities/daily-market-predictor]] — arena pipeline Laya will participate in
- [[concepts/multi-track-autoresearch]] — weekly prompt and criteria optimization tracks
- [[concepts/daily-spy-live-trading]] — systematic trading execution for direction-only models
