---
tags: [agent, workflow, documentation, planning]
category: concept
---

# Visual Terminal-Friendly Planning

This page defines the framework for producing highly visual, terminal-native plans. Rather than relying on external web surfaces or heavy MDX packages, this framework standardizes the use of standard Markdown combined with box-drawing characters, ASCII diagrams, and structured tables to make plans clear, scannable, and developer-friendly directly inside the terminal.

---

## Terminal Rendering Rules

- **Tag all diagram fences with `text`**: Always tag diagram code blocks with ```` ```text ````. Bare triple backticks cause terminal syntax highlighters to guess programming languages, treating box characters and arrows (`▼`) as syntax errors styled with red backgrounds.
- **Avoid LaTeX in tables**: In Markdown tables and status boards, use plain text or inline code spans (for example, `IV - RV (20d)` or `IV - RV_20d`). Terminal math parsers format LaTeX fractions and subscripts across multiple vertical lines, stretching table row heights and breaking column alignment. Reserve LaTeX for standalone display blocks or Artifacts.

---

## Visual Components

Use these pre-formatted Unicode components to build visual plans:

### 1. Status Board
Use a status board to indicate the active phase of the plan.
```text
Phase: Implementation (Awaiting "Go ahead")
```

### 2. Visual Sequence & Data Flow Diagrams
Map interaction or data lifecycles using ASCII/Unicode flowchart arrows. Keep lines aligned and use clean nodes. Tag with `text`.
```text
[User Action] ──(click)──▶ [Route Loader] ──(query)──▶ [Supabase DB]
                                 │
                              (render)
                                 ▼
                         [Suspense Fallback]
```

### 3. Textual UI Mockups
For any UI/UX changes, render a clean, stylized ASCII/Unicode representation of the interface. This aligns user expectations immediately without requiring a full web preview. Tag with `text`.
```text
┌────────────────────────────────────────────────────────┐
│ Today's Insights                      [Confidence: 85%]│
├────────────────────────────────────────────────────────┤
│ ● Claude 3.5 Sonnet: "Bullish on Tech..."              │
│ ● GPT-4o:            "Neutral. Watch macro rates..."   │
├────────────────────────────────────────────────────────┤
│ Primary Concern: [Inflation Trends                     ]│
└────────────────────────────────────────────────────────┘
```

### 4. TDD Test Case Flow
Visualize the test inputs, expected transitions, and assertions. Tag with `text`.
```text
[Raw Response with <think>] ──(regex_strip)──▶ [Clean JSON String] ──(validate)──▶ [Assert Success]
```

---

## Mandatory Plan Sections

A visual plan must structure information into the following distinct sections:

| Section | Visual Element Used | Purpose |
| :--- | :--- | :--- |
| **1. Status Board** | Active phase indicator | High-level active phase |
| **2. Logic / Data Flow** | ASCII/Unicode flowchart (`text` fence) | Technical execution flow or sequence |
| **3. UI/UX Mockup** | Unicode box interface frame (`text` fence) | Screen layout / state changes (if applicable) |
| **4. TDD Validation** | Input-Output flowchart (`text` fence) | Reproduction and regression test structure |
| **5. Open Questions Board** | Markdown table (plain text, no LaTeX) | Unresolved design decisions / default actions |

---

## Reusable Templates

### Example Architecture & Backend Change Plan
````markdown
### 📋 Visual Implementation Plan

Phase: Drafting

#### ⚙️ Data Flow
```text
[MiniMax API] ──(response)──▶ [analysis.py:_extract] ──(strip thoughts)──▶ [JSON Parser]
```

#### 🧪 TDD Verification Flow
Input:  " thinking... response {'action': 'buy'}"
Process: `_analyze_with_minimax` regex stripping
Assert: `parsed_response['action'] == 'buy'`

#### ❓ Open Questions Board
| Question | Options Considered | Recommended Default | Status |
| :--- | :--- | :--- | :--- |
| Should we log stripped thoughts? | A) Discard entirely <br> B) Log via logger.debug | B) Log via logger.debug | Resolved |
````

---

## Related
* [[concepts/agent-workflow]]
* [[entities/wiki-linter]]
