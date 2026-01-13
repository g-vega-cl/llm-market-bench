"""Configuration and environment setup for the AI Wall Street Engine.

This module loads environment variables, configures logging, and defines
constants used throughout the application.
"""

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

# --- Model Selection ---
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")

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
]

# --- Commands ---
COMMAND_INGEST = "ingest"

# --- Content Constants ---
NO_CONTENT_FOUND = "No content found"

# --- Momentum Analysis Configuration ---
MOMENTUM_SIMILARITY_THRESHOLD = 0.85
MOMENTUM_BASELINE_DAYS = 7
MOMENTUM_EXTENDED_WINDOW_DAYS = 90
MOMENTUM_CONCEPT_MERGE_THRESHOLD = 0.90
MOMENTUM_DECAY_HALF_LIFE_DAYS = 28  # Velocity halves every 14 days of inactivity
