"""Tests for secondary edge server (MiniPC) cluster configuration, replication, and failover scripts."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ARCHIVE_DIR = REPO_ROOT / "docker" / "archive"

COMPOSE_SECONDARY = ARCHIVE_DIR / "docker-compose.secondary.yml"
NGINX_SECONDARY = ARCHIVE_DIR / "nginx.secondary.conf"
SETUP_PRIMARY_SCRIPT = ARCHIVE_DIR / "setup_primary_replication.sh"
BOOTSTRAP_REPLICA_SCRIPT = ARCHIVE_DIR / "bootstrap_replica.sh"
PROMOTE_SCRIPT = ARCHIVE_DIR / "promote_to_primary.sh"
DEPLOY_SCRIPT = ARCHIVE_DIR / "deploy_secondary.sh"


def test_secondary_compose_exists_and_sanitized():
    """Verify docker-compose.secondary.yml exists, declares required edge services, and leaks no secrets."""
    assert COMPOSE_SECONDARY.exists(), f"Missing {COMPOSE_SECONDARY}"
    content = COMPOSE_SECONDARY.read_text(encoding="utf-8")

    # Services verification
    assert "archive-db-replica:" in content
    assert "archive-postgrest:" in content
    assert "archive-proxy:" in content
    assert "free-llm-proxy:" in content

    # Secret hygiene: environment variable interpolation must be used
    assert "${POSTGRES_PASSWORD}" in content
    assert "${PGRST_JWT_SECRET}" in content
    assert "password123" not in content.lower()
    assert "secret123" not in content.lower()

    # Port bindings verification
    assert "3001:80" in content
    assert "8086:8086" in content


def test_nginx_secondary_method_routing_and_error_handling():
    """Verify nginx.secondary.conf splits reads and writes, and provides 503 fallback."""
    assert NGINX_SECONDARY.exists(), f"Missing {NGINX_SECONDARY}"
    content = NGINX_SECONDARY.read_text(encoding="utf-8")

    # Method-based upstream mapping
    assert "map $request_method $upstream_backend" in content
    assert "GET     local_read_backend;" in content or "GET     http://archive-postgrest:3000" in content
    assert "POST    primary_write_backend;" in content or "POST    http://" in content

    # 503 Fallback / error handling when primary write node is down
    assert "error_page 502 503 504" in content
    assert "application/json" in content
    assert "Primary write node unavailable" in content


def test_setup_primary_replication_script():
    """Verify setup_primary_replication.sh creates replication user, slot, and hba rules."""
    assert SETUP_PRIMARY_SCRIPT.exists(), f"Missing {SETUP_PRIMARY_SCRIPT}"
    content = SETUP_PRIMARY_SCRIPT.read_text(encoding="utf-8")

    assert "REPLICATION LOGIN" in content
    assert "minipc_standby_slot" in content
    assert "pg_create_physical_replication_slot" in content
    assert "pg_hba.conf" in content


def test_bootstrap_replica_script():
    """Verify bootstrap_replica.sh runs pg_basebackup with standby signal flags."""
    assert BOOTSTRAP_REPLICA_SCRIPT.exists(), f"Missing {BOOTSTRAP_REPLICA_SCRIPT}"
    content = BOOTSTRAP_REPLICA_SCRIPT.read_text(encoding="utf-8")

    assert "pg_basebackup" in content
    assert "-R" in content  # Automatically creates standby.signal and primary_conninfo
    assert "-S" in content
    assert "minipc_standby_slot" in content
    assert "replicator" in content


def test_promote_to_primary_script():
    """Verify promote_to_primary.sh promotes PostgreSQL and switches Nginx routing locally."""
    assert PROMOTE_SCRIPT.exists(), f"Missing {PROMOTE_SCRIPT}"
    content = PROMOTE_SCRIPT.read_text(encoding="utf-8")

    assert "pg_ctl promote" in content or "pg_promote" in content
    assert "nginx" in content.lower()
    assert "reload" in content.lower()


def test_deploy_secondary_script():
    """Verify deploy_secondary.sh contains remote sync, env validation, and docker invocation."""
    assert DEPLOY_SCRIPT.exists(), f"Missing {DEPLOY_SCRIPT}"
    content = DEPLOY_SCRIPT.read_text(encoding="utf-8")

    assert "cv-minipc@minipc" in content or "$TARGET_HOST" in content
    assert "docker-compose.secondary.yml" in content
    assert "rsync" in content or "scp" in content
