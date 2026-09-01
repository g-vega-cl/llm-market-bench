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
LOG_FORMAT = "[%(asctime)s] [%(name)s] %(levelname)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("engine")

# --- Supabase Configuration ---
SUPABASE_URL = os.getenv("SUPABASE_PROJECT_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# --- LLM API Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")

# --- Model Selection ---
# Loaded from the shared packages/config/models.json — the single source of truth.
# To change a model, edit that JSON file. Both Python and TypeScript read from it.
_MODELS_JSON = Path(__file__).resolve().parent.parent.parent.parent / "packages" / "config" / "models.json"
with open(_MODELS_JSON) as _f:
    _models = json.load(_f)

OPENAI_MODEL: str = _models["OPENAI_MODEL"]
ANTHROPIC_MODEL: str = _models["ANTHROPIC_MODEL"]
GEMINI_MODEL: str = _models["GEMINI_MODEL"]
GEMINI_EMBEDDING_MODEL: str = _models["GEMINI_EMBEDDING_MODEL"]
DEEPSEEK_MODEL: str = _models["DEEPSEEK_MODEL"]
DEEPSEEK_FLASH_MODEL: str = _models["DEEPSEEK_FLASH_MODEL"]
MINIMAX_MODEL: str = _models["MINIMAX_MODEL"]
AUTORESEARCH_EXPERIMENT_OWNER_IDS: list[str] = _models.get("AUTORESEARCH_EXPERIMENT_OWNER_IDS", [])
AUTORESEARCH_TRACKS: dict[str, list[str]] = _models.get("AUTORESEARCH_TRACKS", {})
ACTIVE_OWNER_IDS: list[str] = list(_models.values())

# Weights for consensus protocol (higher = more influence)
# Explicitly covers all models in packages/config/models.json — see P1 fix
MODEL_WEIGHTS = {
    OPENAI_MODEL: 1.0,
    ANTHROPIC_MODEL: 1.0,
    GEMINI_MODEL: 1.0,
    DEEPSEEK_MODEL: 1.0,
    DEEPSEEK_FLASH_MODEL: 1.0,
    MINIMAX_MODEL: 1.0,
}

# Guard: ensure every active model has a weight entry
assert MINIMAX_MODEL in MODEL_WEIGHTS, "MODEL_WEIGHTS missing MINIMAX_MODEL"
assert DEEPSEEK_FLASH_MODEL in MODEL_WEIGHTS, "MODEL_WEIGHTS missing DEEPSEEK_FLASH_MODEL"

# Dedup threshold for memory promotion — decoupled from semantic grouping (0.75)
# Using 0.90 prevents false collisions like Sim 0.77 (Gas Pipeline vs AI Chips) seen 2026-08-27
MEMORY_DEDUP_THRESHOLD = 0.90

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
    "themacrocompass@substack.com",
    "markets@axios.com",
    "calculatedrisk@substack.com",
    "macro@axios.com",
    "techbrew@morningbrew.com",
    "closer@axios.com",
    "ftav@substack.com",
    "thebearcave@substack.com",
    "ideabrunch@substack.com",
    "william@puck.new",
    "hello@snacks.robinhood.com",
    "netinterest@substack.com",
    "newsletter@investingmail.com",
    "email@stratechery.com",
    "puck@puck.news",
]
# --- Memory Retention & Decay (Step 15+) ---
MEMORIES_RELEVANCE_DECAY_HALF_LIFE_DAYS = 30  # Memories lose 50% relevance every 30 days
MEMORIES_DECAY_THRESHOLD = 0.05  # Stop decaying if relevance drops below this

# --- Commands ---
COMMAND_INGEST = "ingest"
COMMAND_WEEKEND_INGEST = "weekend-ingest"
COMMAND_POST_ANALYSIS = "post-analysis"
COMMAND_GOVERNMENT = "government"
COMMAND_CALENDAR = "calendar"
COMMAND_CAUSE_AND_EFFECT = "analyze-impact"
COMMAND_AUDIT = "audit"
COMMAND_AUTORESEARCH = "autoresearch"
COMMAND_BOOTSTRAP_AUTORESEARCH = "bootstrap-autoresearch"
COMMAND_CLEANUP = "cleanup"
COMMAND_DAILY_PREDICTOR = "daily-predictor"
COMMAND_EVALUATE_DAILY_PREDICTIONS = "evaluate-daily-predictions"
COMMAND_DAILY_AUTORESEARCH = "daily-autoresearch"
COMMAND_BACKTEST_DAILY_AUTORESEARCH = "backtest-daily-autoresearch"
COMMAND_SEED_DAILY_PREDICTOR = "seed-daily-predictor"
COMMAND_GENERATE_NEWSLETTER = "generate-newsletter"
COMMAND_LIN_RENKO = "lin-renko"
COMMAND_AUDIT_ALPACA = "audit-alpaca"

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
FRED_API_KEY = os.getenv("FRED_API_KEY", "")
FRED_CACHE_TTL_HOURS = int(os.getenv("FRED_CACHE_TTL_HOURS", 12))
MASSIVE_API_KEY = os.getenv("MASSIVE_API_KEY") or os.getenv("POLYGON_API_KEY", "")
MASSIVE_BASE_URL = os.getenv("MASSIVE_BASE_URL", "https://api.polygon.io").rstrip("/")
OPTIONS_CACHE_TTL_SECONDS = int(os.getenv("OPTIONS_CACHE_TTL_SECONDS", 3600))  # 1 hour default
FINANCIAL_PROVIDER = os.getenv("FINANCIAL_PROVIDER", "fmp")

# --- Validation Guardrails ---
MIN_MARKET_CAP_BILLIONS = 2.0
MAX_PRICE_DEVIATION_PCT = 5.0
MIN_TRADE_VALUE = 1000.0  # Minimum purchase/sell value for LLM-driven trades
FINANCIAL_API_THROTTLE_SECONDS = 0.2
MARKET_DATA_CACHE_TTL_SECONDS = int(
    os.getenv("MARKET_DATA_CACHE_TTL_SECONDS", 300)
)  # Default 5-minute cache TTL for market data
MARKET_DATA_RETRIES = int(os.getenv("MARKET_DATA_RETRIES", 2))

# --- Alpaca Paper Trading Configuration ---
# Enable web search grounding for LLM agents
ENABLE_ANTHROPIC_WEB_SEARCH = os.getenv("ENABLE_ANTHROPIC_WEB_SEARCH", "true").lower() == "true"
ENABLE_GEMINI_WEB_SEARCH = os.getenv("ENABLE_GEMINI_WEB_SEARCH", "true").lower() == "true"
ENABLE_OPENAI_WEB_SEARCH = (
    os.getenv("ENABLE_OPENAI_WEB_SEARCH", "false").lower() == "true"
)  # Limited support in Chat API
ENABLE_DEEPSEEK_WEB_SEARCH = os.getenv("ENABLE_DEEPSEEK_WEB_SEARCH", "true").lower() == "true"

# Anthropic web search tool version
# Use 'web_search_20250305' for ZDR compliance, 'web_search_20260209' for dynamic filtering
ANTHROPIC_WEB_SEARCH_VERSION = os.getenv("ANTHROPIC_WEB_SEARCH_VERSION", "web_search_20250305")

# Maximum web searches per request
ANTHROPIC_MAX_WEB_SEARCHES = int(os.getenv("ANTHROPIC_MAX_WEB_SEARCHES", "3"))

# MiniMax Anthropic-format base URL (M3 supports both OpenAI- and Anthropic-compatible endpoints).
# Default per https://platform.minimax.io/docs/api-reference/text-anthropic-api.md
MINIMAX_ANTHROPIC_BASE_URL = os.getenv("MINIMAX_ANTHROPIC_BASE_URL", "https://api.minimax.io/anthropic")

# --- Auto-Research Configuration ---
# Model used for the weekly meta-evaluation (prompt improvement).
# Defaults to DeepSeek Flash; override via AUTORESEARCH_MODEL env var.
AUTORESEARCH_MODEL = os.getenv("AUTORESEARCH_MODEL", DEEPSEEK_FLASH_MODEL)

# Which agent portfolios receive auto-researched prompts (experiment group).
# The remaining agents use the hardcoded baseline prompt (control group).
AUTORESEARCH_EXPERIMENT_OWNER_IDS = frozenset(_models.get("AUTORESEARCH_EXPERIMENT_OWNER_IDS", []))

# Auto-research multi-track mappings (track_id -> list of owner_ids)
AUTORESEARCH_TRACKS = dict(_models.get("AUTORESEARCH_TRACKS", {}))

# Auto-research track meta-evaluator LLM models (track_id -> model_name)
AUTORESEARCH_TRACK_MODELS = dict(
    _models.get(
        "AUTORESEARCH_TRACK_MODELS",
        {
            "track_default": DEEPSEEK_FLASH_MODEL,
            "track_claude": DEEPSEEK_FLASH_MODEL,
            "track_openai": MINIMAX_MODEL,
        },
    )
)

# Model owner IDs that bypass the skeptical verification agent stage
SKIP_VERIFIER_OWNER_IDS = set(_models.get("SKIP_VERIFIER_OWNER_IDS", ["MiniMax-M3", "deepseek-v4-flash"]))


# --- Alpaca Paper Trading Configuration ---
# Hardcoded constant — single source of truth for the audit layer.
ALPACA_ENABLED = True
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_PAPER_ENDPOINT = "https://paper-api.alpaca.markets"  # Hardcoded — not configurable
