"""Configuration module for Free LLM Proxy."""

import json
import os
import socket
from pathlib import Path

from dotenv import load_dotenv

# Load .env file strictly from app directory (never inherit engine keys)
app_dir = Path(__file__).resolve().parent
load_dotenv(app_dir / ".env")

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
CLOUD_MAX_OUTPUT_TOKENS = int(os.environ.get("CLOUD_MAX_OUTPUT_TOKENS", "32768"))
# Wall clock per cloud attempt. Must stay below the tightest caller's patience so
# failover can finish inside the caller's window (live trader: 200s, engine
# instructor clients: 180s). Streaming is not bounded by this.
CLOUD_REQUEST_TIMEOUT_SECONDS = float(
    os.environ.get("CLOUD_REQUEST_TIMEOUT_SECONDS", "90.0")
)
# Never let a wall-clock timeout on a free provider buy paid-tier tokens.
PAID_TIMEOUT_GUARD = os.environ.get("PAID_TIMEOUT_GUARD", "true").lower() not in {
    "0",
    "false",
    "no",
}
# Optional global reasoning effort for the *-go aliases. Empty keeps the
# provider default (Gemini 3 = dynamic/high) instead of forcing a floor.
AUTO_GO_DEFAULT_REASONING_EFFORT = (
    os.environ.get("AUTO_GO_DEFAULT_REASONING_EFFORT", "").strip().lower()
)
# reasoning_budget_tokens (Strata-style) bands mapped onto effort levels.
REASONING_BUDGET_BANDS = ((8192, "high"), (4096, "medium"))
CONNECTOR_ID = os.environ.get("CONNECTOR_ID") or socket.gethostname()
SECURITY_ALERT_401_THRESHOLD = int(os.environ.get("SECURITY_ALERT_401_THRESHOLD", "20"))
SECURITY_ALERT_WINDOW_SECONDS = int(
    os.environ.get("SECURITY_ALERT_WINDOW_SECONDS", "300")
)


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
