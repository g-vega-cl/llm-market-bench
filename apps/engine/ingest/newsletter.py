"""Gmail newsletter ingestion and processing.

This module handles fetching newsletters from Gmail, parsing email content,
and transforming them into structured snapshots for database storage.
"""

import base64
import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from core.config import (
    GMAIL_CREDENTIALS_JSON,
    GMAIL_SCOPES,
    GMAIL_TOKEN_JSON,
    NEWSLETTER_SENDERS,
    NO_CONTENT_FOUND,
    logger,
)


@dataclass
class NewsletterSnapshot:
    """Represents a single newsletter ingestion record.

    Attributes:
        source_id: Unique identifier for the newsletter chunk.
        chunk_hash: SHA-256 hash of the content for deduplication.
        sender: Email sender address.
        date: ISO format datetime string.
        subject: Email subject line.
        content: Processed email body text.
        ingested_at: Timestamp when the snapshot was created.
    """

    source_id: str
    chunk_hash: str
    sender: str
    date: str
    subject: str
    content: str
    ingested_at: str


def get_gmail_service():
    """Authenticate with Google and return a Gmail service object.

    Returns:
        A Gmail API service resource, or None if authentication fails.
    """
    if not GMAIL_CREDENTIALS_JSON:
        logger.error("GMAIL_CREDENTIALS_JSON not found in environment")
        return None

    creds = None
    if GMAIL_TOKEN_JSON:
        try:
            secret_data = json.loads(GMAIL_CREDENTIALS_JSON)
            secrets = secret_data.get("installed") or secret_data.get("web")
            token_data = json.loads(GMAIL_TOKEN_JSON)

            creds = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=secrets["client_id"],
                client_secret=secrets["client_secret"],
                scopes=token_data.get("scopes", GMAIL_SCOPES),
            )
        except Exception as e:
            logger.error(
                f"AUTHENTICATION FAILURE: Error parsing GMAIL credentials or token: {e}"
            )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(
                    f"TOKEN REFRESH FAILURE: Could not refresh Google token: {e}"
                )
                creds = None

        if not creds:
            logger.error(
                "NO VALID GMAIL CREDENTIALS: Manual re-authentication required "
                "or check GMAIL_TOKEN_JSON."
            )
            return None

    try:
        service = build("gmail", "v1", credentials=creds)
        return service
    except HttpError as error:
        logger.error(f"GMAIL SERVICE BUILD ERROR: {error}")
        return None


def decode_base64_url(data: str) -> str:
    """Decode Gmail's base64url-encoded content.

    Args:
        data: Base64url-encoded string.

    Returns:
        Decoded UTF-8 string.
    """
    return base64.urlsafe_b64decode(data + "===").decode("utf-8")


def clean_text(text: str) -> str:
    """Strip non-ASCII characters and normalize whitespace.

    Args:
        text: Raw text to clean.

    Returns:
        Cleaned text with normalized whitespace and ASCII-only characters.
    """
    ascii_text = "".join(ch for ch in text if ord(ch) < 128)
    lines = [line.strip() for line in ascii_text.split("\n")]
    return "\n".join(filter(None, lines))


def html_to_readable_text(html_content: str) -> str:
    """Convert HTML content to readable plain text.

    Args:
        html_content: Raw HTML string.

    Returns:
        Cleaned plain text extracted from HTML.
    """
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    return clean_text(text)


def extract_email_body(payload: dict[str, Any]) -> str:
    """Extract and process the email body from a Gmail message payload.

    Recursively collects both plain text and HTML parts, preferring plain text
    unless it contains truncation indicators.

    Args:
        payload: Gmail message payload dictionary.

    Returns:
        Processed email body text.
    """
    collected = {"plain": "", "html": ""}

    def collect(part: dict[str, Any]) -> None:
        if part.get("body", {}).get("data"):
            try:
                decoded = decode_base64_url(part["body"]["data"])
                mime_type = part.get("mimeType", "")

                if mime_type == "text/plain":
                    if len(decoded) > len(collected["plain"]):
                        collected["plain"] = decoded
                elif mime_type == "text/html":
                    if len(decoded) > len(collected["html"]):
                        collected["html"] = decoded
            except Exception as e:
                logger.warning(f"Failed to decode email part: {e}")

        if "parts" in part:
            for sub_part in part["parts"]:
                collect(sub_part)

    collect(payload)

    # Prefer plain text unless it's truncated
    if collected["plain"] and "click here to read it in full" not in collected["plain"].lower():
        return clean_text(collected["plain"])
    if collected["html"]:
        return html_to_readable_text(collected["html"])
    return clean_text(collected["plain"]) or NO_CONTENT_FOUND


def generate_source_id(date_str: str, sender: str, subject: str) -> str:
    """Generate a unique SourceID based on date, sender, and subject.

    Args:
        date_str: ISO format date string.
        sender: Email sender address.
        subject: Email subject line.

    Returns:
        Deterministic unique identifier for the newsletter chunk.
    """
    sender_clean = re.sub(r"[^a-zA-Z0-9]", "_", sender.split("<")[-1].split(">")[0])
    combined = f"{date_str}_{sender}_{subject}"
    h = hashlib.md5(combined.encode()).hexdigest()[:8]
    return f"news_{sender_clean}_{h}"


def generate_chunk_hash(content: str) -> str:
    """Generate a SHA-256 hash of the content.

    Args:
        content: Text content to hash.

    Returns:
        Hexadecimal SHA-256 hash string.
    """
    return hashlib.sha256(content.encode()).hexdigest()


def _process_message(
    service: Any,
    msg_ref: dict[str, str]
) -> NewsletterSnapshot | None:
    """Fetch a single message and transform it into a NewsletterSnapshot.

    Args:
        service: Gmail API service resource.
        msg_ref: Dictionary containing the message 'id'.

    Returns:
        NewsletterSnapshot if successful, None otherwise.
    """
    try:
        msg = service.users().messages().get(
            userId="me",
            id=msg_ref["id"],
            format="full"
        ).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}

        subject = headers.get("Subject", "No Subject")
        sender = headers.get("From", "Unknown")
        raw_date = headers.get("Date")

        try:
            date_dt = parsedate_to_datetime(raw_date)
            date = date_dt.isoformat()
        except Exception:
            date = datetime.now().isoformat()

        body = extract_email_body(msg["payload"])

        return NewsletterSnapshot(
            source_id=generate_source_id(date, sender, subject),
            chunk_hash=generate_chunk_hash(body),
            sender=sender,
            date=date,
            subject=subject,
            content=body,
            ingested_at=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error processing message {msg_ref.get('id')}: {e}")
        return None


def ingest_newsletters(newer_than_days: int = 1) -> list[dict[str, Any]]:
    """Fetch and process newsletters from Gmail.

    Args:
        newer_than_days: Only fetch emails from the last N days.

    Returns:
        List of newsletter snapshots as dictionaries.
    """
    service = get_gmail_service()
    if not service:
        return []

    sender_filter = " OR ".join(NEWSLETTER_SENDERS)
    query = f"from:({sender_filter}) newer_than:{newer_than_days}d"
    logger.info(f"Fetching newsletters with query: {query}")

    try:
        results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=20
        ).execute()
        messages = results.get("messages", [])
        if not messages:
            logger.info("No messages found matching the query.")
            return []

        logger.info(f"Found {len(messages)} messages. Starting processing...")

        snapshots = []
        for msg_ref in messages:
            snapshot = _process_message(service, msg_ref)
            if snapshot:
                snapshots.append(asdict(snapshot))

        # Summarize results by sender
        if snapshots:
            sender_counts = Counter(s["sender"] for s in snapshots)
            stats = ", ".join(
                [f"{count} from {sender}" for sender, count in sender_counts.items()]
            )
            logger.info(f"Successfully ingested {len(snapshots)} newsletters: {stats}")
        else:
            logger.info("No messages were successfully processed into snapshots.")

        return snapshots
    except HttpError as error:
        logger.error(f"An error occurred fetching from Gmail: {error}")
        return []
