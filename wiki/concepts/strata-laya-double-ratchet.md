---
tags: [autoresearch, strata, laya, double-ratchet, modernbert, qwen, pipeline]
category: concept
---

# Strata & Laya Double-Ratchet

The **Strata & Laya Double-Ratchet** is a two-step co-evolutionary prompt optimization architecture pairing local **Qwen via Strata** (`http://localhost:8080/v1`) with **Laya** (`ModernBERT-large` running on `http://127.0.0.1:8081/v1/systemone` via `laya.cpp`).

---

## Two-Step Pipeline

Rather than asking a single model to both digest noisy multi-channel newsletters and classify market direction simultaneously, the pipeline decouples ingestion and decision-making into two distinct steps:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                          STEP 1: INGESTION                             │
│                                                                        │
│   Raw Feeds (Newsletters, Pre-Market Quotes, FRED Prints, Options)     │
│                                   │                                    │
│                                   ▼                                    │
│                  Qwen via Strata (:8080)                               │
│                  (Prompt 1: Ingestion Prompt)                          │
│                                   │                                    │
│                                   ▼                                    │
│             High-Density Daily Document (~200–240 words, <300 tokens)  │
│             (Macro/Yields, Overnight Tape, Options, Catalysts)         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        STEP 2 & 3: PREDICTION                          │
│                                                                        │
│   Daily Document + Prompt 2: Laya Criteria (UP / DOWN / Gate)          │
│                                   │                                    │
│                                   ▼                                    │
│                  Laya Local (:8081) [laya.cpp CUDA]                    │
│                  POST /v1/systemone (ModernBERT-large)                 │
│                                   │                                    │
│                                   ▼                                    │
│              SPY Intraday Direction (UP / DOWN / NO_TRADE)             │
│              Zero Truncation (100% of Document Evaluated)              │
└────────────────────────────────────────────────────────────────────────┘
```

### Step 1: Document Distillation (Qwen / Strata)
- **Input**: Raw uncompressed point-in-time morning observations timestamped before 09:15 AM ET (individual ingested financial newsletters, FMP/Polygon overnight gaps, FRED 8:30 AM economic surprises, options Max Pain and put/call skew, prior session VWAP/CLV intraday profiles).
- **Execution**: Qwen generates a standardized, dense catalyst briefing document (~200–240 words, under 300 tokens) fitting 100% within Laya's 320-token state budget without truncation.
- **Prompt 1 (Ingestion Prompt)**: Evolves *how* the raw data is filtered, structured, and distilled.

### Step 2 & 3: Direction Classification (Laya)
- **Input**: The daily document produced in Step 1, accompanied by Prompt 2 (the decision criteria for UP vs DOWN and confidence gate `min_confidence`).
- **Execution**: `laya.cpp` evaluates the document and criteria in a single non-autoregressive forward pass (~33 ms).
- **Prompt 2 (Prediction Criteria)**: Evolves *how* Laya interprets the extracted signals to predict whether SPY closes higher or lower at 4:00 PM ET compared to 9:30 AM ET open.

---

## Co-Evolution & The Atomic Ratchet

To prevent the credit assignment trap where one prompt mutates while the other falls out of alignment:
1. **Atomic Mutation**: The local meta-researcher (Qwen on Strata) generates Prompt 1 and Prompt 2 simultaneously in a single JSON payload.
2. **Interaction Contract**: Prompt 2's criteria are explicitly written to consume the exact sections, metrics, and definitions produced by Prompt 1.
3. **Atomic Advancement**: The pair $(P_1, P_2)$ advances only if the joint candidate score exceeds the active baseline on [[concepts/pure-directional-scoring]].

---

## 15% Sequestered Evaluation Slice (Overfitting Defense)

To defend against in-sample memorization and regime bias:
- **Active Ratchet Pool (85%, ~430 days)**: Used exclusively during tournament iteration loops.
- **Sequestered Held-Out Slice (15%, ~75 days)**: Randomly sampled using a deterministic seed (`seed=42`) and held out completely from the search loop.
- **Post-Ratchet Verification**: The winning champion pair is evaluated on the sequestered slice after tournament completion to compute the true out-of-sample win rate and Brier score.

## Real-Life Daily Synthesis Protocol (MANDATORY)

> [!IMPORTANT]
> **Hard Requirement**: Every single session day generates a brand-new Qwen brief on every mutation iteration, exactly mirroring live daily 9:15 AM ET execution.

In production tournaments, brief reuse across mutations is strictly disabled via `--no-cache`. This guarantees that each candidate prompt pair $(P_1, P_2)$ is evaluated strictly on end-to-end synthetic generations freshly produced from point-in-time morning observations, with zero data leakage or cached synthesis artifacts.

---

## Laya State Budget & Zero-Truncation Contract

Reverse-engineering of the `laya-cli` binary (`/home/cv/laya/laya-cli`) reveals that the native CUDA kernels enforce a strict sequence layout:
- `max_len = 512` (total maximum sequence tokens)
- `head_max_len = 192` (reserved for questions and options criteria)
- **State Context Budget = 320 tokens (~240 words)**

To ensure Laya evaluates **100% of the daily briefing with zero truncation**, Prompt 1 strictly instructs Qwen to produce high-density briefings of **200 to 240 words (under 300 tokens)**. Every word generated by Qwen is passed directly to Laya without truncation.

---

## Max Reasoning & Full Newsletter Ingestion (Zero-Truncation Pipeline)

To maximize Qwen's analytical intelligence across multi-channel morning inputs:
1. **Unconstrained Reasoning**: `STRATA_REASONING_BUDGET_TOKENS` defaults to `-1`, allowing Qwen to generate unconstrained chain-of-thought tokens without artificial cutoffs.
2. **Full Body Ingestion**: Newsletters are no longer truncated to arbitrary character limits (`[:500]`). Qwen ingests 100% of substantive financial reporting.
3. **Local Deterministic De-Advertisement Pass**: Ingested newsletters undergo MIME email header decoding (`=?utf-8?B?...?=` $\rightarrow$ clean text) and deterministic stripping of HTML tags, sponsor logos (*Autocamp*, *Cinnabon*), podcast plugs, and legal unsubscribe disclaimers before being fed to Qwen.

---

## Strategy C: Multi-Fidelity Early Pruning (Throughput Optimization)

Evaluating 432 trading days with unconstrained reasoning takes ~2.0 hours per candidate iteration. To optimize throughput without sacrificing full-dataset training on winning models:
1. **Stage 1 (Filter Slice, 80 Trading Days)**: Every candidate mutation pair $(P_1, P_2)$ is first evaluated on an 80-day regime-diverse slice (~22 minutes).
2. **Early Rejection Rule**: If candidate filter score delta vs champion's filter score is less than `-1.50` (`delta < -1.50`), the mutation is **discarded immediately**, saving ~1.5 hours of wasted compute on regressive candidates.
3. **Stage 2 (Full Confirmation, 432 Trading Days)**: If `delta >= -1.50` (candidate is competitive or winning), evaluation continues across all remaining 352 days. If the full 432-day score beats the active champion, it is promoted to the new Champion.

---

## Persistent SQLite Document Caching (Optional Fast Mode)

For development or fast criteria-only search, briefings can be persisted in SQLite (`.local_autoresearch_cache.db` in table `double_ratchet_documents`) keyed by `(target_date, prompt_hash)`. In production ratchet mode, `--no-cache` bypasses this table to guarantee fresh per-day synthesis.

---

## Zero External API Calls (MANDATORY HARD REQUIREMENT)

> [!CAUTION]
> **Hard Cost & Token Safety Requirement**: During local autoresearch, double-ratchet tournaments, and offline backtests, calling external or cloud LLM APIs (Anthropic, OpenAI, OpenRouter Jev, etc.) is **STRICTLY PROHIBITED**.

Iterating across hundreds of trading sessions over multiple generations causes massive API credit drain. All inference for both distillation and decision classification must run 100% locally on dedicated hardware (Strata and Laya). 

If a local server encounters transient engine stalls, PCIe desynchronization, or engine reload cycles, pipelines must execute local retries with progressive backoff. Cloud fallbacks are completely disabled to prevent unintended API egress and credit consumption.

---

## CLI Commands

```bash
# Check server readiness
./apps/engine/.venv/bin/python3 -m apps.engine.local_autoresearch.runner --check-strata
./apps/engine/.venv/bin/python3 -m apps.engine.local_autoresearch.runner --check-laya

# Run a quick test pass (2 iterations across 15 days)
./apps/engine/.venv/bin/python3 -m apps.engine.local_autoresearch.runner \
  --double-ratchet --iterations 2 --max-eval-days 15

# Run full tournament across active pool with fresh daily briefings and 15% held-out slice verification
./apps/engine/.venv/bin/python3 -m apps.engine.local_autoresearch.runner \
  --double-ratchet --iterations 10 --no-cache --cache-db .local_autoresearch_cache.db
```

---

## Related
- [[entities/local-autoresearch]] — Local prompt tournament orchestrator
- [[concepts/laya-decisions-model]] — ModernBERT-large decision classifier
- [[entities/daily-market-predictor]] — Morning arena predicting intraday SPY direction
- [[concepts/pure-directional-scoring]] — Directional scoring metric
