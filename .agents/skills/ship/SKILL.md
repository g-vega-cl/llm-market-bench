---
name: ship
description: Land a verified worktree branch via merge or PR, deploy affected MiniPC edge services with live PostgREST parity probes, and prune the worktree. Invoke explicitly with /ship.
disable-model-invocation: true
---

# Ship (Verified Release & Edge Deploy Gate)

This skill is manual-only (`disable-model-invocation: true`). Run it only when the user explicitly invokes `/ship` to land a verified worktree branch.

## 1. Pre-ship verification gate

1. Confirm `./.agents/skills/verify/scripts/verify.sh` (or targeted engine/web suites plus strict `wiki_lint.py`) and the Tier 7 cold-context reviewer subagent passed with zero unresolved blocking defects.
2. Run `git status --short` inside the worktree and confirm zero uncommitted edits or stray scratch artifacts.
3. Inspect `git log main..HEAD --oneline` and `git diff --stat main...HEAD` to confirm commit messages pass `apps/engine/commit_msg_lint.py` and touch only intended files.

## 2. Land onto `main` or open a PR

- **Standard solo fast-forward (default unless user asked for a PR)**:
  ```bash
  git fetch origin main
  git rebase origin/main
  # From main checkout (preserving any unrelated local edits via stash if needed, or pushing HEAD:main):
  git push origin HEAD:main
  ```
  Note: Pushing to `origin/main` triggers `docker/archive/watch_web_deploy.sh` when web/package paths changed.
- **Pull request path (when requested or for Red-Line review)**:
  ```bash
  git push -u origin "$(git branch --show-current)"
  gh pr create --fill
  ```

## 3. MiniPC edge & PostgREST replica parity (`PGRST205` guard)

Check `git diff --name-only origin/main~1 origin/main` (or the branch diff) for `supabase/migrations/`, `apps/free_llm_proxy/`, `apps/engine/trading/`, `apps/engine/recipes/`, or `docker/archive/`:

1. Verify non-interactive Tailscale SSH first:
   ```bash
   ssh -o BatchMode=yes cv-minipc@minipc true
   ```
   If Tailscale check-mode requests browser authentication, pause and ask the user to run `ssh cv-minipc@minipc` once interactively.
2. Deploy and restart `archive-postgrest` / edge containers:
   ```bash
   ./docker/archive/deploy_secondary.sh cv-minipc@minipc
   ```
3. If `supabase/migrations/*.sql` changed, probe `https://benchify-archive-db.clvg.uk/rest/v1/<table_name>?limit=1` and confirm HTTP `200 OK` with zero `PGRST205` schema-cache errors.

## 4. Worktree cleanup

Once commits are safely on `origin/main` (or PR is merged), remove the finished worktree and prune metadata:

```bash
git worktree remove .worktrees/<slug>
git worktree prune
git branch -d feat/<slug>
```
