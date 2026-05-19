---
tags: [concept, prompt-engineering, auto-research]
category: concept
---

# System-Heavy Prompt Architecture

The **System-Heavy Prompt Architecture** is a design pattern used in the Auto-Research engine to maximize the surface area of evolutionary improvement for the trading agents.

## Core Principle

Traditional LLM prompts often mix **Static Logic** (rules, SOPs, constraints) with **Dynamic Data** (news, portfolio state) in the User message. In a "System-Heavy" setup, we strictly decouple these:

1.  **System Prompt (The Rulebook)**:
    *   Contains 100% of the reasoning logic, risk management rules (e.g., SMA rules), and output formatting requirements.
    *   This is the "DNA" of the agent.
    *   Stored in the database as a `PromptVariant`.
    *   **Evolvable**: The Meta-Researcher can modify any part of this logic during its weekly cycle.

2.  **User Prompt (The Data Case)**:
    *   A minimal skeleton that only contains placeholders for external data injection.
    *   Static in the source code (`ANALYSIS_USER_PROMPT_TEMPLATE`).
    *   Provides the "Environment" for the logic to act upon.

## Why This Matters for Auto-Research

By moving the trading SOPs and logic points into the System message, we enable the **Karpathy Ratchet** to operate on the very foundations of the agent's strategy. If the logic were hardcoded in the User prompt template (source code), the Meta-Researcher would only be able to suggest "hints" rather than fundamental rule changes.

In this architecture:
-   The **PromptFactory** acts as the assembler.
-   The **PromptStore** acts as the memory.
-   The **Meta-Researcher** acts as the evolutionary pressure.

## Implementation Details

See [[entities/autoresearch]] for the module implementation and [[entities/engine]] for how these prompts are invoked in the daily pipeline.
