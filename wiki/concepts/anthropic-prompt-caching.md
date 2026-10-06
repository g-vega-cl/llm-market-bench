---
tags: [anthropic, caching, cost-optimization, llm, observability]
category: concept
---

# Anthropic Prompt Caching

Anthropic's API supports prompt caching, which lets repeated prompt prefixes
(system prompts, large context blocks) be cached server-side so subsequent calls
read them at a fraction of the input-token cost. The engine enables this across
every Anthropic call site using explicit cache breakpoints plus top-level
automatic caching.

## How It Is Applied

Every Anthropic request is built with two caching mechanisms:

1. **Explicit system cache breakpoint** — the system prompt is passed as a list
   of content blocks with `cache_control: {"type": "ephemeral"}` on the text
   block, rather than as a plain string. This marks the system prompt as a
   cacheable prefix.
2. **Top-level automatic caching** — a `cache_control: {"type": "ephemeral"}`
   key is added to the request arguments, letting Anthropic automatically place
   cache breakpoints on the longest reusable prefix.

Example request shape:

python
args = {
    "model": model_name,
    "messages": current_messages,
    "max_tokens": 32000,
    "cache_control": {"type": "ephemeral"},
    "system": [
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }
    ],
}


## Call Sites

Caching is wired into all Anthropic entry points:

- **Tool loop** (`core/llm/handlers/anthropic.py`) — the primary analysis and
  verifier tool-execution loop.
- **Extraction args** (`core/llm/analysis_pipeline/prompt_assembly.py`) — the
  structured-output extraction path.
- **Verification** (`core/llm/verification.py`) — both the tool loop and the
  direct `create` call.
- **Discovery agent** (`analysis/discovery_agent.py`) — forced text completion.
- **Daily predictor** (`tasks/daily_predictor.py`) and **sector predictor**
  (`tasks/sector_predictor.py`) — direct prediction calls.
- **Autoresearch** (`autoresearch/researcher.py`) — research tool loop.

## MiniMax Exclusion

The Anthropic handler is also used to reach MiniMax's Anthropic-compatible
endpoint. Because MiniMax does not support Anthropic's `cache_control`
parameter, the handler detects MiniMax (via `base_url` or model name) and skips
both the top-level `cache_control` and the block-form system prompt, sending the
system prompt as a plain string instead. See [[concepts/minimax-portfolio]].

## Thinking Budget Parameterization

The tool loop accepts a `thinking_budget` argument (default `2048`) so callers
can tune extended-thinking token budgets per use case. The verifier passes
`1024` to keep verification cheap, while autoresearch passes `4096` for deeper
reasoning. See [[concepts/thinking-agents]].

## Observability

After each tool-loop response, the handler reads `resp.usage` and logs cache
telemetry when cache activity is present:


Anthropic [model] cache usage: read=<n>, create=<n>, uncached_input=<n>, output=<n>


This surfaces `cache_read_input_tokens` and `cache_creation_input_tokens` so
cache hit rates are auditable. See [[concepts/auditability]].

## Related

- [[entities/engine]]
- [[concepts/thinking-agents]]
- [[concepts/minimax-portfolio]]
- [[concepts/auditability]]
