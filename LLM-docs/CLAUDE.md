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
- ✅ Use `web-fetch` skill (when user provides URL to read/extract)
  - Supports authentication, auto-fallback (HTTP → Browser → Screenshot), and all content types

---
## Trunk-Based Development Workflow

**Single Main Branch Strategy** - All work happens on `main` with short-lived feature branches

### Branch Strategy

* **Main Branch (`main`)**: Single source of truth, always deployable
* **Feature Branches**: Short-lived (< 2 days), merged via pull request
* **Branch Naming**: `feature/short-description` or `fix/issue-description`
* **No Long-Lived Branches**: Avoid development, staging, or release branches

### Commit & Integration Rules

1. **Frequent Integration**: Merge to `main` at least once per day
2. **Small Commits**: Atomic, focused changes that can be independently reviewed
3. **Feature Flags**: Use flags for incomplete features to keep `main` releasable
4. **CI/CD Required**: Automated tests must pass before merge
5. **Fast Reviews**: Pull requests reviewed and merged within hours, not days

### Pull Request Guidelines

* **Small PRs**: Target < 400 lines of code for faster review
* **Self-Contained**: Each PR should be independently deployable
* **Tested**: Include tests; all CI checks must pass
* **Clear Description**: Explain what, why, and how
* **Quick Turnaround**: Review and merge same day when possible


---

## Collaboration Protocol (from dev-loop.mdc)

**Mode: Clarify → Decompose → Evaluate**

### 0. Mandatory Clarification (Always Ask First)

For **every** user request—no exceptions:
* Ask **numbered clarifying questions** to remove ambiguity
* Request **examples** if the expected output format is not explicitly given
* Confirm scope, constraints, and "done" definition
* Only proceed to decomposition **after** the user responds

### 1. Mandatory Decomposition (Orchestrator)

After clarifications:

#### Analysis & Goal
* Extract requirements, constraints, and unknowns
* Define exact success criteria and expected output format

#### Plan & Approaches
* Break into detailed, ordered subtasks
* Outline 2-3 approaches with trade-offs (Select one)
* Define measurable Evaluation Criteria (Correctness, Performance, Edge Cases)

#### PAUSE and wait for confirmation before implementation.

### 2. Implementation Discipline (Strict Scope)

* **Execute ONLY what is explicitly requested.**
* **Code Integrity:**
    * Touch only specified elements; preserve existing code outside scope.
    * Remove imports/variables only when directly affected.
    * Address linter errors only in modified lines.
    * Never fix/refactor unrelated code without asking.

### 3. Mandatory Evaluator-Optimizer Loop

After implementation:
1. **Evaluate:** Compare result directly against criteria.
2. **Status:** Assign **PASS**, **NEEDS_IMPROVEMENT**, or **FAIL**.
3. **Loop:** If not PASS, identify root cause (not symptoms), fix, and re-evaluate until PASS.

### 4. Completion Checklist

Before declaring "Done":
- [ ] Clarifications resolved
- [ ] Plan confirmed by user
- [ ] Code follows scope discipline (no unrelated refactoring)
- [ ] Passed all evaluation criteria

### 5. Operating Mode Summary

**Clarify → Decompose → Confirm → Implement → Evaluate → Iterate until PASS**

No direct execution. No skipping steps.

### Code Style & Standards
- **Minimal Changes**: Only modify code that's explicitly requested
- **Clean Imports and Variables**: Remove unused imports and variables
- **Focused Fixes**: Avoid fixing unrelated linter errors

