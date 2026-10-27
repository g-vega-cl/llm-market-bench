#!/usr/bin/env bash
set -euo pipefail

# bootstrap_replica.sh
# Runs on the MiniPC (secondary server) to pull the initial base backup and join the cluster as a streaming standby.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"

if [[ -f "${ENV_FILE}" ]]; then
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
fi

PRIMARY_HOST="${PRIMARY_HOST:-primary-workstation}"
PRIMARY_PORT="${PRIMARY_PORT:-5433}"
REPL_USER="${REPLICATION_USER:-replicator}"
REPL_PASSWORD="${REPLICATION_PASSWORD:-${POSTGRES_PASSWORD:-archive_replicator_password}}"
SLOT_NAME="${REPLICATION_SLOT:-minipc_standby_slot}"
VOLUME_NAME="archive_pgdata_replica"

echo "=== [1/4] Stopping replica containers if running ==="
docker compose -f "${SCRIPT_DIR}/docker-compose.secondary.yml" down || true

echo "=== [2/4] Ensuring Docker volume '${VOLUME_NAME}' exists ==="
docker volume create "${VOLUME_NAME}" >/dev/null

echo "=== [3/4] Pulling initial pg_basebackup with standby signal (-R) ==="
docker run --rm \
    -v "${VOLUME_NAME}:/var/lib/postgresql/data" \
    -e PGPASSWORD="${REPL_PASSWORD}" \
    ankane/pgvector:latest \
    bash -c "
        set -e
        echo 'Cleaning existing data directory...'
        rm -rf /var/lib/postgresql/data/*
        echo 'Streaming base backup from ${PRIMARY_HOST}:${PRIMARY_PORT}...'
        pg_basebackup -h ${PRIMARY_HOST} -p ${PRIMARY_PORT} -U ${REPL_USER} -D /var/lib/postgresql/data -Fp -Xs -P -R -S ${SLOT_NAME}
        chown -R postgres:postgres /var/lib/postgresql/data
        chmod 700 /var/lib/postgresql/data
        echo 'Standby basebackup initialized successfully.'
    "

echo "=== [4/4] Starting secondary edge stack ==="
docker compose -f "${SCRIPT_DIR}/docker-compose.secondary.yml" up -d

echo "Waiting for replica to enter recovery mode..."
sleep 3
docker exec market-bench-archive-db-replica psql -U postgres -d "${POSTGRES_DB:-market_bench_archive}" -c "SELECT pg_is_in_recovery() AS is_standby_replica;"

echo "=== MiniPC replica bootstrap completed successfully! ==="
