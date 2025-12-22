import os
import logging
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

# --- Gmail Configuration ---
GMAIL_CREDENTIALS_JSON = os.getenv("GMAIL_CREDENTIALS_JSON")
GMAIL_TOKEN_JSON = os.getenv("GMAIL_TOKEN_JSON")
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# --- Newsletter Configuration ---
NEWSLETTER_SENDERS = [
    'no-reply@connect.etoro.com', 
    'crew@morningbrew.com', 
    'notifications@e-news.wealthsimple.com',
    'squad@thedailyupside.com', 
    'noreply@news.bloomberg.com', 
    'newsletter+211@tradingcentral.com',
    'daily@chartr.co'
]

# --- Commands ---
COMMAND_INGEST = "ingest"
