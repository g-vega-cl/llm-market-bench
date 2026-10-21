"""Tests for docker archive secret sanitation and JWT token generation."""

from pathlib import Path
from unittest.mock import MagicMock, patch

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

    secret = "test_secret_key_32_bytes_long_minimum!!"  # ggignore
    anon_token = generate_token(secret, role="anon")  # ggignore
    service_token = generate_token(secret, role="service_role")  # ggignore

    decoded_anon = jwt.decode(anon_token, secret, algorithms=["HS256"])
    assert decoded_anon["role"] == "anon"
    assert decoded_anon["iss"] == "supabase"

    decoded_service = jwt.decode(service_token, secret, algorithms=["HS256"])
    assert decoded_service["role"] == "service_role"
    assert decoded_service["iss"] == "supabase"


def test_update_postgres_role_password_success():
    """Verify update_postgres_role_password executes docker exec and returns True on exit 0."""
    from docker.archive.rotate_secrets import update_postgres_role_password

    mock_res = MagicMock()
    mock_res.returncode = 0
    dummy_role_pwd = "mock_test_role_password_only"  # ggignore

    with patch("subprocess.run", return_value=mock_res) as mock_run:
        success = update_postgres_role_password(dummy_role_pwd)
        assert success is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "docker" in args
        assert "exec" in args
        assert "market-bench-archive-db" in args
        assert f"ALTER USER postgres WITH PASSWORD '{dummy_role_pwd}';" in args[-1]  # ggignore


def test_update_postgres_role_password_failure():
    """Verify update_postgres_role_password returns False if docker exec fails or errors."""
    from docker.archive.rotate_secrets import update_postgres_role_password

    mock_res = MagicMock()
    mock_res.returncode = 1
    dummy_role_pwd = "mock_test_role_password_only"  # ggignore

    with patch("subprocess.run", return_value=mock_res):
        success = update_postgres_role_password(dummy_role_pwd)
        assert success is False

    with patch("subprocess.run", side_effect=OSError("Docker not found")):
        success = update_postgres_role_password(dummy_role_pwd)
        assert success is False


def test_gitguardian_configuration_ignores_secrets_test():
    """Verify that .gitguardian.yaml exists and ignores test_docker_archive_secrets.py."""
    gg_config_path = REPO_ROOT / ".gitguardian.yaml"
    assert gg_config_path.exists(), ".gitguardian.yaml must exist at repo root"
    content = gg_config_path.read_text(encoding="utf-8")
    assert "version: 2" in content
    assert "apps/engine/tests/test_docker_archive_secrets.py" in content


def test_rotate_all_sync_db_flag(tmp_path):
    """Verify rotate_all respects sync_db parameter."""
    from docker.archive.rotate_secrets import rotate_all

    with (
        patch("docker.archive.rotate_secrets.REPO_ROOT", tmp_path),
        patch("docker.archive.rotate_secrets.update_postgres_role_password") as mock_update,
    ):
        mock_update.return_value = True

        # Default sync_db=True
        rotate_all(sync_db=True)
        mock_update.assert_called_once()

        mock_update.reset_mock()
        # sync_db=False
        rotate_all(sync_db=False)
        mock_update.assert_not_called()
