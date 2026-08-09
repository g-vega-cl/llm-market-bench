---
tags: [autoresearch, prompt-engineering, trading-discipline, reasoning-blocks]
category: concept
---

# Modular Prompt Blocks

A mechanism enabling the Auto-Researcher meta-agent to dynamically toggle structured trading discipline and causal reasoning blocks into the trading agent's system prompt. Each block is a reusable, independently-selectable module defined in `apps/engine/autoresearch/prompt_blocks.py` that enforces a specific behavioral rule or analytical framework.

## Motivation

Previously, the Auto-Researcher could only rewrite free-form strategy text. This made it difficult to consistently enforce discipline rules (like letting winners run or cutting losers fast) across prompt mutations. Modular Prompt Blocks provide a library of hardened, pre-written blocks that the meta-researcher can slot in or out via a dedicated `selected_prompt_blocks` JSON field, without needing to author raw prompt text for these patterns.

## Available Blocks

| Block ID | Title | Purpose |
|----------|-------|---------|
| `let_winners_run` | LET WINNERS RUN | Trailing profit ratchet, momentum scale-in rules, thesis realization exit gates |
| `cut_losers_fast` | CUT LOSERS FAST | Immediate exit on thesis invalidation, asymmetric drawdown guardrails, no sunk-cost averaging |
| `catalyst_expiry_timer` | CATALYST EXPIRY TIMER | 48h post-catalyst exit rule for short-term news plays |
| `five_whys_causal` | 5 WHYS CAUSAL DEPTH | Deep root-cause validation via iterative questioning |
| `mece_risk_partition` | MECE RISK PARTITIONING | Mutually Exclusive, Collectively Exhaustive scenario analysis |

## Rendering Pipeline

1. **Meta-Researcher Output**: The Auto-Researcher returns `selected_prompt_blocks` (list of block IDs) in its `PromptResearchResult` JSON alongside custom `new_prompt_text`, `selected_tools`, etc.
2. **Prompt Assembly** (`apps/engine/core/llm/prompt_factory.py`): When building the trading agent's system prompt for an experiment track, `render_prompt_blocks()` converts the selected block IDs into formatted markdown and injects the resulting text **before** the mutable strategy section (and after the constraints header).
3. **Registry** (`apps/engine/autoresearch/prompt_blocks.py`): The `AVAILABLE_PROMPT_BLOCKS` dictionary maps each block ID to a title and content. The registry is single-source-of-truth; blocks can be added or modified there without changing the pipeline code.

## Self-Auditing Workflow

The auto-researcher program (`program.md`) now includes a structured self-auditing step where the meta-researcher reviews recent losing trades, evaluates exit timing and drawdown patterns, then selects appropriate discipline blocks to mitigate identified weaknesses.

## Integration

- **PromptResearchResult Model** (`researcher.py`): New `selected_prompt_blocks: list[str]` field with validated block IDs.
- **Prompt Store** (`prompt_store.py`): The `research_output` metadata column stores the full output, including `selected_prompt_blocks`, allowing downstream prompt assembly to read and render the blocks.
- **DB Post-Mortem Context** (`tools.py`): The auto-researcher can pre-query `model_trade_decisions` via `query_trade_postmortems()` to audit recent trade outcomes and verifier feedback before formulating its prompt changes. This gives data-driven grounding for block selection.

## Related

- [[entities/autoresearch]] — the meta-researcher agent that uses this mechanism
- [[concepts/auto-research-prompt-improver]] — weekly prompt iteration loop
- [[concepts/multi-track-autoresearch]] — track isolation that allows different block selections per portfolio group
- [[concepts/system-heavy-prompt]] — architecture pattern where blocks slot into the system prompt
