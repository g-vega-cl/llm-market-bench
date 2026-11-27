#!/usr/bin/env bash
# Wrap long worktree builds/tests in systemd-inhibit on Fedora so sleep/shutdown waits for completion.
set -euo pipefail

if [ "$#" -eq 0 ]; then
  echo "Usage: $0 <command> [args...]" >&2
  exit 2
fi

if command -v systemd-inhibit >/dev/null 2>&1 && systemd-inhibit --list >/dev/null 2>&1; then
  exec systemd-inhibit \
    --what=shutdown:sleep:idle \
    --who="llm-market-bench-agent" \
    --why="Active worktree build or verification run" \
    "$@"
fi

exec "$@"
