---
tags: [verification, execution, model-config, performance]
category: concept
---

# Verifier Bypass

Verifier bypass allows specific LLM models to skip the skeptical verification agent stage during trade execution. This is configured via `SKIP_VERIFIER_OWNER_IDS` in `models.json` and applied in `main.py` during the per-decision processing loop.

## Configuration

```json
{
  "SKIP_VERIFIER_OWNER_IDS": ["MiniMax-M3", "deepseek-v4-flash"]
}
```

Models listed here receive an automatic `APPROVED` verification result with reasoning `"Skipped per model config"`, bypassing the contrarian context search and verification LLM call entirely.

## Rationale

Some models (e.g., MiniMax-M3, DeepSeek Flash) are used in simplified execution pipelines where full skeptical verification adds latency without commensurate benefit. Bypassing verification reduces pipeline time and LLM API costs for these fast models.

## Implementation

In `apps/engine/main.py`, before the verification step:

```python
from core.config import SKIP_VERIFIER_OWNER_IDS

if d.model_name in SKIP_VERIFIER_OWNER_IDS:
    verification = type(
        "VerificationResult",
        (),
        {"status": "APPROVED", "verification_reasoning": "Skipped per model config"},
    )()
else:
    verification = await verify_trading_decision(...)
```

## Related

- [[concepts/execution]] — Pre-market validation, Reg T checks, trade settlement
- [[concepts/minimax-portfolio]] — Simplified execution model for MiniMax-M3
- [[entities/autoresearch]] — Auto-research configuration includes verifier bypass settings
