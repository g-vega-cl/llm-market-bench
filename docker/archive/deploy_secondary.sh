#!/usr/bin/env bash
set -euo pipefail

# deploy_secondary.sh
# Synchronizes edge configurations, Docker compose stacks, and secrets from Workstation to MiniPC.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

TARGET_HOST="${1:-cv-minipc@minipc}"
REMOTE_DIR="~/llm-market-bench"

echo "=== [1/6] Testing SSH reachability to ${TARGET_HOST} ==="
if ! ssh -o ConnectTimeout=5 "${TARGET_HOST}" "echo 'SSH connection successful.'" >/dev/null 2>&1; then
    echo "ERROR: Unable to connect via SSH to ${TARGET_HOST}."
    echo "Please verify that Tailscale is running and key authentication is configured."
    exit 1
fi
echo "SSH connection verified."

echo "=== [2/6] Ensuring remote workspace directories exist ==="
ssh "${TARGET_HOST}" "mkdir -p ${REMOTE_DIR}/docker/archive ${REMOTE_DIR}/apps/free_llm_proxy ${REMOTE_DIR}/apps/engine ${REMOTE_DIR}/packages/config"

echo "=== [3/6] Syncing configurations, trader engine, and Docker files via rsync ==="
rsync -avz --delete \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'data/' \
    "${SCRIPT_DIR}/docker-compose.secondary.yml" \
    "${SCRIPT_DIR}/ensure_proxy_config.sh" \
    "${SCRIPT_DIR}/bootstrap_replica.sh" \
    "${SCRIPT_DIR}/promote_to_primary.sh" \
    "${SCRIPT_DIR}/Dockerfile.trader" \
    "${SCRIPT_DIR}/nginx.web.secondary.conf" \
    "${TARGET_HOST}:${REMOTE_DIR}/docker/archive/"

# Routing config is failover state, not code: a promotion rewrites nginx.secondary.conf in place and
# leaves .promoted behind, so a routine deploy must not rsync standby routing back over it. Distinguish
# "sentinel absent" (rc 1) from "cannot tell" (ssh 255, DNS/Tailscale blip) and abort on the latter:
# failing open here would silently revert a live failover.
if ssh "${TARGET_HOST}" "test -f ${REMOTE_DIR}/docker/archive/.promoted"; then
    echo "WARNING: ${TARGET_HOST} is in promoted (local-write) failover state; keeping its nginx.secondary.conf."
    echo "         Clear with: ssh ${TARGET_HOST} 'rm -f ${REMOTE_DIR}/docker/archive/.promoted' once the workstation is primary again."
else
    sentinel_rc=$?
    if [[ "${sentinel_rc}" -ne 1 ]]; then
        echo "ERROR: cannot determine failover state on ${TARGET_HOST} (ssh/test exited ${sentinel_rc})." >&2
        echo "       Refusing to sync nginx.secondary.conf: a blind sync could revert a live failover." >&2
        exit 1
    fi
    rsync -avz "${SCRIPT_DIR}/nginx.secondary.conf" "${TARGET_HOST}:${REMOTE_DIR}/docker/archive/"
fi

rsync -avz --delete \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'data/' \
    "${REPO_ROOT}/apps/free_llm_proxy/" \
    "${TARGET_HOST}:${REMOTE_DIR}/apps/free_llm_proxy/"

rsync -avz --delete \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.venv' \
    --exclude 'market' \
    --exclude '.pytest_cache' \
    --exclude 'tests' \
    "${REPO_ROOT}/apps/engine/" \
    "${TARGET_HOST}:${REMOTE_DIR}/apps/engine/"

rsync -avz --delete \
    "${REPO_ROOT}/packages/config/" \
    "${TARGET_HOST}:${REMOTE_DIR}/packages/config/"

# Sync .env if present
if [[ -f "${SCRIPT_DIR}/.env" ]]; then
    echo "Syncing docker/archive/.env..."
    rsync -avz "${SCRIPT_DIR}/.env" "${TARGET_HOST}:${REMOTE_DIR}/docker/archive/.env"
fi

if [[ -f "${REPO_ROOT}/apps/engine/.env" ]]; then
    echo "Syncing apps/engine/.env..."
    rsync -avz "${REPO_ROOT}/apps/engine/.env" "${TARGET_HOST}:${REMOTE_DIR}/apps/engine/.env"
fi

if [[ -f "${REPO_ROOT}/apps/free_llm_proxy/.env" ]]; then
    echo "Syncing apps/free_llm_proxy/.env..."
    rsync -avz "${REPO_ROOT}/apps/free_llm_proxy/.env" "${TARGET_HOST}:${REMOTE_DIR}/apps/free_llm_proxy/.env"
fi

echo "=== [4/6] Setting execution permissions on remote helper scripts ==="
ssh "${TARGET_HOST}" "chmod +x ${REMOTE_DIR}/docker/archive/*.sh"

echo "=== [5/6] Rebuilding, launching Docker containers, and reloading PostgREST schema cache on ${TARGET_HOST} ==="
ssh "${TARGET_HOST}" "cd ${REMOTE_DIR}/docker/archive && bash ensure_proxy_config.sh --validate-only docker-compose.secondary.yml archive-proxy market-bench-archive-proxy-replica nginx.secondary.conf && docker compose -f docker-compose.secondary.yml up -d --build && bash ensure_proxy_config.sh docker-compose.secondary.yml archive-proxy market-bench-archive-proxy-replica nginx.secondary.conf && bash ensure_proxy_config.sh docker-compose.secondary.yml web-proxy market-bench-web-proxy-secondary nginx.web.secondary.conf && docker compose -f docker-compose.secondary.yml restart archive-postgrest && docker compose -f docker-compose.secondary.yml ps"

echo "=== [6/6] Verifying local read replica endpoint health on ${TARGET_HOST} ==="
if ! ssh "${TARGET_HOST}" "curl -s -f -o /dev/null http://localhost:3001/rest/v1/"; then
    echo "ERROR: Local PostgREST read endpoint on ${TARGET_HOST} did not return 200 OK." >&2
    echo "       The replica is up but not serving reads; do not treat this deploy as complete. Inspect the archive-postgrest logs." >&2
    exit 1
fi
echo "PostgREST read endpoint on ${TARGET_HOST} is healthy and schema cache reloaded."


echo "=== Deployment to ${TARGET_HOST} complete and services started! ==="