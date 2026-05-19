---
tags: [concept, reasoning, logic]
category: concept
---

# Reasoning Rigor & 5 Whys

The "LLM Market Bench" engine prioritizes depth of reasoning over simple pattern matching. We enforce this through structured prompt engineering and the **5 Whys** technique.

## The 5 Whys Technique

Originally developed at Toyota, the 5 Whys method involves asking "Why?" repeatedly to drill down to the root cause of a phenomenon. In our trading engine, the agents are instructed to apply this to market-moving news:

1.  **Event**: Company X announces a major partnership.
2.  **Why 1**: Because they want to expand their market share.
3.  **Why 2**: Because their current organic growth is slowing in their primary region.
4.  **Why 3**: Because a new competitor (Company Y) has captured 15% of the local demographic.
5.  **Why 4**: Because Company Y's supply chain is more vertically integrated.
6.  **Why 5 (Root Cause)**: Company X is pivoting to a partnership-heavy model to outsource supply chain risk and remain asset-light.

**Trading Decision**: Instead of just "Buy Company X," the agent might look for the specific partner that provides the vertical integration Company X lacks.

## Parallel Reasoning Loop

The engine runs multiple agents in parallel, each utilizing the same **System-Heavy** logic but reacting to different data windows. This creates a "Consensus of Reason," where we look for overlapping root causes rather than just overlapping tickers.

## Integration with System-Heavy Prompts

By placing the **Reasoning SOP** (including the 5 Whys instructions) inside the **System Prompt**, we treat "Thinking Style" as an evolvable trait. The Meta-Researcher can refine the reasoning steps, add new "mental models" (like MECE or First Principles), and observe how these changes impact risk-adjusted returns.

See [[concepts/system-heavy-prompt]] for the architectural split and [[entities/autoresearch]] for the evolution loop.
