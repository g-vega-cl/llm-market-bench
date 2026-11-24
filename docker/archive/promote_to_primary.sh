#!/usr/bin/env bash
set -euo pipefail

# promote_to_primary.sh
# Emergency failover: promote the MiniPC PostgreSQL standby to read-write primary, rewrite the archive
# proxy routing to serve mutations locally, and prove the proxy is actually serving that routing
# before declaring success.
#
# nginx.secondary.conf is a single-file bind mount, so `nginx -s reload` re-reads the stale inode and
# would silently keep the pre-failover routing. The rebind therefore goes through
# ensure_proxy_config.sh (validate -> recreate -> assert), and the .promoted sentinel stops the next
# deploy_secondary.sh run from rsyncing standby routing back over a live failover.
#
# Runs ON the MiniPC, from ~/llm-market-bench/docker/archive.
# Every gate below exits non-zero; "Failover Complete!" prints only after all of them pass.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_CONTAINER="market-bench-archive-db-replica"
PROXY_CONTAINER="market-bench-archive-proxy-replica"
PROXY_SERVICE="archive-proxy"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.secondary.yml"
NGINX_CONF="${SCRIPT_DIR}/nginx.secondary.conf"
SENTINEL="${SCRIPT_DIR}/.promoted"
PSQL=(docker exec "${DB_CONTAINER}" psql -U postgres -d market_bench_archive -t -c)

echo "=== [1/4] Verifying standby state ==="
if [[ "$(docker inspect "${DB_CONTAINER}" --format '{{.State.Running}}' 2>/dev/null || echo false)" != "true" ]]; then
    echo "ERROR: ${DB_CONTAINER} is not running! Cannot promote."
    exit 1
fi

IS_RECOVERY="$("${PSQL[@]}" "SELECT pg_is_in_recovery();" | tr -d '[:space:]')"
case "${IS_RECOVERY}" in
t)
    echo "=== [2/4] Promoting PostgreSQL standby to primary ==="
    docker exec "${DB_CONTAINER}" su - postgres -c "pg_ctl promote -D /var/lib/postgresql/data"

    # Poll instead of sleeping: pg_ctl promote returns before the server itself leaves recovery.
    NEW_STATE="${IS_RECOVERY}"
    for _ in $(seq 1 15); do
        NEW_STATE="$("${PSQL[@]}" "SELECT pg_is_in_recovery();" | tr -d '[:space:]')"
        [[ "${NEW_STATE}" == "f" ]] && break
        sleep 1
    done
    if [[ "${NEW_STATE}" != "f" ]]; then
        echo "ERROR: ${DB_CONTAINER} is still in recovery (pg_is_in_recovery = ${NEW_STATE}) after promotion."
        exit 1
    fi
    echo "New recovery state: ${NEW_STATE} (f = primary read-write)"
    ;;
f)
    echo "INFO: Database is already in read-write primary mode (pg_is_in_recovery = false)."
    ;;
*)
    echo "ERROR: could not determine recovery state (got '${IS_RECOVERY}'); refusing to promote blindly." >&2
    exit 1
    ;;
esac

echo "=== [3/4] Switching Nginx routing to 100% local processing ==="
# Replace upstream mapping to route all methods (reads + writes) locally
sed -i.bak 's/default primary_write_backend;/default local_read_backend;/g' "${NGINX_CONF}"
sed -i 's/POST    primary_write_backend;/POST    local_read_backend;/g' "${NGINX_CONF}"
sed -i 's/PUT     primary_write_backend;/PUT     local_read_backend;/g' "${NGINX_CONF}"
sed -i 's/PATCH   primary_write_backend;/PATCH   local_read_backend;/g' "${NGINX_CONF}"
sed -i 's/DELETE  primary_write_backend;/DELETE  local_read_backend;/g' "${NGINX_CONF}"

# The seds are whitespace-literal, so assert the rewrite landed instead of trusting it: only the
# now-unused `upstream primary_write_backend` block may survive.
routing_refs="$(grep -c 'primary_write_backend' "${NGINX_CONF}" || true)"
if ! grep -q 'default local_read_backend' "${NGINX_CONF}" || [[ "${routing_refs}" -gt 1 ]]; then
    echo "ERROR: routing rewrite incomplete (${routing_refs} 'primary_write_backend' reference(s) left; only the upstream block may remain)." >&2
    echo "       Nothing was rebound. Fix ${NGINX_CONF} by hand, then re-run this script." >&2
    exit 1
fi

# Written before the rebind so that even a failed rebind cannot be reverted by a later deploy.
printf '%s promoted on %s by %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(hostname)" "$(id -un)" > "${SENTINEL}"

echo "   rebinding ${PROXY_CONTAINER} (validate -> recreate -> assert)..."
if ! bash "${SCRIPT_DIR}/ensure_proxy_config.sh" \
    "${COMPOSE_FILE}" "${PROXY_SERVICE}" "${PROXY_CONTAINER}" "${NGINX_CONF}"; then
    echo "ERROR: PostgreSQL is promoted and ${SENTINEL} exists, but ${PROXY_CONTAINER} still serves the pre-failover routing." >&2
    echo "       Writes still point at the dead primary. Re-run by hand:" >&2
    echo "         cd ${SCRIPT_DIR} && bash ensure_proxy_config.sh docker-compose.secondary.yml ${PROXY_SERVICE} ${PROXY_CONTAINER} nginx.secondary.conf" >&2
    exit 1
fi

echo "=== [4/4] Verifying failover state ==="
if ! docker exec "${PROXY_CONTAINER}" grep -q 'default local_read_backend' /etc/nginx/nginx.conf; then
    echo "ERROR: the running proxy does not show local write routing; failover is NOT complete." >&2
    exit 1
fi
echo "   proxy serves local write routing."

# Split-brain check: primary-workstation is an extra_hosts alias inside the proxy container, NOT a
# host-level name, so resolve it there and probe the address from this host.
WORKSTATION_IP="$(docker exec "${PROXY_CONTAINER}" getent hosts primary-workstation 2>/dev/null | awk 'NR==1{print $1}')"
if [[ -z "${WORKSTATION_IP}" ]]; then
    echo "   NOTE: primary-workstation does not resolve inside ${PROXY_CONTAINER}; split-brain check skipped."
elif curl -fsS --max-time 3 -o /dev/null "http://${WORKSTATION_IP}:3001/rest/v1/"; then
    echo "   WARNING: the workstation archive API still answers at ${WORKSTATION_IP}:3001."
    echo "            Two live primaries can accept writes. Stop the workstation archive stack before trusting this state."
else
    echo "   workstation archive API is not answering at ${WORKSTATION_IP}:3001 (expected)."
fi

echo "=== Failover Complete! ==="
echo "MiniPC is now the read-write database and API gateway for benchify.dev."
echo
echo "Demotion (reverse failover), run from the workstation once it is healthy again:"
echo "  1. stop this host's write surface:  docker compose -f docker-compose.secondary.yml stop archive-postgrest"
echo "  2. demote this database: pg_rewind against the recovered workstation primary, or re-run bootstrap_replica.sh"
echo "     NOTE: both discard every write this host accepted during the failover. Export what you need first."
echo "  3. rm -f ${SENTINEL}"
echo "  4. ./docker/archive/deploy_secondary.sh cv-minipc@minipc   # restores standby routing + rebinds the proxy"
