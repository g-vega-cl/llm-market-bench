---
tags: [architecture, tools, prompts, autoresearch, agency]
category: concept
---

# Tool-First, Agency-Driven Architecture

The **Tool-First, Agency-Driven Architecture** is a foundational architectural mandate of `llm-market-bench` (codified as Principle 8 in `GEMINI.md`). It dictates that autonomous reasoning models and Autoresearchers must be granted full agency to formulate their own hypotheses, prompts, and behaviors, rather than being micromanaged by human or coding-agent prompt injections.

---

## 1. Core Philosophy: Agency vs. Puppet-Mastering

Traditional LLM workflows often suffer from "prompt puppet-mastering": whenever a model makes a poor decision or a new domain feature is introduced, engineers instinctively modify the system prompt to append rules, heuristics, and guards (e.g. *"Only buy tech when VIX < 20"* or hardcoding pre-trade audit checklists).

This practice breaks autonomy and pollutes the prompt space:
1. **Fragile Overfitting**: Static instructions force the model down rigid reasoning paths that degrade under regime shifts.
2. **Attention Dilution ("Lost in the Middle")**: Shoving raw news batches, macro snapshots, and ledger dumps into the prompt bloats context windows, dilutes attention, and degrades calibration.
3. **Usurping the Auto-Researcher**: The Karpathy Autoresearch loop (`[[entities/autoresearch]]`) exists specifically to discover optimal trading prompts and tool-selection strategies empirically. Hardcoding developer rules short-circuits this evolutionary mechanism.

---

## 2. Dual-Taxonomy of LLM Tasks

To maintain clarity across the platform, LLM tasks are divided into two strictly decoupled categories:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│              CATEGORY A: AUTONOMOUS DECISION / TRADING AGENTS               │
│       (Trading Analysis Agents, Autoresearchers, Alpha Discovery)           │
├─────────────────────────────────────────────────────────────────────────────┤
│ • Objective: Open-ended market reasoning, hypothesis testing, alpha discovery│
│ • Evaluated by: Live market returns, Brier calibration, Ratchet Score       │
│ • Prompt Ownership: The Auto-Researcher (the LLM itself mutates prompts)   │
│ • Developer Rule: ZERO hardcoded trading filters or pre-injected data tables│
│   Developers ONLY build callable tools; the LLM chooses whether to use them │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ▲
                                      │  (Strict Boundary)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              CATEGORY B: PRODUCTION PIPELINE & UTILITY FLOWS                │
│    (Daily Newsletter Generator, De-Advertisement Cleaner, Synthesis)        │
├─────────────────────────────────────────────────────────────────────────────┤
│ • Objective: Deterministic data transformation, editorial formatting, hygiene│
│ • Evaluated by: Editorial polish, schema adherence, token efficiency        │
│ • Prompt Ownership: Humans & developers craft and maintain prompts directly │
│ • Developer Rule: Direct prompt engineering is expected! Humans set tone,   │
│   Markdown headers (e.g. 6-min read format), and inject direct data payloads│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. The Developer & Coding-Agent Boundary (Category A)

When working on autonomous decision agents (such as `apps/engine/core/llm/analysis.py` or `apps/engine/tasks/daily_predictor.py`), coding agents and developers must adhere to strict boundaries:

### Prohibited (Anti-Patterns)
- ❌ **Do NOT modify baseline system prompts** (`CORE_ANALYSIS_SYSTEM_PROMPT`) to add trading heuristics, setup filters, or risk rules.
- ❌ **Do NOT inject massive static data dumps** (raw news batches, macro snapshots, ledger XML) into user prompts.
- ❌ **Do NOT write prompt hacks** for specific models (e.g. the historical `GPT54_NANO_PRE_AUDIT_PROMPT` which had to be reverted in commit `34ae76a6`).

### Mandated (Best Practices)
- ✅ **Package Capabilities as Tools**: Implement clean, callable tools with descriptive docstrings and schemas in `apps/engine/core/llm/tools.py` and register them in `packages/config/tools.json`.
- ✅ **Provide Modular Blocks for Autoresearch**: If crafting a new reasoning pattern (e.g. options volatility bounding or macro regime routing), register it as an optional block in `apps/engine/autoresearch/prompt_blocks.py`. The Autoresearcher LLM can then choose to test it via `selected_prompt_blocks`.
- ✅ **Pull Over Push**: Give the agent lean seed context (e.g. current date, high-level directive) and pull tools (`get_portfolio_ledger`, `get_todays_news_menu`, `get_options_vol_surface`, `get_yield_curve_regime`). The agent pulls whatever information it deems relevant.

---

## 4. Contract Enforcement

These invariants are enforced by unit tests in `apps/engine/tests/test_tool_first_architecture_contracts.py`:
- Baseline system prompts are scanned to ensure zero hardcoded developer heuristics or model-specific pre-audit blocks.
- Modular blocks in `prompt_blocks.py` must remain separate from baseline prompts.
- Core pull tools must remain registered in `CANONICAL_TOOLS_REGISTRY`.

---

## Related

- [[concepts/system-heavy-prompt]] — system/user prompt separation and pull-based workspace design
- [[concepts/anthropic-fs-insights]] — tools over prompt forcing and domain analytics
- [[entities/autoresearch]] — the evolutionary prompt mutation engine (Karpathy Ratchet)
- [[concepts/agents]] — the 7 specialized multi-agent roles and interaction flow
- [[entities/tool-registry]] — canonical tool registry
