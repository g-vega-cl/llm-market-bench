#!/usr/bin/env bash
# Persistent tmux PTY wrapper and supervisor for Pi + @llblab/pi-telegram.
# Keeps a live Pi TUI connected to Telegram in background tmux session 'pi-telegram'
# and exits non-zero under 'supervise' if tmux or Pi dies so systemd Restart=always recovers it.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION_NAME="${PI_TMUX_SESSION:-pi-telegram}"
PI_BIN="${PI_BIN:-$HOME/.local/bin/pi}"
PI_PROFILE="${PI_TELEGRAM_PROFILE:-default}"

wait_for_pi_prompt() {
  local elapsed=0
  while [ "$elapsed" -lt 25 ]; do
    if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
      return 1
    fi
    if tmux capture-pane -p -t "$SESSION_NAME" 2>/dev/null | grep -qE "[›>]|pi|model"; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  return 0
}

start_session() {
  if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    tmux new-session -d -s "$SESSION_NAME" -c "$REPO_ROOT" "$PI_BIN"
    wait_for_pi_prompt
    tmux send-keys -t "$SESSION_NAME" "/telegram-connect $PI_PROFILE" Enter
    echo "[pi-telegram] Started tmux session '$SESSION_NAME' and sent '/telegram-connect $PI_PROFILE'."
  fi
}

case "${1:-start}" in
  start)
    start_session
    ;;
  supervise)
    start_session
    while tmux has-session -t "$SESSION_NAME" 2>/dev/null; do
      pane_dead="$(tmux list-panes -t "$SESSION_NAME" -F '#{pane_dead}' 2>/dev/null | head -n 1 || echo 1)"
      if [ "$pane_dead" = "1" ]; then
        tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
        exit 1
      fi
      sleep 5
    done
    exit 1
    ;;
  stop)
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
      tmux send-keys -t "$SESSION_NAME" "/telegram-disconnect" Enter || true
      sleep 1
      tmux kill-session -t "$SESSION_NAME" || true
    fi
    ;;
  status)
    tmux has-session -t "$SESSION_NAME"
    ;;
  *)
    echo "Usage: $0 {start|supervise|stop|status}" >&2
    exit 2
    ;;
esac
