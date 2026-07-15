---
tags: [validation, resilience, llm-output, pydantic]
category: concept
---

# Output Normalization

LLMs often produce well‑reasoned but slightly non‑canonical output—lowercase signals, extra spaces in enum values, or custom labels for catalyst types. Pydantic **field validators** on `DecisionObject`, `MacroEvent`, and `VerificationResult` transparently clean and map these variations to a consistent set of allowed values, preventing downstream parsing errors without requiring the prompting stage to be perfect.

## DecisionObject Normalizations

| Validator | Input Examples | Canonical Output |
|-----------|----------------|------------------|
| `normalize_signal` | `" buy "`, `"Buy"`, `"BUY"` | `"BUY"`, `"SELL"`, or `"HOLD"` (whitespace stripped) |
| `normalize_catalyst_type` | `"MERGERS"`, `"M&A"`, `"macro_economics"`, `"geopolitical_risk_trade_rerouting"` | Known variations mapped to canonical literals (e.g., `"M_A"`, `"MACRO"`); unrecognised → `"OTHER"` |
| `normalize_catalyst_duration` | `"SHORT"`, `"short-term"`, `"short term"` | Spaced/hyphenated/shortened forms → `"SHORT_TERM"`, `"MEDIUM_TERM"`, `"LONG_TERM"`, or `"INTRADAY"`; fallback → `"SHORT_TERM"` |

## MacroEvent Normalizations

| Validator | Input Examples | Canonical Output |
|-----------|----------------|------------------|
| `normalize_impact` | `"Bullish"`, `" bearIsh"` | `"BULLISH"`, `"BEARISH"`, or `"NEUTRAL"` |
| `normalize_catalyst_type` | Same mapping as `DecisionObject`, but fallback → `"MACRO"` rather than `"OTHER"` |

## VerificationResult Normalization

| Validator | Input Examples | Canonical Output |
|-----------|----------------|------------------|
| `normalize_status` | `"approved"`, `"rejected"` | `"APPROVED"`, `"REJECTED"` → `"REJECTED_VERIFICATION"` |

## Why It Matters

- **Pipeline robustness** – prevents `ValidationError` from non‑deterministic LLM output formatting.
- **Auditability** – canonical values are stored even when the originating prompt did not perfectly adhere to the schema.
- **Fallbacks instead of crashes** – unknown catalyst types receive a safe default rather than aborting the entire analysis batch.

## Related

- [[concepts/model-anomalies]] — catalog of LLM behavioral oddities that motivate this layer
- [[entities/engine]] — the Python engine where these models live
- [[concepts/tool-enforcement]] — another layer of hallucination prevention
- [[concepts/auditability]] — ensuring every value can be traced back to its raw LLM output
