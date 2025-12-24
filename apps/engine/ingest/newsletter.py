import json
import base64
import re
import html
import hashlib
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from core.config import (
    GMAIL_CREDENTIALS_JSON, 
    GMAIL_TOKEN_JSON, 
    GMAIL_SCOPES, 
    NEWSLETTER_SENDERS, 
    logger
)

try:
    from bs4 import BeautifulSoup
except ImportError:
    logger.warning("BeautifulSoup not found. Falling back to regex for HTML stripping.")
    BeautifulSoup = None

@dataclass
class NewsletterSnapshot:
    """Represents a single newsletter ingestion record."""
    source_id: str
    chunk_hash: str
    sender: str
    date: str
    subject: str
    content: str
    ingested_at: str

def get_gmail_service():
    """Authenticates with Google and returns a Gmail service object."""
    if not GMAIL_CREDENTIALS_JSON:
        logger.error("GMAIL_CREDENTIALS_JSON not found in environment")
        return None

    creds = None
    if GMAIL_TOKEN_JSON:
        try:
            secret_data = json.loads(GMAIL_CREDENTIALS_JSON)
            secrets = secret_data.get('installed') or secret_data.get('web')
            token_data = json.loads(GMAIL_TOKEN_JSON)
            
            creds = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri='https://oauth2.googleapis.com/token',
                client_id=secrets['client_id'],
                client_secret=secrets['client_secret'],
                scopes=token_data.get('scopes', GMAIL_SCOPES)
            )
        except Exception as e:
            logger.error(f"AUTHENTICATION FAILURE: Error parsing GMAIL credentials or token: {e}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"TOKEN REFRESH FAILURE: Could not refresh Google token: {e}")
                creds = None
        
        if not creds:
            logger.error("NO VALID GMAIL CREDENTIALS: Manual re-authentication required or check GMAIL_TOKEN_JSON.")
            # We don't want to run_local_server in a headless environment (GitHub Actions)
            return None
            
    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except HttpError as error:
        logger.error(f'GMAIL SERVICE BUILD ERROR: {error}')
        return None

def decode_base64_url(data: str) -> str:
    return base64.urlsafe_b64decode(data + '===').decode('utf-8')

def clean_text(text: str) -> str:
    """Strips non-ASCII characters and normalizes whitespace."""
    ascii_text = ''.join(ch for ch in text if ord(ch) < 128)
    lines = [line.strip() for line in ascii_text.split('\n')]
    return '\n'.join(filter(None, lines))

def html_to_readable_text(html_content: str) -> str:
    if not html_content:
        return ""
    if BeautifulSoup is None:
        text = re.sub(r'<[^>]+>', '', html_content)
        text = html.unescape(text)
        return clean_text(text)
    
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator='\n')
    return clean_text(text)

def extract_email_body(payload: Dict[str, Any]) -> str:
    collected = {'plain': '', 'html': ''}
    def collect(part):
        if part.get('body', {}).get('data'):
            try:
                decoded = decode_base64_url(part['body']['data'])
                if part['mimeType'] == 'text/plain':
                    if len(decoded) > len(collected['plain']): collected['plain'] = decoded
                elif part['mimeType'] == 'text/html':
                    if len(decoded) > len(collected['html']): collected['html'] = decoded
            except Exception:
                pass
        if 'parts' in part:
            for sub_part in part['parts']:
                collect(sub_part)
    collect(payload)
    
    if collected['plain'] and "click here to read it in full" not in collected['plain'].lower():
        return clean_text(collected['plain'])
    if collected['html']:
        return html_to_readable_text(collected['html'])
    return clean_text(collected['plain']) or "No content found"

def generate_source_id(date_str: str, sender: str, subject: str) -> str:
    """Generates a unique SourceID based on date, sender and subject hash."""
    sender_clean = re.sub(r'[^a-zA-Z0-9]', '_', sender.split('<')[-1].split('>')[0])
    combined = f"{date_str}_{sender}_{subject}"
    h = hashlib.md5(combined.encode()).hexdigest()[:8]
    return f"news_{sender_clean}_{h}"

def generate_chunk_hash(content: str) -> str:
    """Generates a SHA-256 hash of the content."""
    return hashlib.sha256(content.encode()).hexdigest()

def _process_message(service: Any, msg_ref: Dict[str, str]) -> Optional[NewsletterSnapshot]:
    """Fetches a single message and transforms it into a NewsletterSnapshot."""
    try:
        msg = service.users().messages().get(userId='me', id=msg_ref['id'], format='full').execute()
        headers = {h['name']: h['value'] for h in msg['payload']['headers']}
        
        subject = headers.get('Subject', 'No Subject')
        sender = headers.get('From', 'Unknown')
        raw_date = headers.get('Date')
        
        try:
            date_dt = parsedate_to_datetime(raw_date)
            date = date_dt.isoformat()
        except Exception:
            date = datetime.now().isoformat()
            
        body = extract_email_body(msg['payload'])
        
        return NewsletterSnapshot(
            source_id=generate_source_id(date, sender, subject),
            chunk_hash=generate_chunk_hash(body),
            sender=sender,
            date=date,
            subject=subject,
            content=body,
            ingested_at=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error processing message {msg_ref.get('id')}: {e}")
        return None

def ingest_newsletters(newer_than_days: int = 1) -> List[Dict[str, Any]]:
    """Fetches and processes newsletters."""
    service = get_gmail_service()
    if not service:
        return []

    query = f"from:({ ' OR '.join(NEWSLETTER_SENDERS) }) newer_than:{newer_than_days}d"
    logger.info(f"Fetching newsletters with query: {query}")
    
    try:
        results = service.users().messages().list(userId='me', q=query, maxResults=20).execute()
        messages = results.get('messages', [])
        logger.info(f"Found {len(messages)} messages.")
        
        snapshots = []
        for msg_ref in messages:
            snapshot = _process_message(service, msg_ref)
            if snapshot:
                snapshots.append(asdict(snapshot))
            
        return snapshots
    except HttpError as error:
        logger.error(f'An error occurred fetching from Gmail: {error}')
        return []
