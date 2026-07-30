---
tags: [prompt, autoresearch, ui, visualization]
category: concept
---

# Prompt Section Splitting

A utility and UI pattern for visually decomposing the monolithic `CORE_ANALYSIS_SYSTEM_PROMPT` into three distinct, semantically meaningful sections: a frozen header, an evolvable mutable strategy, and a frozen footer. This mirrors the engine-side `split_prompt` logic and makes the scope of the autoresearch system immediately legible to users.

## Motivation

The trading prompt is a long, single block of text. For users auditing the autoresearch system, it is critical to understand which parts of the prompt are immutable system constraints (price injection rules, tool requirements, output schema) and which parts are the actual trading strategies being iteratively optimized by the meta-researcher.

## How It Works

### Engine-Side Splitting

The Python engine (`apps/engine/core/llm/prompts.py`) defines a `split_prompt` function that parses the prompt using well-known section markers.

### Web-Side Splitting

The TypeScript utility `splitPromptSections` (`apps/web/src/features/autoresearch/utils/promptSections.ts`) replicates this logic for client-side rendering. It identifies:

- **Header (Frozen)**: Everything before the first mutable strategy marker (e.g., `=== REASONING RIGOR`). Contains system identity, critical tool usage requirements, and price injection rules.
- **Mutable Strategy (Evolvable)**: The section between the first mutable marker and the footer marker (e.g., `=== SMA MANAGEMENT RULES ===`). Contains trading philosophy, reasoning frameworks, entry/exit logic, and portfolio management rules. This is the target of the autoresearch loop.
- **Footer (Frozen)**: Everything from the footer marker onward. Contains SMA margin rules, trade signal definitions, and the mandatory structured JSON output schema.

### Fallback Behavior

If the standard section markers are not found (e.g., for custom or legacy prompts), the utility gracefully falls back to displaying the entire prompt as a single, un-split block.

## UI Presentation

The `ExperimentDetails` component in the autoresearch arena uses this utility to render a segmented card:

1.  **Engine Constraints & Tool Protocols** — Amber "Frozen / System Managed" badge.
2.  **Trading Strategy & Analysis Rules** — Emerald "Mutable / Evolved by Autoresearch" badge with a highlighted border.
3.  **Risk Rules & Output JSON Schema** — Amber "Frozen / System Managed" badge.

## Related

- [[entities/autoresearch-arena]]
- [[entities/autoresearch]]
- [[concepts/auto-research-prompt-improver]]
