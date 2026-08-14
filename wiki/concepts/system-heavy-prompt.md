---
tags: [concept, prompt-engineering, auto-research, caching]
category: concept
---

# System-Heavy Prompt Architecture

The **System-Heavy Prompt Architecture** is a project-wide design principle applied to every agent prompt pair in `prompts.py`. It strictly separates static instructions from dynamic data across the system/user message boundary.

## Core Principle

Traditional LLM prompts mix **Static Logic** (rules, SOPs, constraints) with **Dynamic Data** (news, portfolio state) in the User message. In a System-Heavy setup, these are strictly decoupled:

1. **System Prompt (The Rulebook)**:
   - Contains 100% of the agent's reasoning logic, SOPs, tool-enforcement rules, output format requirements, and persona definition.
   - Never contains runtime data (`{placeholders}`).
   - For the primary analysis agent, this is stored in the database as a `PromptVariant` and is **evolvable** by the Meta-Researcher (specifically, the mutable strategies section is evolved, while system/formatting constraints are frozen).
   - For all other agents, it is hardcoded in `prompts.py`.

2. **User Prompt (The Data Case)**:
   - A minimal skeleton containing only section labels, `{placeholder}` variables for runtime data injection, and a single closing task directive ("Return ONLY...").
   - Contains no persona openers, no instructions, no SOPs.
   - Static in source code for all agents.
   - For auto-research experiment agents, the template used is `EXPERIMENT_USER_PROMPT_TEMPLATE` (a pull-based template). It strips all newsletter text and raw ledger data, relying on dynamic tool selection to retrieve this context and reducing the prompt cache footprint significantly.

## Motivations

### 1. Auto-Research Surface Area (Karpathy Ratchet)
By moving all trading logic into the System message, the Meta-Researcher can mutate the very foundations of an agent's strategy — not just append hints. If logic lived in the User prompt (source code), it would be invisible to the ratchet. See [[entities/autoresearch]].

### 2. Prompt Caching (Anthropic & DeepSeek)
Both Anthropic and DeepSeek cache prompts from the top down, creating a cache breakpoint at the longest common prefix shared across requests. Since the System message is fully static (identical on every call), it is cached after the first request. The User message — which changes every run (new news, new portfolio state, new prices) — is never cached. Keeping all instructions in the System prompt and all dynamic content in the User prompt maximizes cache hit rate and reduces cost per call.

## Scope: All 8 Agent Prompt Pairs

As of **2026-05-20**, this pattern is enforced across every agent in the system:

| Agent | System Prompt | User Prompt (data only) |
|---|---|---|
| [[concepts/agents]] (Analysis) | `CORE_ANALYSIS_SYSTEM_PROMPT` | `ANALYSIS_USER_PROMPT_TEMPLATE` |
| [[concepts/agents]] (Verifier) | `VERIFIER_SYSTEM_PROMPT` | `VERIFIER_USER_PROMPT_TEMPLATE` |
| [[concepts/agents]] (Synthesis) | `SYNTHESIS_SYSTEM_PROMPT` | `SYNTHESIS_USER_PROMPT_TEMPLATE` |
| [[concepts/agents]] (Manager) | `MANAGER_SYSTEM_PROMPT` | `MANAGER_USER_PROMPT_TEMPLATE` |
| [[concepts/agents]] (Relationship) | `RELATIONSHIP_SYSTEM_PROMPT` | `RELATIONSHIP_USER_PROMPT_TEMPLATE` |
| [[concepts/agents]] (Cause & Effect) | `CAUSE_AND_EFFECT_SYSTEM_PROMPT` | `CAUSE_AND_EFFECT_USER_PROMPT_TEMPLATE` |
| [[concepts/agents]] (De-Advertisement) | `DE_ADVERTISEMENT_SYSTEM_PROMPT` | `DE_ADVERTISEMENT_USER_PROMPT_TEMPLATE` |

## Invariants (Enforced by Tests)

The `TestPureDataInjectionUserPrompts` class in `test_prompts_refactor.py` enforces these contracts:
- User prompts must **not** contain persona openers (`"You are a..."`)
- User prompts must **not** contain instruction blocks or SOPs
- User prompts **must** contain all `{placeholder}` variables
- System prompts **must** own all rules previously in user prompts

## Related

- [[concepts/agents]] — detailed role and tool definitions for all 8 agents
- [[entities/autoresearch]] — module implementation and the Karpathy Ratchet
- [[entities/engine]] — how prompts are invoked in the daily pipeline
- [[concepts/auto-research-prompt-improver]] — the evolutionary loop
