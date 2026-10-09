---
tags: [anthropic, claude, haiku, thinking, llm, provider]
category: concept
---

# Anthropic Adaptive Thinking

Claude Haiku 5.5 replaces manual extended-thinking token budgets with **adaptive thinking** plus an **effort** level. The engine centralizes this provider-specific configuration in a single helper so every Anthropic call site stays consistent.

## The Helper

`get_anthropic_thinking_kwargs` lives in `apps/engine/core/llm/handlers/anthropic.py` and returns the correct thinking parameters for a given model:

```python
def get_anthropic_thinking_kwargs(model_name, budget_tokens=2048, effort="medium"):
    if "haiku-5-5" in model_name.lower():
        return {
            "thinking": {"type": "adaptive", "display": "summarized"},
            "output_config": {"effort": effort},
        }
    return {"thinking": {"type": "enabled", "budget_tokens": budget_tokens}}
```

- **Haiku 5.5** → adaptive thinking with `output_config.effort`; manual token budgets are omitted.
- **Legacy Claude models** (Haiku 4.5, Sonnet) → `enabled` thinking with an explicit `budget_tokens`.

## Call Sites

Every Anthropic call site routes through the helper, tuning the effort level to the task:

| Call site | Effort | Budget (legacy) |
| :--- | :--- | :--- |
| `handlers/anthropic.py` tool loop | `medium` | `thinking_budget` |
| `analysis_pipeline/prompt_assembly.py` extraction | `medium` | 2048 |
| `core/llm/verification.py` | `medium` | 1024 |
| `tasks/daily_predictor.py` | `medium` | 2048 |
| `tasks/sector_predictor.py` | `medium` | 2048 |
| `autoresearch/researcher.py` | `high` | 4096 |

## Thinking Block Preservation

Multi-turn tool loops preserve thinking blocks in assistant history across turns. Haiku 5.5 may return **empty / signature-only** thinking blocks; these are retained (including their `signature`) so the API does not reject the conversation with a 400. `redacted_thinking` blocks are also carried through verbatim.

## Related

- [[concepts/thinking-agents]]
- [[concepts/agents]]
- [[concepts/anthropic-prompt-caching]]
