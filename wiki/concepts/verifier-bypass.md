---
tags: [verification, execution, model-config, performance]
category: concept
---

# Verifier bypass

Verifier bypass allows specific LLM portfolios to skip the skeptical verification agent stage during trade execution. The system scopes verification via `VERIFIER_ENABLED_OWNER_IDS` and `SKIP_VERIFIER_OWNER_IDS` in `models.json`, applied in `main.py` and `backtest_autoresearch.py` via `is_verifier_enabled_for_owner`.

## Configuration

Only portfolios in `track_claude` run the skeptical second-step verification. All other models bypass it:

```json
{
  "VERIFIER_ENABLED_OWNER_IDS": [
    "claude-haiku-4-5",
    "deepseek-v4-flash"
  ],
  "SKIP_VERIFIER_OWNER_IDS": [
    "gpt-5.6-luna",
    "gemini-3.5-flash-lite",
    "deepseek-v4-pro",
    "MiniMax-M3"
  ]
}
```

Bypassed models receive an automatic `APPROVED` verification result with reasoning `"Skipped per verifier portfolio configuration"`, bypassing the verification LLM call entirely.

## Mechanical safety checks

Bypassing the LLM verifier step does not bypass execution risk controls. All portfolios continue to undergo:
1. Current quote and price sanity bounds
2. Reg T initial margin and buying power checks
3. 10% minimum position enforcement
4. Slippage simulation and trade settlement

## Implementation

In `apps/engine/main.py`, before the verification step:

```python
from core.config import is_verifier_enabled_for_owner
from core.models import VerificationResult

if not is_verifier_enabled_for_owner(d.model_name):
    verification = VerificationResult(
        status="APPROVED",
        verification_reasoning="Skipped per verifier portfolio configuration",
        confidence_score=100,
    )
else:
    verification = await verify_trading_decision(...)
```

## Related

- [[concepts/execution]] — Pre-market validation, Reg T checks, trade settlement
- [[concepts/minimax-portfolio]] — Simplified execution model for MiniMax-M3
- [[entities/autoresearch]] — Multi-track prompt optimization
