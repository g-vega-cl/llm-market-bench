"""Tests for docker archive secret sanitation and JWT token generation."""

from pathlib import Path

import jwt

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
COMPOSE_PATH = REPO_ROOT / "docker" / "archive" / "docker-compose.yml"

LEAKED_JWT_SECRET = "915f2b56f99826c5d433e491c3d22e575836a9116ad040196e93668cad2f36b0"
LEAKED_POSTGRES_PASSWORD = "archive_secure_password_local"


def test_docker_compose_does_not_contain_hardcoded_secrets():
    """Verify that docker-compose.yml does not expose plaintext secrets."""
    assert COMPOSE_PATH.exists(), f"Compose file not found at {COMPOSE_PATH}"
    compose_content = COMPOSE_PATH.read_text(encoding="utf-8")

    assert LEAKED_JWT_SECRET not in compose_content, "Leaked PGRST_JWT_SECRET found in docker-compose.yml!"
    assert LEAKED_POSTGRES_PASSWORD not in compose_content, "Hardcoded POSTGRES_PASSWORD found in docker-compose.yml!"
    assert "${PGRST_JWT_SECRET}" in compose_content, "docker-compose.yml must reference ${PGRST_JWT_SECRET}"
    assert "${POSTGRES_PASSWORD}" in compose_content, "docker-compose.yml must reference ${POSTGRES_PASSWORD}"


def test_minted_jwt_tokens_are_valid():
    """Verify that JWT tokens can be signed and verified with HS256 and expected claims."""
    from docker.archive.rotate_secrets import generate_token

    secret = "test_secret_key_32_bytes_long_minimum!!"
    anon_token = generate_token(secret, role="anon")
    service_token = generate_token(secret, role="service_role")

    decoded_anon = jwt.decode(anon_token, secret, algorithms=["HS256"])
    assert decoded_anon["role"] == "anon"
    assert decoded_anon["iss"] == "supabase"

    decoded_service = jwt.decode(service_token, secret, algorithms=["HS256"])
    assert decoded_service["role"] == "service_role"
    assert decoded_service["iss"] == "supabase"
