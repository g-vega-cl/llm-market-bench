---
name: implement
description: Execute an approved plan or SPEC.md end-to-end inside an isolated git worktree using strict Red-Green-Refactor TDD and Ponytail minimal-code discipline.
---

# Implement (Worktree TDD Execution)

Use this skill after receiving explicit user approval on an inline chat plan or `specs/<slug>/SPEC.md` contract. Once approved, run uninterrupted through verification without pausing on routine micro-steps.

## 1. Pre-flight contract check

1. Confirm explicit plan sign-off exists in the session or ticket. If missing, present a compact visual plan (`[[concepts/visual-planning]]`) and wait for approval first.
2. For multi-file features, database migrations, API changes, or trading/risk logic, verify `specs/<slug>/SPEC.md` exists (keep it to 1 page: Objective, Mechanical Acceptance Criteria in `WHEN ... THE SYSTEM SHALL ...` form, Permitted Paths, Forbidden Red-Line Paths, and Exact Verification Commands). Localized bug fixes need only the approved chat plan and failing test case.

## 2. Isolated git worktree setup

Never code directly on a shared dirty checkout. Create or enter a dedicated worktree under `.worktrees/<slug>`:

```bash
git worktree add -b feat/<slug> .worktrees/<slug> HEAD
ln -sfn "$(pwd)/apps/engine/.venv" ".worktrees/<slug>/apps/engine/.venv"
pnpm --dir ".worktrees/<slug>" install --frozen-lockfile --prefer-offline
```

If running a long uninterrupted suite on Fedora, wrap heavy commands with `./scripts/inhibit-run.sh <cmd>` so power/sleep actions wait for completion.

## 3. Strict Red-Green-Refactor TDD loop

For each vertical behavior in the plan:

1. **Red**: Write a minimal, hermetic reproduction test (`< 100ms`, zero network sockets, zero artificial sleep) in the colocated test file (`foo.py` -> `test_foo.py`, `Foo.tsx` -> `Foo.test.tsx`). Run it and confirm it fails for the expected reason.
2. **Green**: Climb the Ponytail Minimal-Code Ladder (`AGENTS.md`):
   - Delete dead code or collapse boolean flag sprawl first (`[[concepts/state-machines]]`).
   - Prefer config, SQL/PostgREST, or stdlib/existing repo helpers over new code.
   - Keep modules under the 400 LOC soft ceiling (800 LOC hard ceiling).
   Run the targeted test and confirm it turns green.
3. **Refactor & Commit**: Clean up duplication, verify lint/types on touched files, stage strictly task-specific paths (`git add path/to/file`), and create an atomic Conventional Commit.

## 4. Red-line boundaries & stall escalation

Stop early and alert the user on CLI or Telegram **only** if:
- Completing the task requires an unapproved Red-Line edit (`supabase/migrations/*.sql`, `apps/engine/autoresearch/evaluator.py`, `apps/engine/local_autoresearch/single_prompt_ratchet.py`, `.github/workflows/*`, or new package dependencies).
- The same check stalls for **2 consecutive fix rounds**: revert the failed patch, record a 3-line negative-knowledge note naming what failed, and ask the user or escalate model tier.

## 5. Finish with `/verify` and hold for `/ship`

Run `/verify` (`.agents/skills/verify/SKILL.md`), including the cold-context reviewer subagent configured in `.agents/reviewer-profiles.json`. Once clean, report the verified worktree branch and wait for explicit `/ship` or PR merge before touching `main`.
