#!/usr/bin/env bash
set -euo pipefail

# deploy_secondary.sh
# Synchronizes edge configurations, Docker compose stacks, and secrets from Workstation to MiniPC.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

TARGET_HOST="${1:-cv-minipc@minipc}"
REMOTE_DIR="~/llm-market-bench"

echo "=== [1/4] Testing SSH reachability to ${TARGET_HOST} ==="
if ! ssh -o ConnectTimeout=5 "${TARGET_HOST}" "echo 'SSH connection successful.'" >/dev/null 2>&1; then
    echo "ERROR: Unable to connect via SSH to ${TARGET_HOST}."
    echo "Please verify that Tailscale is running and key authentication is configured."
    exit 1
fi
echo "SSH connection verified."

echo "=== [2/4] Ensuring remote workspace directories exist ==="
ssh "${TARGET_HOST}" "mkdir -p ${REMOTE_DIR}/docker/archive ${REMOTE_DIR}/apps/free_llm_proxy"

echo "=== [3/4] Syncing configurations and Docker compose files via rsync ==="
rsync -avz --delete \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'data/' \
    "${SCRIPT_DIR}/docker-compose.secondary.yml" \
    "${SCRIPT_DIR}/nginx.secondary.conf" \
    "${SCRIPT_DIR}/bootstrap_replica.sh" \
    "${SCRIPT_DIR}/promote_to_primary.sh" \
    "${TARGET_HOST}:${REMOTE_DIR}/docker/archive/"

rsync -avz --delete \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'data/' \
    "${REPO_ROOT}/apps/free_llm_proxy/" \
    "${TARGET_HOST}:${REMOTE_DIR}/apps/free_llm_proxy/"

# Sync .env if present
if [[ -f "${SCRIPT_DIR}/.env" ]]; then
    echo "Syncing docker/archive/.env..."
    rsync -avz "${SCRIPT_DIR}/.env" "${TARGET_HOST}:${REMOTE_DIR}/docker/archive/.env"
fi

if [[ -f "${REPO_ROOT}/apps/free_llm_proxy/.env" ]]; then
    echo "Syncing apps/free_llm_proxy/.env..."
    rsync -avz "${REPO_ROOT}/apps/free_llm_proxy/.env" "${TARGET_HOST}:${REMOTE_DIR}/apps/free_llm_proxy/.env"
fi

echo "=== [4/4] Setting execution permissions on remote helper scripts ==="
ssh "${TARGET_HOST}" "chmod +x ${REMOTE_DIR}/docker/archive/*.sh"

echo "=== Deployment sync to ${TARGET_HOST} complete! ==="
echo "To initialize replication on MiniPC, SSH into ${TARGET_HOST} and run:"
echo "  cd ${REMOTE_DIR}/docker/archive && ./bootstrap_replica.sh"
