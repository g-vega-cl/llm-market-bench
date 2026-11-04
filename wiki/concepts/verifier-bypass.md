---
tags: [verification, execution, model-config, performance]
category: concept
---

# Verifier bypass

Verifier bypass allows LLM portfolios to skip the skeptical verification agent stage during trade execution. The system scopes verification via `VERIFIER_ENABLED_OWNER_IDS` and `SKIP_VERIFIER_OWNER_IDS` in `packages/config/models.json`, applied in `apps/engine/pipeline/decision_processor.py` and `apps/engine/tasks/backtest_autoresearch.py` via `is_verifier_enabled_for_owner`.

As of November 2026, the second-step LLM Verifier is decommissioned across all active benchmark models (`VERIFIER_ENABLED_OWNER_IDS: []`). All portfolios execute under identical deterministic server-side guardrails.

## Historical Context and Forensic Audit

The second-step LLM Verifier was originally introduced to catch duplicate trades, hallucinated tickers, and reckless sizing. However, an audit of 500 historical verification traces revealed that the LLM Verifier became actively counterproductive:
1. **Excessive Rejection Rate**: Across 500 calls in `llm_reasoning_logs`, the verifier rejected 59.0% of trades outright (`REJECTED_VERIFICATION`) and modified 22.4% (`ADJUSTED_ALLOCATION`), leaving only 18.6% approved unmodified. For Claude Haiku, the rejection rate exceeded 80%.
2. **Allocation Floor Trap**: When the verifier returned `ADJUSTED_ALLOCATION` (typically reducing proposed position sizes by 50%), the resulting trade fell below the dynamic 10% equity floor ($1,000 minimum). In `decision_processor.py`, overwriting `qty` with `adjusted_quantity` after the initial floor clamp resulted in guaranteed `REJECTED_MARGIN` rejections on valid ETF allocations (such as XLV, XLE, and IEF).
3. **Data Quality Sensitivity**: Verifier prompts depended on `audit_financial_valuation` DCF calculations. When FMP endpoints returned HTTP 402 tier limits, fallback calculations with mis-scaled share counts caused the verifier to reject valid trades on mega-cap equities.
4. **Redundancy with Server-Side Guardrails**: Portfolios operating with the verifier bypassed (`gpt-5.6-luna`, `gemini-3.5-flash-lite`, `MiniMax-M3`) produced zero 48-hour duplicate trades across dozens of executions because deterministic server-side guards already enforce idempotency, market hours, market cap limits, 2% price drift limits, and cash capacity.

## Configuration

All active benchmark models bypass the verification LLM step:

```json
{
  "VERIFIER_ENABLED_OWNER_IDS": [],
  "SKIP_VERIFIER_OWNER_IDS": [
    "gpt-5.6-luna",
    "gemini-3.5-flash-lite",
    "MiniMax-M3",
    "claude-haiku-5-5",
    "deepseek-v4-flash"
  ]
}
```

Bypassed models receive an automatic `APPROVED` verification result with reasoning `"Skipped per verifier portfolio configuration"`, eliminating 15 to 45 seconds of latency and LLM token overhead per signal.

### Key-Presence Gating Semantics

`is_verifier_enabled_for_owner(owner_id)` in `apps/engine/core/config.py` gates on **key presence**, not list truthiness:

- If `VERIFIER_ENABLED_OWNER_IDS` is present in `models.json` (even as an empty list), the function is an **allow-list**: only owners listed there get verification, and every other owner bypasses it.
- If the key is absent entirely, the function falls back to the `SKIP_VERIFIER_OWNER_IDS` **deny-list**.
- `None` or an empty-string owner always returns `False`.

This means shipping `"VERIFIER_ENABLED_OWNER_IDS": []` is a deliberate, explicit decommission — not an accidental fall-through to the deny-list path.

## Deterministic Safety Checks

Bypassing the LLM verifier step does not bypass execution risk controls. All portfolios continue to undergo:
1. **Pre-market Validation**: Quote validity, NYSE hours, and minimum $2.0B market cap in `apps/engine/execution/validation.py`.
2. **Semantic Overlap Gate**: Vector cosine similarity checking (24-hour lookback) to eliminate duplicate or redundant theses on the same ticker.
3. **Stale Quote Guard**: 2% maximum price drift check between analysis and execution.
4. **Reg T and Cash-Only Capacity**: Dynamic 10% minimum position floor ($1,000) and strict cash buying power enforcement in `apps/engine/execution/reg_t_validation.py`.
5. **Quantity Floor Clamp Defense-in-Depth**: If `ADJUSTED_ALLOCATION` is ever returned by an experimental verifier run, `decision_processor.py` clamps the quantity up to `min_buy_threshold` when buying power permits, preventing false margin rejections.

## Implementation

In `apps/engine/pipeline/decision_processor.py`, before the verification step:

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
    verification = await verify_fn(...)
```

## Autoresearch Verifier Inspection Tool

Because `track_claude` is the only track subject to skeptical second-step verification, the auto-research meta-improver for `track_claude` has access to an optional function-calling tool: `inspect_verifier_rules_and_rejections`.

In alignment with **Principle 8 (Tool-First, Agency-Driven Architecture)**, verifier data is never bloated into the researcher prompt. Instead:
1. `researcher.py` provides `INSPECT_VERIFIER_RULES_TOOL` inside `run_tool_loop` exclusively when `track_id == 'track_claude'`.
2. The meta-researcher LLM decides autonomously whether to call the tool.
3. If invoked, `execute_inspect_verifier_rules_tool` returns the verbatim `VERIFIER_SYSTEM_PROMPT` SOP, recent `REJECTED_VERIFICATION` decisions, and an actionable prompt engineering nudge.
4. Non-Claude tracks (`track_default`, `track_openai`) strictly bypass this tool.

## ETF and Index Fund Valuation Exemption

Single-stock intrinsic valuation (`audit_financial_valuation` DCF and peer multiples) cannot run against ETFs (such as `SPY`, `QQQ`, `XLV`, `XLE`) because funds do not file GAAP income or cash-flow statements. The `VERIFIER_SYSTEM_PROMPT` explicitly exempts ETFs and index funds from single-stock DCF requirements, evaluating them instead via macroeconomic regime alignment, moving average trend, and sector concentration.

## Related

- [[concepts/execution]]: Pre-market validation, cash-only capacity checks, trade settlement
- [[concepts/minimax-portfolio]]: Simplified execution model for MiniMax-M3
- [[entities/autoresearch]]: Multi-track prompt optimization
- [[concepts/multi-track-autoresearch]]: Isolated prompt lineage per track
