"""Utility script to generate cryptographically secure secrets and mint HS256 PostgREST tokens."""

import re
import secrets
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

    filepath.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def rotate_all() -> dict[str, str]:
    """Generate new secrets, write .env files, and return secret summary."""
    new_jwt_secret = secrets.token_hex(32)
    new_pg_password = secrets.token_urlsafe(32)

    anon_jwt = generate_token(new_jwt_secret, role="anon")
    service_jwt = generate_token(new_jwt_secret, role="service_role")

    # 1. Write docker/archive/.env
    archive_env = REPO_ROOT / "docker" / "archive" / ".env"
    archive_updates = {
        "POSTGRES_DB": "market_bench_archive",
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": new_pg_password,
        "PGRST_JWT_SECRET": new_jwt_secret,
        "PGRST_OPENAPI_SERVER_PROXY_URI": "https://benchify-archive-db.clvg.uk",
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

    # 3. Update apps/web/.env
    web_env = REPO_ROOT / "apps" / "web" / ".env"
    if web_env.exists():
        web_updates = {
            "SUPABASE_ANON_KEY": anon_jwt,
            "VITE_SUPABASE_ANON_KEY": anon_jwt,
            "SUPABASE_URL": "https://benchify-archive-db.clvg.uk",
            "VITE_SUPABASE_URL": "https://benchify-archive-db.clvg.uk",
        }
        update_env_file(web_env, web_updates)

    return {
        "POSTGRES_PASSWORD": new_pg_password,
        "PGRST_JWT_SECRET": new_jwt_secret,
        "SUPABASE_ANON_KEY": anon_jwt,
        "SUPABASE_SERVICE_ROLE_KEY": service_jwt,
    }


if __name__ == "__main__":
    creds = rotate_all()
    print("Secrets rotated successfully.")
