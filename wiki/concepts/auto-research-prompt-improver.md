---
tags: [auto-research, prompt-improvement, meta-learning]
category: concept
---

# Auto-Research Prompt Improver

A meta-researcher LLM evaluates weekly live trading performance and iteratively improves the trading prompt, following Karpathy's autonomous research pattern. The system modifies only the `CORE_ANALYSIS_SYSTEM_PROMPT` — the system prompt that drives all trading agents.

## Architecture

The auto-research loop runs weekly:
1. **Evaluate**: Compare live trading performance against control portfolios
2. **Hypothesize**: Propose prompt changes to improve performance
3. **Validate**: Check proposed prompt against hard invariants (forbidden patterns, size limits)
4. **Activate**: If valid, deploy the new prompt for the next trading week

## Validation

The validator enforces only **hard invariants** — patterns that would break the trading loop's safety contract:
- Empty prompts
- Prompts over 1000 words
- Prompts containing "guess the price" or similar forbidden phrases

There are **no soft invariants or recommended tokens**. The prompt is an experiment space — the control portfolios and safety checker provide the real guardrails. Hardcoded token requirements would only constrain the researcher's ability to explore.

## Constraints

The researcher's `program.md` specifies:
- Only modify the `CORE_ANALYSIS_SYSTEM_PROMPT`
- Do NOT remove tool usage requirements
- Do NOT add instructions to output price fields (prices are system-provided)
- Keep the prompt under 1000 words
- Compatible with Gemini Flash and DeepSeek Flash

## Related

- [[entities/autoresearch]] — the implementation module
- [[concepts/tool-enforcement]] — why tool usage requirements are critical
- [[concepts/memory-feedback]] — the feedback loop that feeds into auto-research
