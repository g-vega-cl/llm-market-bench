#!/usr/bin/env bash
set -euo pipefail

# deploy_web.sh
# Builds and deploys the self-hosted TanStack Start web app (web-app + web-proxy)
# to both the primary workstation and the secondary MiniPC edge node.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

TARGET_HOST="${DEPLOY_WEB_HOST:-cv-minipc@192.168.88.7}"
REMOTE_DIR="~/llm-market-bench"
SKIP_TESTS=false
LOCAL_ONLY=false
REMOTE_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --skip-tests) SKIP_TESTS=true ;;
        --local-only) LOCAL_ONLY=true ;;
        --remote-only) REMOTE_ONLY=true ;;
        *)
            TARGET_HOST="$arg"
            ;;
    esac
done

DEFAULT_WEB_ENV="${HOME}/.config/benchify/web.env"
DEFAULT_ARCHIVE_ENV="${HOME}/.config/benchify/archive.env"

if [[ -z "${WEB_ENV_FILE:-}" ]]; then
    if [[ -f "${DEFAULT_WEB_ENV}" ]]; then
        WEB_ENV_FILE="${DEFAULT_WEB_ENV}"
    else
        WEB_ENV_FILE="${REPO_ROOT}/apps/web/.env"
    fi
fi

if [[ -z "${ARCHIVE_ENV_FILE:-}" ]]; then
    if [[ -f "${DEFAULT_ARCHIVE_ENV}" ]]; then
        ARCHIVE_ENV_FILE="${DEFAULT_ARCHIVE_ENV}"
    else
        ARCHIVE_ENV_FILE="${SCRIPT_DIR}/.env"
    fi
fi

export WEB_ENV_FILE

if [[ ! -f "${WEB_ENV_FILE}" ]]; then
    echo "ERROR: Missing ${WEB_ENV_FILE}. Create it from apps/web/.env.example or set WEB_ENV_FILE."
    exit 1
fi

# Export VITE_* build args and compose variables from apps/web/.env without printing secrets.
set -a
# shellcheck disable=SC1090
source "${WEB_ENV_FILE}"
if [[ -f "${ARCHIVE_ENV_FILE}" ]]; then
    # shellcheck disable=SC1090
    source "${ARCHIVE_ENV_FILE}"
fi
set +a

if [[ "${SKIP_TESTS}" == "false" ]]; then
    echo "=== [1/4] Running web lint, typecheck, and unit tests ==="
    (cd "${REPO_ROOT}" && pnpm biome check apps/web packages/ui-design-system packages/database && pnpm --filter web typecheck && pnpm --filter web test --maxWorkers=2)
else
    echo "=== [1/4] Skipping local checks (--skip-tests) ==="
fi

smoke_check() {
    local label="$1"
    local prefix="$2"
    local cmd='for i in 1 2 3 4 5 6; do
        if curl -sf http://localhost:3005/health >/dev/null; then
            HTML=$(curl -sf http://localhost:3005/ || true)
            CSS_PATH=$(printf "%s" "$HTML" | grep -oE "/assets/app-[A-Za-z0-9_-]+\.css" | head -n 1 || true)
            if printf "%s" "$HTML" | grep -q "Benchify" && [ -n "$CSS_PATH" ] && curl -sf "http://localhost:3005${CSS_PATH}" >/dev/null; then
                exit 0
            fi
        fi
        sleep 2
    done
    exit 1'
    if [[ -n "${prefix}" ]]; then
        if ! ssh "${prefix}" "${cmd}"; then
            echo "ERROR: Web smoke check failed on ${label} — the deploy aborts here under 'set -e'. Inspect web-app / web-proxy logs."
            return 1
        fi
    else
        if ! bash -c "${cmd}"; then
            echo "ERROR: Web smoke check failed on ${label} — the deploy aborts here under 'set -e'. Inspect web-app / web-proxy logs."
            return 1
        fi
    fi
    echo "Web smoke check passed on ${label} (http://localhost:3005)."
}

if [[ "${REMOTE_ONLY}" == "false" ]]; then
    echo "=== [2/4] Building and starting web-app + web-proxy on primary workstation ==="
    # Parse the config before compose runs: if compose itself recreates the proxy (spec/image drift),
    # it must not be the first thing to load an unvalidated file.
    bash "${SCRIPT_DIR}/ensure_proxy_config.sh" --validate-only \
        "${SCRIPT_DIR}/docker-compose.yml" web-proxy market-bench-web-proxy "${SCRIPT_DIR}/nginx.web.conf"
    (cd "${SCRIPT_DIR}" && docker compose -f docker-compose.yml up -d --build web-app web-proxy)
    # nginx.web.conf is a single-file bind mount: the container keeps the inode it was created with,
    # so a synced config stays invisible until the container is recreated. The helper validates the
    # new config first, recreates only when the served bytes differ, then asserts the rebind.
    bash "${SCRIPT_DIR}/ensure_proxy_config.sh" \
        "${SCRIPT_DIR}/docker-compose.yml" web-proxy market-bench-web-proxy "${SCRIPT_DIR}/nginx.web.conf"
    smoke_check "primary workstation" ""
else
    echo "=== [2/4] Skipping primary workstation (--remote-only) ==="
fi

if [[ "${LOCAL_ONLY}" == "false" ]]; then
    echo "=== [3/4] Syncing web workspace and Docker configs to ${TARGET_HOST} ==="
    if ! ssh -o ConnectTimeout=5 "${TARGET_HOST}" "echo 'SSH ok'" >/dev/null 2>&1; then
        echo "ERROR: Unable to reach ${TARGET_HOST} via SSH."
        exit 1
    fi

    ssh "${TARGET_HOST}" "mkdir -p ${REMOTE_DIR}/docker/archive ${REMOTE_DIR}/apps/web ${REMOTE_DIR}/packages/config ${REMOTE_DIR}/packages/database ${REMOTE_DIR}/packages/ui-design-system"

    rsync -avz \
        "${REPO_ROOT}/package.json" \
        "${REPO_ROOT}/pnpm-lock.yaml" \
        "${REPO_ROOT}/pnpm-workspace.yaml" \
        "${REPO_ROOT}/.gitignore" \
        "${REPO_ROOT}/.dockerignore" \
        "${TARGET_HOST}:${REMOTE_DIR}/"

    rsync -avz \
        "${SCRIPT_DIR}/Dockerfile.web" \
        "${SCRIPT_DIR}/nginx.web.conf" \
        "${SCRIPT_DIR}/nginx.web.secondary.conf" \
        "${SCRIPT_DIR}/ensure_proxy_config.sh" \
        "${SCRIPT_DIR}/docker-compose.secondary.yml" \
        "${TARGET_HOST}:${REMOTE_DIR}/docker/archive/"

    rsync -avz --delete \
        --exclude 'node_modules' \
        --exclude 'dist' \
        --exclude 'coverage' \
        --exclude '.netlify' \
        --exclude '.tanstack' \
        --exclude '.scratch' \
        "${REPO_ROOT}/apps/web/" \
        "${TARGET_HOST}:${REMOTE_DIR}/apps/web/"

    rsync -avz --delete --exclude 'node_modules' "${REPO_ROOT}/packages/config/" "${TARGET_HOST}:${REMOTE_DIR}/packages/config/"
    rsync -avz --delete --exclude 'node_modules' "${REPO_ROOT}/packages/database/" "${TARGET_HOST}:${REMOTE_DIR}/packages/database/"
    rsync -avz --delete --exclude 'node_modules' "${REPO_ROOT}/packages/ui-design-system/" "${TARGET_HOST}:${REMOTE_DIR}/packages/ui-design-system/"

    rsync -avz "${WEB_ENV_FILE}" "${TARGET_HOST}:${REMOTE_DIR}/apps/web/.env"
    if [[ -f "${ARCHIVE_ENV_FILE}" ]]; then
        rsync -avz "${ARCHIVE_ENV_FILE}" "${TARGET_HOST}:${REMOTE_DIR}/docker/archive/.env"
    fi

    echo "=== [4/4] Rebuilding and starting web-app + web-proxy on ${TARGET_HOST} ==="
    ssh "${TARGET_HOST}" "bash -lc 'set -a && source ${REMOTE_DIR}/apps/web/.env && if [ -f ${REMOTE_DIR}/docker/archive/.env ]; then source ${REMOTE_DIR}/docker/archive/.env; fi && set +a && export WEB_ENV_FILE=${REMOTE_DIR}/apps/web/.env && cd ${REMOTE_DIR}/docker/archive && bash ensure_proxy_config.sh --validate-only docker-compose.secondary.yml web-proxy market-bench-web-proxy-secondary nginx.web.secondary.conf && docker compose -f docker-compose.secondary.yml up -d --build web-app web-proxy && bash ensure_proxy_config.sh docker-compose.secondary.yml web-proxy market-bench-web-proxy-secondary nginx.web.secondary.conf && docker compose -f docker-compose.secondary.yml ps web-app web-proxy'"
    smoke_check "${TARGET_HOST}" "${TARGET_HOST}"
else
    echo "=== [3/4] Skipping MiniPC sync/deploy (--local-only) ==="
fi

echo "=== Self-hosted web deployment complete! ==="
