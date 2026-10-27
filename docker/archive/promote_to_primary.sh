#!/usr/bin/env bash
set -euo pipefail

# promote_to_primary.sh
# Emergency failover script: Promotes MiniPC PostgreSQL standby replica to read-write Primary
# and configures Nginx to route all mutations locally.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_CONTAINER="market-bench-archive-db-replica"
PROXY_CONTAINER="market-bench-archive-proxy-replica"
NGINX_CONF="${SCRIPT_DIR}/nginx.secondary.conf"

echo "=== [1/3] Verifying standby state ==="
if ! docker ps --filter "name=${DB_CONTAINER}" --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    echo "ERROR: ${DB_CONTAINER} is not running! Cannot promote."
    exit 1
fi

IS_RECOVERY=$(docker exec "${DB_CONTAINER}" psql -U postgres -d market_bench_archive -t -c "SELECT pg_is_in_recovery();" | tr -d '[:space:]')
if [[ "${IS_RECOVERY}" != "t" ]]; then
    echo "INFO: Database is already in read-write primary mode (pg_is_in_recovery = false)."
else
    echo "=== [2/3] Promoting PostgreSQL standby to primary ==="
    docker exec "${DB_CONTAINER}" su - postgres -c "pg_ctl promote -D /var/lib/postgresql/data"
    sleep 2
    NEW_STATE=$(docker exec "${DB_CONTAINER}" psql -U postgres -d market_bench_archive -t -c "SELECT pg_is_in_recovery();" | tr -d '[:space:]')
    echo "New recovery state: ${NEW_STATE} (f = primary read-write)"
fi

echo "=== [3/3] Switching Nginx routing to 100% local processing ==="
# Replace upstream mapping to route all methods (reads + writes) locally
sed -i.bak 's/default primary_write_backend;/default local_read_backend;/g' "${NGINX_CONF}"
sed -i 's/POST    primary_write_backend;/POST    local_read_backend;/g' "${NGINX_CONF}"
sed -i 's/PUT     primary_write_backend;/PUT     local_read_backend;/g' "${NGINX_CONF}"
sed -i 's/PATCH   primary_write_backend;/PATCH   local_read_backend;/g' "${NGINX_CONF}"
sed -i 's/DELETE  primary_write_backend;/DELETE  local_read_backend;/g' "${NGINX_CONF}"

echo "Reloading Nginx reverse proxy..."
docker exec "${PROXY_CONTAINER}" nginx -s reload

echo "=== Failover Complete! ==="
echo "MiniPC is now operating as the Primary Read-Write database and API gateway."
