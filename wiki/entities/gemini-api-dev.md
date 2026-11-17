---
tags: [gemini, api, skill, development]
category: entity
---

# Gemini API Development Skill

Reference skill for calling the Google Gemini API within the LLM Market Bench project. Ensures consistent, up-to-date usage of the Gemini Interactions API across all Python and TypeScript code.

## Purpose

The project uses Gemini models (e.g., `gemini-3.5-flash-lite`, `gemini-3.8-flash`) as one of several LLM providers in the trading pipeline. This skill provides developers with current API patterns, model selection guidance, and migration references to prevent usage of deprecated APIs and models.

## Location

- Skill definition: `.agents/skills/gemini-api-dev/SKILL.md`
- SDK examples reference: `.agents/skills/gemini-api-dev/references/sdk-examples.md`
- Migration reference: `.agents/skills/gemini-api-dev/references/migration.md`
- Claude Code symlink: `.claude/skills/gemini-api-dev` → `.agents/skills/gemini-api-dev`

## Key Guidance

- Uses `google-genai` SDK >= 2.0.0 (Python) or `@google/genai` >= 2.0.0 (TypeScript)
- Interactions API (`client.interactions.create()`) replaces legacy `generateContent`
- Current models: `gemini-4-hydrogen` (GA 2026-11-12), `gemini-3.8-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-pro-preview`, `gemini-nano-banana-2.1`. This repo's Gemini slot deliberately stays on `gemini-3.5-flash-lite` for cost — see [[concepts/model-registry]]
- Deprecated models: `gemini-2.5-*`, `gemini-2.0-*`, `gemini-1.5-*` — never use; substitute `gemini-3.8-flash` instead
- Thinking configuration uses `thinking_level` (`minimal`, `low`, `medium`, `high`) not the deprecated `thinking_budget` parameter
- Managed agents (`antigravity-preview-09-2026`, `deep-research-preview-04-2026`) require `environment="remote"`

## Model Pricing & Capability Notes

| Model | Context / budget | Price (in / out per 1M) | Notes |
| :--- | :--- | :--- | :--- |
| `gemini-4-hydrogen` | Unified 1M input+output budget | $1.50 / $7.50 | Agentic/coding frontier tier. `thinking_level` accepts **`LOW`\|`MEDIUM`\|`HIGH`\|`XHIGH` only** — `MINIMAL` and `thinking_budget` return 400s. Sampling parameters (temperature/top_p/top_k) are silently ignored. |
| `gemini-3.8-flash` | 1M tokens | $0.75 / $3.75 (introductory through 2026-12-31) | Fast, balanced performance for agentic and multimodal tasks. |
| `gemini-3.5-flash-lite` | 1M tokens | — | Fastest, lowest-cost 3.5 model for high-throughput execution; the slot this repo actually runs. |

`gemini-4-hydrogen` is available but not adopted: it costs 5x the flash-lite input price and changes thinking/sampling semantics, so the Gemini slot stays on the cost-efficient tier by choice (see [[concepts/model-registry]]).

## Related

- [[concepts/thinking-agents]] — how thinking parameters are used in the trading pipeline
- [[concepts/agents]] — provider-specific agent implementations
- [[concepts/model-registry]] — the canonical model slot registry and currency audit procedure
- [[concepts/mcp-setup]] — other development tooling
