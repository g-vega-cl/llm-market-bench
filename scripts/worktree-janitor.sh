#!/usr/bin/env bash
# Safe boot + 30-minute worktree and stale git lockfile janitor.
# Never deletes dirty worktrees; removes index.lock only when >60m old AND zero git/hook processes run in repo.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

has_active_repo_git_or_hook_process() {
  local pid cwd cmdline
  for proc_dir in /proc/[0-9]*; do
    pid="${proc_dir#/proc/}"
    [ "$pid" = "$$" ] && continue
    cwd="$(readlink -f "$proc_dir/cwd" 2>/dev/null || true)"
    case "$cwd" in
      "$REPO_ROOT"|"$REPO_ROOT"/*)
        cmdline="$(tr '\0' ' ' < "$proc_dir/cmdline" 2>/dev/null || true)"
        case "$cmdline" in
          *git*|*husky*|*pre-commit*|*pytest*|*vitest*|*tsc*|*biome*)
            return 0
            ;;
        esac
        ;;
    esac
  done
  return 1
}

clean_stale_lock() {
  local lock_file="$1"
  [ -f "$lock_file" ] || return 0

  if command -v lsof >/dev/null 2>&1 && lsof -- "$lock_file" >/dev/null 2>&1; then
    echo "[janitor] Active descriptor holds $lock_file; keeping lock."
    return 0
  fi

  if has_active_repo_git_or_hook_process; then
    echo "[janitor] Active git/hook/test process running in $REPO_ROOT; keeping $lock_file."
    return 0
  fi

  # Only clear orphaned locks older than 60 minutes so slow pre-commit runs can never race.
  if [ -n "$(find "$lock_file" -mmin +60 2>/dev/null)" ]; then
    rm -f "$lock_file"
    echo "[janitor] Removed orphaned lockfile (>60m): $lock_file"
  fi
}

clean_stale_lock "$REPO_ROOT/.git/index.lock"
if [ -d "$REPO_ROOT/.git/worktrees" ]; then
  for wt_lock in "$REPO_ROOT"/.git/worktrees/*/index.lock; do
    [ -e "$wt_lock" ] && clean_stale_lock "$wt_lock"
  done
fi

git worktree prune
