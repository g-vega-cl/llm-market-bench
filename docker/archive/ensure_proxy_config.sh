#!/usr/bin/env bash
# ensure_proxy_config.sh [--validate-only] <compose-file> <service> <container> <host-config-path>
#
# A proxy config reaches its container as a single-file bind mount, so the container keeps reading
# the inode that existed when it was created. rsync/git checkout replace that inode, and
# `docker compose up` sees no service change, so it leaves the proxy serving the old bytes forever
# (reload re-reads the same stale inode). This helper makes the rebind explicit and safe:
#
#   1. compare host file against the bytes the container is actually serving -> no churn if equal,
#      except that a file rewritten in place (same inode, new bytes) is reloaded so nginx's memory
#      stops disagreeing with the mount
#   2. validate the new config BEFORE stopping anything, inside the live container so Docker DNS and
#      extra_hosts resolve static `upstream` blocks (a bare `nginx:alpine` cannot resolve
#      `archive-postgrest:3000` and would refuse every archive-proxy rebind)
#   3. recreate only that service, then assert the container is running and serves the new bytes
#
# --validate-only stops after step 2. Deployers call it before `docker compose up` so a config change
# can never reach a container through compose's own recreate without having been parsed first.
#
# Exit codes: 0 = serving the requested bytes (already, or after a rebind); 1 = nothing was changed
# and the caller must not claim success; 2 = bad invocation. A container that exists but is not
# running (crash loop, exited, restarting) is never recreated blind: it is reported and we abort.
set -euo pipefail

VALIDATE_ONLY=false
if [[ "${1:-}" == "--validate-only" ]]; then
    VALIDATE_ONLY=true
    shift
fi

if [[ $# -ne 4 ]]; then
    echo "usage: $(basename "$0") [--validate-only] <compose-file> <service> <container> <host-config-path>" >&2
    exit 2
fi

COMPOSE_FILE="$1"
SERVICE="$2"
CONTAINER="$3"
HOST_CONF="$4"
CONTAINER_CONF="/etc/nginx/nginx.conf"
VALIDATE_IN_CONTAINER="/tmp/.nginx-config-validate.$$.conf"
LOCK_FILE="${TMPDIR:-/tmp}/benchify-proxy-rebind.$(hostname -s).lock"

# Callers pass bare filenames from the compose directory; normalize once so md5/docker cp agree.
HOST_DIR="$(dirname "${HOST_CONF}")"
if ! HOST_DIR="$(cd "${HOST_DIR}" 2>/dev/null && pwd)"; then
    echo "ERROR: config directory does not exist: $(dirname "${HOST_CONF}")" >&2
    exit 1
fi
HOST_CONF="${HOST_DIR}/$(basename "${HOST_CONF}")"
if [[ ! -f "${HOST_CONF}" ]]; then
    echo "ERROR: config file not found: ${HOST_CONF}" >&2
    exit 1
fi

validate_in_container() {
    trap 'docker exec "${CONTAINER}" rm -f "${VALIDATE_IN_CONTAINER}" >/dev/null 2>&1 || true' EXIT
    docker cp "${HOST_CONF}" "${CONTAINER}:${VALIDATE_IN_CONTAINER}" >/dev/null
    if ! validate_out="$(docker exec "${CONTAINER}" nginx -t -c "${VALIDATE_IN_CONTAINER}" 2>&1)"; then
        echo "ERROR: $(basename "${HOST_CONF}") failed 'nginx -t'; refusing to touch ${CONTAINER} (the old config stays live)." >&2
        printf '%s\n' "${validate_out}" >&2
        exit 1
    fi
    docker exec "${CONTAINER}" rm -f "${VALIDATE_IN_CONTAINER}" >/dev/null 2>&1 || true
    trap - EXIT
}

# One rebind at a time per host: overlapping runs would otherwise validate each other's bytes.
exec 9>"${LOCK_FILE}"
if ! flock -w 300 9; then
    echo "ERROR: another proxy rebind is already running on this host (${LOCK_FILE})." >&2
    exit 1
fi

container_state="$(docker inspect "${CONTAINER}" --format '{{.State.Status}}' 2>/dev/null || echo missing)"

if [[ "${VALIDATE_ONLY}" == "true" ]]; then
    if [[ "${container_state}" == "running" ]]; then
        validate_in_container
        echo "    $(basename "${HOST_CONF}") parses cleanly inside ${CONTAINER}."
    else
        echo "    ${CONTAINER} is '${container_state}'; nothing to validate against yet."
    fi
    exit 0
fi

host_md5="$(md5sum "${HOST_CONF}" | awk '{print $1}')"
running_md5="$(docker exec "${CONTAINER}" md5sum "${CONTAINER_CONF}" 2>/dev/null | awk '{print $1}' || true)"

if [[ -n "${running_md5}" && "${running_md5}" == "${host_md5}" ]]; then
    echo "    ${CONTAINER} already serves $(basename "${HOST_CONF}") (${host_md5}); no recreate needed."
    # Same bytes can still mean stale memory when a writer edited the file in place (same inode):
    # the mount shows the new contents while nginx's master still holds the old ones. Reload is
    # graceful and does not drop established connections.
    file_mtime="$(docker exec "${CONTAINER}" stat -c %Y "${CONTAINER_CONF}" 2>/dev/null || echo 0)"
    started_at="$(docker inspect "${CONTAINER}" --format '{{.State.StartedAt}}' 2>/dev/null || true)"
    started_epoch="$(date -d "${started_at}" +%s 2>/dev/null || echo 0)"
    if [[ "${started_epoch}" -gt 0 && "${file_mtime}" -gt "${started_epoch}" ]]; then
        if docker exec "${CONTAINER}" nginx -s reload >/dev/null 2>&1; then
            echo "    config file is newer than the running master; reloaded in place."
        else
            echo "    WARNING: config is newer than the running master and 'nginx -s reload' failed; recreate by hand." >&2
        fi
    fi
    exit 0
fi

echo "    validating $(basename "${HOST_CONF}") before touching ${CONTAINER}..."
case "${container_state}" in
    running)
        # The only environment where static `upstream` hostnames resolve is the live container.
        validate_in_container
        ;;
    missing)
        # Nothing is serving yet, so there is no live front door to protect, and a bare container
        # cannot resolve the compose network's upstream aliases; the recreate below surfaces any
        # real config error.
        echo "    WARNING: ${CONTAINER} does not exist yet; skipping pre-flight 'nginx -t' (first create)."
        ;;
    *)
        # Crash loop, exited, paused: recreating here would replace a diagnosable failure with a
        # silent one, and the new config would be unvalidated.
        echo "ERROR: ${CONTAINER} exists but is '${container_state}'; refusing to recreate it with an unvalidated config." >&2
        echo "       Inspect first: docker logs --tail 50 ${CONTAINER}" >&2
        echo "       Force it anyway: docker compose -f ${COMPOSE_FILE} up -d --no-deps --force-recreate ${SERVICE}" >&2
        exit 1
        ;;
esac

echo "    recreating ${SERVICE} (${CONTAINER}) to rebind $(basename "${HOST_CONF}")..."
docker compose -f "${COMPOSE_FILE}" up -d --no-deps --force-recreate "${SERVICE}"

# Byte equality alone would pass for a container that serves the right file and then dies, so the
# assertion also requires a live container that never restarted.
for _ in 1 2 3 4 5 6; do
    now_md5="$(docker exec "${CONTAINER}" md5sum "${CONTAINER_CONF}" 2>/dev/null | awk '{print $1}' || true)"
    if [[ "${now_md5}" == "${host_md5}" ]]; then
        state_line="$(docker inspect "${CONTAINER}" --format '{{.State.Running}} {{.RestartCount}}' 2>/dev/null || true)"
        if [[ "${state_line}" != "true 0" ]]; then
            echo "ERROR: ${CONTAINER} serves ${host_md5} but is not healthy (running/restarts: '${state_line}')." >&2
            docker logs --tail 20 "${CONTAINER}" >&2 || true
            exit 1
        fi
        echo "    ${CONTAINER} now serves ${host_md5} (running, restart count 0)."
        exit 0
    fi
    sleep 2
done

echo "ERROR: ${CONTAINER} still serves stale $(basename "${HOST_CONF}") (wanted ${host_md5})." >&2
exit 1
