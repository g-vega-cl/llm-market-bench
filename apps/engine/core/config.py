"""Configuration and environment setup for the AI Wall Street Engine.

This module loads environment variables, configures logging, and defines
constants used throughout the application.
"""

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

# Load environment variables
load_dotenv(dotenv_path=ENV_PATH)

# --- Logging Configuration ---
LOG_FORMAT = "[%(asctime)s] %(levelname)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("engine")

# --- Supabase Configuration ---
SUPABASE_URL = os.getenv("SUPABASE_PROJECT_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# --- LLM API Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
MIMO_API_KEY = os.getenv("MIMO_API_KEY")

# --- Model Selection ---
# Loaded from the shared packages/config/models.json — the single source of truth.
# To change a model, edit that JSON file. Both Python and TypeScript read from it.
_MODELS_JSON = Path(__file__).resolve().parent.parent.parent.parent / "packages" / "config" / "models.json"
with open(_MODELS_JSON) as _f:
    _models = json.load(_f)

OPENAI_MODEL: str = _models["OPENAI_MODEL"]
ANTHROPIC_MODEL: str = _models["ANTHROPIC_MODEL"]
GEMINI_MODEL: str = _models["GEMINI_MODEL"]
DEEPSEEK_MODEL: str = _models["DEEPSEEK_MODEL"]
XIAOMI_MODEL: str = _models["XIAOMI_MODEL"]
CONTRARIAN_AGENT_ID: str = _models["CONTRARIAN_AGENT_ID"]
ACTIVE_OWNER_IDS: list[str] = list(_models.values())

# Weights for consensus protocol (higher = more influence)
MODEL_WEIGHTS = {
    OPENAI_MODEL: 1.0,
    ANTHROPIC_MODEL: 1.0,
    GEMINI_MODEL: 1.0,
    DEEPSEEK_MODEL: 1.0,
    XIAOMI_MODEL: 1.0,
}

# --- Gmail Configuration ---
GMAIL_CREDENTIALS_JSON = os.getenv("GMAIL_CREDENTIALS_JSON")
GMAIL_TOKEN_JSON = os.getenv("GMAIL_TOKEN_JSON")
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# --- Newsletter Configuration ---
NEWSLETTER_SENDERS = [
    "no-reply@connect.etoro.com",
    "crew@morningbrew.com",
    "notifications@e-news.wealthsimple.com",
    "squad@thedailyupside.com",
    "noreply@news.bloomberg.com",
    "newsletter+211@tradingcentral.com",
    "daily@chartr.co",
    "brewmarkets@morningbrew.com",
    "contact@stockanalysis.com",
    "themacrocompass@substack.com"
]
# --- Memory Retention & Decay (Step 15+) ---
MEMORIES_RELEVANCE_DECAY_HALF_LIFE_DAYS = 30  # Memories lose 50% relevance every 30 days
MEMORIES_DECAY_THRESHOLD = 0.05  # Stop decaying if relevance drops below this

# --- Commands ---
COMMAND_INGEST = "ingest"
COMMAND_POST_ANALYSIS = "post-analysis"
COMMAND_GOVERNMENT = "government"
COMMAND_CALENDAR = "calendar"
COMMAND_CAUSE_AND_EFFECT = "analyze-impact"

# --- Content Constants ---
NO_CONTENT_FOUND = "No content found"

# --- Momentum Analysis Configuration ---
MOMENTUM_SIMILARITY_THRESHOLD = 0.75
MOMENTUM_BASELINE_DAYS = 30
MOMENTUM_EXTENDED_WINDOW_DAYS = 90
MOMENTUM_CONCEPT_MERGE_THRESHOLD = 0.75
MOMENTUM_DECAY_HALF_LIFE_DAYS = 28  # Velocity halves every 14 days of inactivity

# --- Financial Data Configuration ---
FMP_API_KEY = os.getenv("FMP_API_KEY")
FINANCIAL_PROVIDER = os.getenv("FINANCIAL_PROVIDER", "ibkr_proxy")
FALLBACK_FINANCIAL_PROVIDER = os.getenv("FALLBACK_FINANCIAL_PROVIDER", "fmp")
SECOND_FALLBACK_FINANCIAL_PROVIDER = os.getenv("SECOND_FALLBACK_FINANCIAL_PROVIDER", "yfinance")

# --- Validation Guardrails ---
MIN_MARKET_CAP_BILLIONS = 2.0
MAX_PRICE_DEVIATION_PCT = 5.0
MIN_TRADE_VALUE = 1000.0  # Minimum purchase/sell value for LLM-driven trades
FINANCIAL_API_THROTTLE_SECONDS = float(os.getenv("FINANCIAL_API_THROTTLE_SECONDS", 2.0))
MARKET_DATA_CACHE_TTL_SECONDS = int(os.getenv("MARKET_DATA_CACHE_TTL_SECONDS", 2))
MARKET_DATA_RETRIES = int(os.getenv("MARKET_DATA_RETRIES", 2))

# --- IBKR Configuration ---
IBKR_HOST = os.getenv("IBKR_HOST", "127.0.0.1")
IBKR_PORT = int(os.getenv("IBKR_PORT", "7496"))
IBKR_CLIENT_ID = int(os.getenv("IBKR_CLIENT_ID", "1"))

# --- IBKR Proxy Configuration ---
IBKR_PROXY_URL = os.getenv("IBKR_PROXY_URL")
# The engine will use this service role key to sign a JWT for the proxy
# unless a specific IBKR_PROXY_TOKEN is provided.
IBKR_PROXY_TOKEN = os.getenv("IBKR_PROXY_TOKEN")

# --- Web Search Configuration ---
# Enable web search grounding for LLM agents
ENABLE_ANTHROPIC_WEB_SEARCH = os.getenv("ENABLE_ANTHROPIC_WEB_SEARCH", "true").lower() == "true"
ENABLE_GEMINI_WEB_SEARCH = os.getenv("ENABLE_GEMINI_WEB_SEARCH", "true").lower() == "true"
ENABLE_OPENAI_WEB_SEARCH = os.getenv("ENABLE_OPENAI_WEB_SEARCH", "false").lower() == "true"  # Limited support in Chat API

# Anthropic web search tool version
# Use 'web_search_20250305' for ZDR compliance, 'web_search_20260209' for dynamic filtering
ANTHROPIC_WEB_SEARCH_VERSION = os.getenv("ANTHROPIC_WEB_SEARCH_VERSION", "web_search_20250305")

# Maximum web searches per request
ANTHROPIC_MAX_WEB_SEARCHES = int(os.getenv("ANTHROPIC_MAX_WEB_SEARCHES", "3"))
