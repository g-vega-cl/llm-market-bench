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

## The Reasoning Toolbox (Arsenal)

To expand beyond the 5 Whys, the system supports a pluggable toolbox of advanced reasoning frameworks. These are embedded in all core agent prompts, giving the models options to selectively apply the best approach:

1.  **MECE (Structuring)**: Ensures scenario analyses, risk checklists, and portfolio allocations are Mutually Exclusive (no logical overlap) and Collectively Exhaustive (no blindspots or gaps).
2.  **IS / IS NOT Analysis (Kepner-Tregoe)**: A diagnostic matrix to isolate causality by comparing where/when an event impact manifests (IS) against similar locations/assets where it does not (IS NOT).
3.  **Ishikawa (Fishbone) / 6 Ms**: Categorizes contributing drivers of market anomalies across Machine (tech/APIs), Method (strategy rules), Material (data inputs), Manpower (execution overrides), Measurement (ratios/indicators), and Milieu (macro regimes/volatility).

## Parallel Reasoning Loop

The engine runs multiple agents in parallel, each utilizing the same **System-Heavy** logic but reacting to different data windows. This creates a "Consensus of Reason," where we look for overlapping root causes rather than just overlapping tickers.

## Integration with System-Heavy Prompts

By placing the **Reasoning SOP** (including the 5 Whys instructions and the Reasoning Toolbox) inside the **System Prompt**, we treat "Thinking Style" as an evolvable trait. The Meta-Researcher (via the Auto-Researcher instruction set in [program.md](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/autoresearch/program.md)) can strategically inject, refine, or combine these mental models based on performance reports, tracking how these changes impact risk-adjusted returns.

See [[concepts/system-heavy-prompt]] for the architectural split and [[entities/autoresearch]] for the evolution loop.

