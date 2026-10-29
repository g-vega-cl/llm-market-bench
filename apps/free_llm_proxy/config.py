"""Configuration module for Free LLM Proxy."""

import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from app directory or engine directory
app_dir = Path(__file__).resolve().parent
load_dotenv(app_dir / ".env")
load_dotenv(app_dir.parent / "engine" / ".env")

PORT = int(os.environ.get("PORT", "8086"))
HOST = os.environ.get("HOST", "127.0.0.1")
MASTER_KEY = os.environ.get("FREE_PROXY_MASTER_KEY", "sk-free-proxy-secret-key-12345")
DEFAULT_COOLDOWN = int(os.environ.get("DEFAULT_COOLDOWN_SECONDS", "60"))
MAX_RETRIES = int(os.environ.get("MAX_FAILOVER_RETRIES", "4"))
DB_PATH = os.environ.get("SQLITE_DB_PATH", str(app_dir / "data" / "free_llm_proxy.db"))
STRATA_BASE_URL = os.environ.get("STRATA_BASE_URL", "http://localhost:8080/v1")
ENABLE_STRATA = os.environ.get("ENABLE_STRATA", "true").lower() not in {
    "0",
    "false",
    "no",
}


def load_providers_config() -> dict:
    """Loads provider definitions and virtual alias rules from providers.json."""
    config_file = app_dir / "providers.json"
    if not config_file.exists():
        return {"providers": {}, "virtual_aliases": {}}
    with open(config_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Apply environment overrides for Strata
    providers = data.get("providers", {})
    if "strata" in providers:
        if not ENABLE_STRATA:
            del providers["strata"]
        elif STRATA_BASE_URL:
            providers["strata"]["base_url"] = STRATA_BASE_URL

    return data


def get_provider_key(env_key: str | None) -> str | None:
    """Retrieves provider key from environment if defined."""
    if not env_key:
        return None
    val = os.environ.get(env_key)
    if val and val.strip() and not val.startswith("your-"):
        return val.strip()
    return None
