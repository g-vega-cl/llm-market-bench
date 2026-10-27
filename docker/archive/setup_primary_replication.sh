#!/usr/bin/env bash
set -euo pipefail

# setup_primary_replication.sh
# Idempotently configures the Primary PostgreSQL instance on this workstation for streaming replication to MiniPC.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"

if [[ -f "${ENV_FILE}" ]]; then
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
fi

CONTAINER_NAME="market-bench-archive-db"
DB_USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DB:-market_bench_archive}"
REPL_USER="${REPLICATION_USER:-replicator}"
REPL_PASSWORD="${REPLICATION_PASSWORD:-${POSTGRES_PASSWORD:-archive_replicator_password}}"
SLOT_NAME="${REPLICATION_SLOT:-minipc_standby_slot}"

echo "=== [1/4] Checking primary database container status ==="
if ! docker ps --filter "name=${CONTAINER_NAME}" --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "ERROR: ${CONTAINER_NAME} is not running! Start it first: docker compose -f ${SCRIPT_DIR}/docker-compose.yml up -d"
    exit 1
fi

echo "=== [2/4] Creating/updating replication user '${REPL_USER}' ==="
docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" <<EOF
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${REPL_USER}') THEN
        CREATE ROLE ${REPL_USER} WITH REPLICATION LOGIN PASSWORD '${REPL_PASSWORD}';
        RAISE NOTICE 'Role ${REPL_USER} created with REPLICATION privilege.';
    ELSE
        ALTER ROLE ${REPL_USER} WITH REPLICATION LOGIN PASSWORD '${REPL_PASSWORD}';
        RAISE NOTICE 'Role ${REPL_USER} updated with REPLICATION privilege.';
    END IF;
END
\$\$;
EOF

echo "=== [3/4] Ensuring physical replication slot '${SLOT_NAME}' exists ==="
docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" <<EOF
SELECT pg_create_physical_replication_slot('${SLOT_NAME}')
WHERE NOT EXISTS (
    SELECT 1 FROM pg_replication_slots WHERE slot_name = '${SLOT_NAME}'
);
EOF

echo "=== [4/4] Verifying pg_hba.conf rules for replication connections ==="
docker exec -i "${CONTAINER_NAME}" bash -c "
if ! grep -q 'host replication ${REPL_USER}' /var/lib/postgresql/data/pg_hba.conf; then
    echo 'host replication ${REPL_USER} 0.0.0.0/0 scram-sha-256' >> /var/lib/postgresql/data/pg_hba.conf
    echo 'Added replication rule to pg_hba.conf.'
else
    echo 'Replication rule already present in pg_hba.conf.'
fi
"
docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT pg_reload_conf();"

echo "=== Primary replication configuration complete! ==="
echo "Slot: ${SLOT_NAME} | Replicator User: ${REPL_USER}"
