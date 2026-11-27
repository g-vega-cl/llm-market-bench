#!/usr/bin/env bash
# Idempotent Fedora user-space installer for:
# 1. Persistent supervised Pi + @llblab/pi-telegram bridge (systemd --user, Restart=always)
# 2. Boot + 30-minute worktree/lockfile janitor timer
# 3. Background QMD update/embed timer
# Note: Antigravity loads .agents/hooks.json and Pi loads .pi/extensions/bench-gate.ts per checkout/worktree,
# avoiding duplicate global extension registration.
set -euo pipefail

SCRIPT_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAIN_WORKTREE="$(git -C "$SCRIPT_REPO" worktree list --porcelain 2>/dev/null | awk '/^worktree / {print $2; exit}')"
if [ -n "${TARGET_REPO_ROOT:-}" ]; then
  REPO_ROOT="$TARGET_REPO_ROOT"
elif [ -n "$MAIN_WORKTREE" ] && [ -f "$MAIN_WORKTREE/scripts/worktree-janitor.sh" ]; then
  REPO_ROOT="$MAIN_WORKTREE"
else
  REPO_ROOT="$SCRIPT_REPO"
fi
UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"

# Remove any duplicate global bench-gate.ts link so Pi does not load .pi/extensions/bench-gate.ts twice
rm -f "$HOME/.pi/agent/extensions/bench-gate.ts"

# 1. Install janitor service + 30-minute timer
cat > "$UNIT_DIR/llm-bench-janitor.service" <<EOF
[Unit]
Description=LLM Market Bench stale git lockfile and worktree janitor

[Service]
Type=oneshot
WorkingDirectory=$REPO_ROOT
ExecStart=$REPO_ROOT/scripts/worktree-janitor.sh
EOF

cat > "$UNIT_DIR/llm-bench-janitor.timer" <<EOF
[Unit]
Description=Run LLM Market Bench worktree janitor on boot and every 30 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=30min
Persistent=true

[Install]
WantedBy=timers.target
EOF

# 2. Install background QMD update/embed timer
cat > "$UNIT_DIR/llm-bench-qmd-garden.service" <<EOF
[Unit]
Description=LLM Market Bench background QMD index and embedding refresh

[Service]
Type=oneshot
WorkingDirectory=$REPO_ROOT
ExecStart=$REPO_ROOT/scripts/qmd-garden.sh
EOF

cat > "$UNIT_DIR/llm-bench-qmd-garden.timer" <<EOF
[Unit]
Description=Refresh QMD search index and embeddings every 2 hours

[Timer]
OnBootSec=5min
OnUnitActiveSec=2h
Persistent=true

[Install]
WantedBy=timers.target
EOF

# 3. Persistent supervised Pi + @llblab/pi-telegram tmux bridge (Restart=always; attach via `tmux attach -t pi-telegram`)
if [ -x "$HOME/.local/bin/pi" ] && command -v tmux >/dev/null 2>&1; then
  cat > "$UNIT_DIR/pi-telegram-bridge.service" <<EOF
[Unit]
Description=Persistent Pi + @llblab/pi-telegram Bridge (tmux session pi-telegram)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$REPO_ROOT
Environment=PATH=$HOME/.local/bin:$HOME/.npm-global/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$REPO_ROOT/scripts/pi-telegram-daemon.sh supervise
ExecStop=$REPO_ROOT/scripts/pi-telegram-daemon.sh stop
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF
  echo "[fedora-setup] Wrote $UNIT_DIR/pi-telegram-bridge.service (Restart=always; attach via: tmux attach -t pi-telegram)"
else
  echo "[fedora-setup] Note: Install pi (~/.local/bin/pi) and tmux to enable pi-telegram-bridge.service"
fi

if command -v systemctl >/dev/null 2>&1; then
  systemctl --user daemon-reload || true
  systemctl --user enable --now llm-bench-janitor.timer llm-bench-qmd-garden.timer || true
  if [ -f "$UNIT_DIR/pi-telegram-bridge.service" ]; then
    systemctl --user enable --now pi-telegram-bridge.service || true
  fi
fi

echo "[fedora-setup] User-space timers and supervised Pi Telegram unit installed."
