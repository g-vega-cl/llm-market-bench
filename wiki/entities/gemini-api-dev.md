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
- Migration reference: `.agents/skills/gemini-api-dev/references/migration.md`
- Claude Code symlink: `.claude/skills/gemini-api-dev` → `.agents/skills/gemini-api-dev`

## Key Guidance

- Uses `google-genai` SDK >= 2.0.0 (Python) or `@google/genai` >= 2.0.0 (TypeScript)
- Interactions API (`client.interactions.create()`) replaces legacy `generateContent`
- Current models: `gemini-3.8-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-pro-preview`, `gemini-nano-banana-2.1`
- Deprecated models: `gemini-2.5-*`, `gemini-2.0-*`, `gemini-1.5-*` — never use; substitute `gemini-3.8-flash` instead
- Thinking configuration uses `thinking_level` (`minimal`, `low`, `medium`, `high`) not the deprecated `thinking_budget` parameter
- Managed agents (`antigravity-preview-09-2026`, `deep-research-preview-04-2026`) require `environment="remote"`

## Related

- [[concepts/thinking-agents]] — how thinking parameters are used in the trading pipeline
- [[concepts/agents]] — provider-specific agent implementations
- [[concepts/mcp-setup]] — other development tooling
