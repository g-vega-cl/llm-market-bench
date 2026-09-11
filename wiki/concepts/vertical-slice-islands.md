---
tags: [architecture, vertical-slice, islands, modularity, code-quality]
category: concept
---

# Vertical Slice Islands & Modular Architecture

Vertical Slice Islands are self-contained, modular code units designed to optimize both human maintainability and AI coding agent reliability. Instead of horizontal technical layering or massive monolithic files, code is structured into cohesive domains with strict boundaries, narrow interfaces, and colocated tests.

## Why File Architecture Affects AI Coding Agents

AI coding agents interact with codebases using tool interfaces such as `view_file`, `replace_file_content`, and grep search. File size and coupling directly determine agent success rates.

### The Monolith Failure Mode

Files exceeding 700 lines create specific failure points for LLMs:

1. **Tool viewport truncation**: Tools like `view_file` cap reads at 800 lines (or 46 KB). Files larger than this ceiling force agents to read partial slices, blinding them to class signatures, imports, or helper utilities defined earlier or later in the file.
2. **Patch search collisions**: Editing tools rely on unique string matching. In long files, repeated patterns (generic returns, logging calls, loop variables) trigger ambiguity errors or accidental modifications to the wrong line ranges.
3. **Hidden state coupling**: State variables declared at line 80 often have subtle side effects on logic at line 1200. Agents lack the context to maintain distant invariants.

This dynamic is confirmed by git forensics in `apps/engine/hotspots.py`:

| File | LOC | Churn | Bug Fix Ratio | Status |
| :--- | :---: | :---: | :---: | :---: |
| `apps/engine/core/llm/analysis.py` | 1,150 | 22 | 63.6% | CRITICAL |
| `apps/engine/execution/market_data.py` | 749 | 15 | 66.7% | CRITICAL |
| `apps/engine/main.py` | 949 | 27 | 40.7% | CRITICAL |
| `apps/engine/core/llm/tools.py` | 3,128 | 28 | 10.7% | High cognitive load |
| `apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx` | 1,471 | 15 | 20.0% | Bloated view |

Files exceeding 700 LOC in this repository exhibit bug fix ratios between 40% and 66%, meaning nearly half of all commits touching those files were fixes for regressions introduced during earlier edits.

### The Micro-File Trap

The opposite extreme, breaking every function or interface into a 20-line file, introduces distinct failure modes:

1. **Navigation tax**: Tracing an execution path through multiple layers (`Controller -> Service -> Validator -> Repository -> Mapper`) requires 5 to 10 sequential tool calls, inflating token consumption and causing the agent to lose conversational context.
2. **Coordinated patch failures**: When an abstraction leaks across 6 tiny files, an agent must execute 6 separate patch operations. An error on step 4 leaves the workspace in a dirty, broken state.
3. **Import and barrel churn**: High file counts lead to deep import graphs and circular dependency risks in both Python and TypeScript.

## The Island Standard

The optimal architecture balances high internal cohesion with low external coupling:

```text
apps/web/src/features/memories/
├── components/
│   ├── MemoryCard.tsx        # UI presentation (100-200 LOC)
│   └── MemoryCard.test.tsx   # Colocated unit tests
├── hooks/
│   └── useMemorySearch.ts    # Isolated fetching hook
└── types.ts                  # Local domain types
```

### Architectural Rules

1. **Target size: 100 to 300 LOC**: Every unit comfortably fits within a single tool viewport with ample margin for reasoning tokens.
2. **Soft ceiling: 400 LOC**: Any file reaching 400 lines must be reviewed for decomposition into sub-components or domain sub-modules.
3. **Hard ceiling: 800 LOC**: No file should exceed 800 lines under any circumstance to avoid tool truncation.
4. **Colocated tests**: Test files must sit directly alongside the code they verify (`foo.ts` and `foo.test.ts`, or `feature.py` and `test_feature.py`). In git forensics, colocated pairs exhibit tight 80% to 100% co-churn with zero collateral damage to unrelated files.
5. **Narrow, explicit boundaries**: An island accepts typed inputs, performs its work, and returns explicit outputs. Avoid reading or mutating ambient global state.

## Related

- [[concepts/code-hotspots]] — Churn forensics and regression analysis
- [[entities/agent-rules]] — Canonical operational rules in GEMINI.md
- [[entities/web-app]] — Web frontend application architecture
- [[sources/web-architecture-source]] — Feature slicing specification
- [[sources/web-testing-source]] — Test colocation conventions
