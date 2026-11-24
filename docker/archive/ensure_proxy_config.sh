#!/usr/bin/env bash
# ensure_proxy_config.sh <compose-file> <service> <container> <host-config-path>
#
# A proxy config reaches its container as a single-file bind mount, so the container keeps reading
# the inode that existed when it was created. rsync/git checkout replace that inode, and
# `docker compose up` sees no service change, so it leaves the proxy serving the old bytes forever
# (reload re-reads the same stale inode). This helper makes the rebind explicit and safe:
#
#   1. compare host file against the bytes the container is actually serving -> no churn if equal
#   2. validate the new config BEFORE stopping anything, inside the live container so Docker DNS and
#      extra_hosts resolve static `upstream` blocks (a bare `nginx:alpine` cannot resolve
#      `archive-postgrest:3000` and would refuse every archive-proxy rebind)
#   3. recreate only that service, then assert the container now serves the new bytes
set -euo pipefail

COMPOSE_FILE="$1"
SERVICE="$2"
CONTAINER="$3"
HOST_CONF="$4"
IMAGE="${PROXY_IMAGE:-nginx:alpine}"
VALIDATE_IN_CONTAINER="/tmp/.nginx-config-validate.conf"

# `docker run -v` demands an absolute host path, while the deployers call this from the compose
# directory with relative config names, so normalize the path once here.
HOST_CONF="$(cd "$(dirname "${HOST_CONF}")" && pwd)/$(basename "${HOST_CONF}")"

host_md5="$(md5sum "${HOST_CONF}" | awk '{print $1}')"
running_md5="$(docker exec "${CONTAINER}" md5sum /etc/nginx/nginx.conf 2>/dev/null | awk '{print $1}' || true)"

if [[ -n "${running_md5}" && "${running_md5}" == "${host_md5}" ]]; then
    echo "    ${CONTAINER} already serves $(basename "${HOST_CONF}") (${host_md5}); no recreate needed."
    exit 0
fi

echo "    validating $(basename "${HOST_CONF}") before touching ${CONTAINER}..."
if [[ "$(docker inspect "${CONTAINER}" --format '{{.State.Running}}' 2>/dev/null || true)" == "true" ]]; then
    docker cp "${HOST_CONF}" "${CONTAINER}:${VALIDATE_IN_CONTAINER}" >/dev/null
    if ! validate_out="$(docker exec "${CONTAINER}" nginx -t -c "${VALIDATE_IN_CONTAINER}" 2>&1)"; then
        docker exec "${CONTAINER}" rm -f "${VALIDATE_IN_CONTAINER}" >/dev/null 2>&1 || true
        echo "ERROR: $(basename "${HOST_CONF}") failed 'nginx -t'; refusing to recreate ${CONTAINER} (the old config stays live)." >&2
        printf '%s\n' "${validate_out}" >&2
        exit 1
    fi
    docker exec "${CONTAINER}" rm -f "${VALIDATE_IN_CONTAINER}" >/dev/null 2>&1 || true
else
    # Nothing is serving yet: there is no live front door to protect, and a bare container cannot
    # resolve the compose network's upstream aliases, so a pre-flight test would only produce false
    # negatives. The recreate below surfaces any real config error.
    echo "    WARNING: ${CONTAINER} is not running; skipping pre-flight 'nginx -t' (first create)."
fi

echo "    recreating ${SERVICE} (${CONTAINER}) to rebind $(basename "${HOST_CONF}")..."
docker compose -f "${COMPOSE_FILE}" up -d --no-deps --force-recreate "${SERVICE}"

for _ in 1 2 3 4 5 6; do
    now_md5="$(docker exec "${CONTAINER}" md5sum /etc/nginx/nginx.conf 2>/dev/null | awk '{print $1}' || true)"
    if [[ "${now_md5}" == "${host_md5}" ]]; then
        echo "    ${CONTAINER} now serves ${host_md5}."
        exit 0
    fi
    sleep 2
done

echo "ERROR: ${CONTAINER} still serves stale $(basename "${HOST_CONF}") (wanted ${host_md5})." >&2
exit 1
