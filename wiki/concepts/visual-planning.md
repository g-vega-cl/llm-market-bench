---
tags: [agent, workflow, documentation, planning]
category: concept
---

# Visual Terminal-Friendly Planning

This page defines the framework for producing highly visual, terminal-native plans. Rather than relying on external web surfaces or heavy MDX packages, this framework standardizes the use of standard Markdown combined with box-drawing characters, ASCII diagrams, and structured tables to make plans clear, scannable, and developer-friendly directly inside the terminal.

---

## Visual Components

Use these pre-formatted Unicode components to build visual plans:

### 1. Progress Tracker & State Board
Use visual progress bars to indicate completion status of planning, execution, and verification phases.
```
Status: [▓▓▓▓▓░░░░░] 50% | Phase: Implementation
```

### 2. File Change Tree
Always visualize the affected files using a structured Unicode file tree instead of bullet points or prose.
```
📁 apps/web/src/
├── 📁 features/
│   └── 📁 today/
│       ├── 📄 AgentInsights.tsx (Modify: update table layout)
│       └── 📄 MarketFeelingCard.tsx (New: add concerns list)
└── 📁 shared/
    └── 📄 Button.tsx (Modify: add type-safe variants)
```

### 3. Visual Sequence & Data Flow Diagrams
Map interaction or data lifecycles using ASCII/Unicode flowchart arrows. Keep lines aligned and use clean nodes.
```
[User Action] ──(click)──▶ [Route Loader] ──(query)──▶ [Supabase DB]
                                 │
                              (render)
                                 ▼
                         [Suspense Fallback]
```

### 4. Textual UI Mockups
For any UI/UX changes, render a clean, stylized ASCII/Unicode representation of the interface. This aligns user expectations immediately without requiring a full web preview.
```
┌────────────────────────────────────────────────────────┐
│ Today's Insights                      [Confidence: 85%]│
├────────────────────────────────────────────────────────┤
│ ● Claude 3.5 Sonnet: "Bullish on Tech..."              │
│ ● GPT-4o:            "Neutral. Watch macro rates..."   │
├────────────────────────────────────────────────────────┤
│ Primary Concern: [Inflation Trends                     ]│
└────────────────────────────────────────────────────────┘
```

### 5. TDD Test Case Flow
Visualize the test inputs, expected transitions, and assertions.
```
[Raw Response with <think>] ──(regex_strip)──▶ [Clean JSON String] ──(validate)──▶ [Assert Success]
```

---

## Mandatory Plan Sections

A visual plan must structure information into the following distinct sections:

| Section | Visual Element Used | Purpose |
| :--- | :--- | :--- |
| **1. Progress Board** | Progress bar + status badge | High-level status & active phase |
| **2. File Change Tree** | Unicode file directory tree | Explicit file paths, lines, and actions |
| **3. Logic / Data Flow** | ASCII/Unicode flowchart | Technical execution flow or sequence |
| **4. UI/UX Mockup** | Unicode box interface frame | Screen layout / state changes (if applicable) |
| **5. TDD Validation** | Input-Output flowchart | Reproduction and regression test structure |
| **6. Open Questions Board** | Markdown table | Unresolved design decisions / default actions |

---

## Reusable Templates

### Example Architecture & Backend Change Plan
```
### 📋 Visual Implementation Plan

Status: [░░░░░░░░░░] 0% | Phase: Drafting

#### 📁 File Change Tree
📁 apps/engine/
├── 📁 core/
│   └── 📄 analysis.py (Modify: add MiniMax extractor regex)
└── 📁 tests/
    └── 📄 test_minimax.py (New: TDD empty thoughts test)

#### ⚙️ Data Flow
[MiniMax API] ──(response)──▶ [analysis.py:_extract] ──(strip thoughts)──▶ [JSON Parser]

#### 🧪 TDD Verification Flow
Input:  " thinking... response {'action': 'buy'}"
Process: `_analyze_with_minimax` regex stripping
Assert: `parsed_response['action'] == 'buy'`

#### ❓ Open Questions Board
| Question | Options Considered | Recommended Default | Status |
| :--- | :--- | :--- | :--- |
| Should we log stripped thoughts? | A) Discard entirely <br> B) Log via logger.debug | B) Log via logger.debug | Resolved |
```

---

## Related
* [[concepts/agent-workflow]]
* [[entities/wiki-linter]]
