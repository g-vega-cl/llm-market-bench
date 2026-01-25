## AI Agent Rules & Workflow

### Additional Rule Categories

1. **Google Best Practices** - `.cursor/rules/google-best-practices/`
   - TypeScript/JavaScript code standards
   - Naming conventions
   - Documentation requirements
   - Type system usage

2. **Code Review Guidelines** - `.cursor/rules/reviews/`
   - Review checklist and standards

### Tool Selection Priority

**Documentation/URL Content:**
- ✅ Use `web-docs-extractor` agent (when user provides URL to read/extract)
  - The agent automatically uses the `web-fetch` skill with smart-fetch.js for optimal extraction
  - Supports authentication, auto-fallback (HTTP → Browser → Screenshot), and all content types
- ❌ Don't use WebFetch tool directly
- ❌ Don't invoke `web-fetch` skill directly (let the agent handle it)
- ❌ Don't use manual browser automation

**Codebase Exploration:**
- ✅ Use `Explore` agent (for open-ended exploration like "how does X work?")
- ❌ Don't use Grep/Glob directly for exploratory questions

---

## Collaboration Protocol

**Mode: Clarify → Plan → Implement → Verify**

### 0. Clarification (Always First)

For every request—no exceptions:
- Ask **numbered clarifying questions** to remove ambiguity
- Request **examples** if output format is unclear
- Confirm scope, **constraints**, **non-goals**, and "done" definition
- Proceed only **after** user responds

### 1. Planning (Adjacent Possible)

**Principle:** Small steps, not leaps. Each step must be verifiable.

- Extract requirements, constraints, and unknowns
- Define success criteria as **oracles** (tests, benchmarks, checks that decide success)
- Break work into **small, ordered subtasks**—each independently verifiable
- Identify **repo anchors**: existing files, patterns, and prior art to reuse
- Outline 2-3 approaches with trade-offs (select one)
- **PAUSE** and wait for confirmation before implementation

### 2. Implementation (Strict Scope)

- Execute **ONLY** what is explicitly requested
- **Reuse existing patterns**—cite prior art; don't invent new abstractions without justification
- Keep diffs **small and reviewable**
- Touch only specified elements; preserve existing code outside scope
- Remove imports/variables only when directly affected
- Address linter errors only in modified lines

### 3. Verification Loop (Error as Steering)

After each change:
1. Run tests/checks (the oracle)
2. If failures: fix and re-run (don't batch fixes)
3. Repeat until green
4. Status: **PASS**, **NEEDS_IMPROVEMENT**, or **FAIL**

If not PASS, identify **root cause** (not symptoms), fix, and re-verify.

### 4. Completion Checklist

- [ ] Clarifications resolved
- [ ] Plan confirmed by user
- [ ] Existing patterns reused (or new abstraction justified)
- [ ] All oracles pass (tests, lints, benchmarks)
- [ ] Diff is minimal and focused

---

## Context Packet (For Non-Trivial Tasks)

When starting complex work (reliability, perf, migrations, refactors), create or request:

| Field | Description |
|-------|-------------|
| **Goal** | One sentence: the outcome, not the mechanism |
| **Non-goals** | Explicitly out of scope (kills "helpful creativity") |
| **Constraints** | Hard requirements: budgets, safety, compatibility, forbidden actions |
| **Authority order** | When sources conflict: `tests/CI > code > docs > lore` |
| **Repo anchors** | 3-10 files defining truth: entrypoints, types, helpers, config |
| **Prior art** | Patterns to copy, abstractions to reuse |
| **Oracle** | Definition of done: tests to pass, edge cases, benchmarks |
| **Risk/Rollback** | How it could fail, what to watch, how to undo |

**Why:** Turns implicit senior intuition into explicit constraints. Agents stop guessing, reviews focus on invariants instead of vibes

