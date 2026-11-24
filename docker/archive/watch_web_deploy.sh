#!/usr/bin/env bash
set -euo pipefail

# watch_web_deploy.sh
# Polls origin/main in an isolated clean clone and triggers deploy_web.sh
# whenever web-related files change. Safe for public repos (no external runner).

export PATH="${HOME}/.nvm/versions/node/v24.22.1/bin:${HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin:${PATH}"

REPO_URL="${BENCHIFY_REPO_URL:-https://github.com/g-vega-cl/llm-market-bench.git}"
DEPLOY_REPO="${BENCHIFY_DEPLOY_REPO:-${HOME}/.local/share/benchify-deploy-repo}"
STATE_DIR="${HOME}/.config/benchify"
STATE_FILE="${STATE_DIR}/last-attempted-web-sha"
LOCK_FILE="/tmp/benchify-web-deploy.lock"

mkdir -p "${STATE_DIR}"

exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
    exit 0
fi

if [[ ! -d "${DEPLOY_REPO}/.git" ]]; then
    mkdir -p "$(dirname "${DEPLOY_REPO}")"
    git clone --branch main --single-branch "${REPO_URL}" "${DEPLOY_REPO}"
fi

cd "${DEPLOY_REPO}"
git fetch --quiet origin main
REMOTE_SHA="$(git rev-parse origin/main)"

if [[ ! -f "${STATE_FILE}" ]]; then
    echo "${REMOTE_SHA}" > "${STATE_FILE}"
    echo "[watch_web_deploy] Initialized state at ${REMOTE_SHA}; waiting for next push."
    exit 0
fi

LAST_SHA="$(cat "${STATE_FILE}")"
if [[ "${REMOTE_SHA}" == "${LAST_SHA}" ]]; then
    exit 0
fi

# Skip builds unless web, shared TS packages, or web Docker/compose files changed.
if git diff --quiet "${LAST_SHA}" "${REMOTE_SHA}" -- \
    apps/web \
    packages/config \
    packages/database \
    packages/ui-design-system \
    docker/archive/Dockerfile.web \
    docker/archive/nginx.web.conf \
    docker/archive/docker-compose.yml \
    docker/archive/docker-compose.secondary.yml \
    docker/archive/deploy_web.sh \
    docker/archive/ensure_proxy_config.sh \
    package.json \
    pnpm-lock.yaml \
    pnpm-workspace.yaml \
    .dockerignore; then
    echo "${REMOTE_SHA}" > "${STATE_FILE}"
    echo "[watch_web_deploy] ${REMOTE_SHA} has no web changes; skipped deploy."
    exit 0
fi

echo "[watch_web_deploy] Detected web changes (${LAST_SHA:0:8}..${REMOTE_SHA:0:8}); deploying..."
# Record attempt before running so a failing commit does not loop every 60s.
echo "${REMOTE_SHA}" > "${STATE_FILE}"

git reset --hard "${REMOTE_SHA}"
pnpm install --frozen-lockfile
WEB_ENV_FILE="${STATE_DIR}/web.env" \
ARCHIVE_ENV_FILE="${STATE_DIR}/archive.env" \
./docker/archive/deploy_web.sh

echo "[watch_web_deploy] Deployed ${REMOTE_SHA:0:8} successfully."
