"""Utility script to generate cryptographically secure secrets and mint HS256 PostgREST tokens."""

import re
import secrets
import subprocess
import time
from pathlib import Path
import jwt

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def generate_token(secret: str, role: str) -> str:
    """Mint an HS256 PostgREST JWT compatible with Supabase SDKs."""
    now = int(time.time())
    payload = {
        "role": role,
        "iss": "supabase",
        "iat": now,
        "exp": now + 10 * 365 * 24 * 3600,  # 10-year validity
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def update_env_file(filepath: Path, updates: dict[str, str]) -> None:
    """Update or append environment variables in a .env file."""
    if not filepath.exists():
        content = ""
    else:
        content = filepath.read_text(encoding="utf-8")

    lines = content.splitlines()
    keys_updated = set()
    new_lines = []

    for line in lines:
        matched = False
        for key, val in updates.items():
            if re.match(rf"^{key}\s*=", line):
                new_lines.append(f"{key}={val}")
                keys_updated.add(key)
                matched = True
                break
        if not matched:
            new_lines.append(line)

    for key, val in updates.items():
        if key not in keys_updated:
            new_lines.append(f"{key}={val}")

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def update_postgres_role_password(
    password: str, container_name: str = "market-bench-archive-db"
) -> bool:
    """Execute ALTER USER postgres WITH PASSWORD inside the running container if accessible.

    PostgreSQL container volumes (archive_pgdata) preserve existing user passwords across restarts;
    changing POSTGRES_PASSWORD in .env does not alter existing database users unless updated via SQL.
    """
    try:
        cmd = [
            "docker",
            "exec",
            container_name,
            "psql",
            "-U",
            "postgres",
            "-d",
            "market_bench_archive",
            "-c",
            f"ALTER USER postgres WITH PASSWORD '{password}';",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return res.returncode == 0
    except Exception:
        return False


def rotate_all(sync_db: bool = True) -> dict[str, str]:
    """Generate new secrets, write .env files, and return secret summary."""
    new_jwt_secret = secrets.token_hex(32)
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    new_pg_password = "".join(secrets.choice(alphabet) for _ in range(32))
    new_repl_password = "".join(secrets.choice(alphabet) for _ in range(32))

    anon_jwt = generate_token(new_jwt_secret, role="anon")
    service_jwt = generate_token(new_jwt_secret, role="service_role")

    if sync_db:
        db_synced = update_postgres_role_password(new_pg_password)
        if db_synced:
            print(
                "Successfully updated postgres role password in running database container."
            )
        else:
            print(
                "WARNING: Could not update postgres user password in running container."
            )
            print("If the database has an existing persistent volume, execute:")
            print(
                f"  docker exec market-bench-archive-db psql -U postgres -d market_bench_archive -c \"ALTER USER postgres WITH PASSWORD '{new_pg_password}';\""
            )

    # 1. Write docker/archive/.env
    archive_env = REPO_ROOT / "docker" / "archive" / ".env"
    archive_updates = {
        "POSTGRES_DB": "market_bench_archive",
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": new_pg_password,
        "PGRST_JWT_SECRET": new_jwt_secret,
        "PGRST_OPENAPI_SERVER_PROXY_URI": "https://benchify-archive-db.clvg.uk",
        "REPLICATION_USER": "replicator",
        "REPLICATION_PASSWORD": new_repl_password,
        "REPLICATION_SLOT": "minipc_standby_slot",
    }
    update_env_file(archive_env, archive_updates)

    # 2. Update apps/engine/.env
    engine_env = REPO_ROOT / "apps" / "engine" / ".env"
    if engine_env.exists():
        engine_updates = {
            "SUPABASE_SERVICE_ROLE_KEY": service_jwt,
            "SUPABASE_ANON_KEY": anon_jwt,
            "SUPABASE_PROJECT_URL": "https://benchify-archive-db.clvg.uk",
        }
        update_env_file(engine_env, engine_updates)

    # 3. Update apps/web/.env (Archive DB keys only — never overwrite Supabase Cloud Auth keys!)
    web_env = REPO_ROOT / "apps" / "web" / ".env"
    if web_env.exists():
        web_updates = {
            "ARCHIVE_DB_ANON_KEY": anon_jwt,
            "VITE_ARCHIVE_DB_ANON_KEY": anon_jwt,
            "ARCHIVE_DB_SERVICE_ROLE_KEY": service_jwt,
            "ARCHIVE_DB_URL": "https://benchify-archive-db.clvg.uk",
            "VITE_ARCHIVE_DB_URL": "https://benchify-archive-db.clvg.uk",
        }
        update_env_file(web_env, web_updates)

    return {
        "POSTGRES_PASSWORD": new_pg_password,
        "PGRST_JWT_SECRET": new_jwt_secret,
        "REPLICATION_PASSWORD": new_repl_password,
        "ARCHIVE_DB_ANON_KEY": anon_jwt,
        "ARCHIVE_DB_SERVICE_ROLE_KEY": service_jwt,
        "SUPABASE_ANON_KEY": anon_jwt,
        "SUPABASE_SERVICE_ROLE_KEY": service_jwt,
    }


if __name__ == "__main__":
    creds = rotate_all()
    print("Secrets rotated successfully.")
    print("\n--- DEPLOYMENT CHECKLIST ---")
    print("1. Netlify (Site Settings -> Environment Variables):")
    print("   # Local PostgREST Archive DB (Data API):")
    print("   ARCHIVE_DB_URL              = https://benchify-archive-db.clvg.uk")
    print("   VITE_ARCHIVE_DB_URL         = https://benchify-archive-db.clvg.uk")
    print(
        "   VITE_ARCHIVE_DB_ANON_KEY    = <ARCHIVE_DB_ANON_KEY>  (ANON KEY ONLY - NEVER SERVICE ROLE!)"
    )
    print("   ARCHIVE_DB_ANON_KEY         = <ARCHIVE_DB_ANON_KEY>")
    print("   ARCHIVE_DB_SERVICE_ROLE_KEY = <ARCHIVE_DB_SERVICE_ROLE_KEY>")
    print("   # Supabase Cloud (Auth Only - DO NOT point to benchify-archive-db!):")
    print("   SUPABASE_AUTH_URL           = https://<project-ref>.supabase.co")
    print("   VITE_SUPABASE_AUTH_URL      = https://<project-ref>.supabase.co")
    print("   SUPABASE_AUTH_ANON_KEY      = <cloud-supabase-anon-key>")
    print("   VITE_SUPABASE_AUTH_ANON_KEY = <cloud-supabase-anon-key>")
    print("   (Then trigger 'Clear cache and deploy site')")
    print("\n2. GitHub Actions Secrets (Repository Settings -> Secrets -> Actions):")
    print("   SUPABASE_SERVICE_ROLE_KEY = <SUPABASE_SERVICE_ROLE_KEY>")
    print("   SUPABASE_ANON_KEY         = <SUPABASE_ANON_KEY>")
    print("   SUPABASE_PROJECT_URL      = https://benchify-archive-db.clvg.uk")
    print("\n3. Restart local Docker archive stack:")
    print(
        "   docker compose -f docker/archive/docker-compose.yml up -d --force-recreate"
    )
