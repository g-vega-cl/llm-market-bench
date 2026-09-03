"""Gmail newsletter ingestion and processing.

This module handles fetching newsletters from Gmail, parsing email content,
and transforming them into structured snapshots for database storage.
"""

import asyncio
import base64
import contextlib
import email
import hashlib
import imaplib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Any

from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from core.config import (
    GMAIL_APP_PASSWORD,
    GMAIL_CREDENTIALS_JSON,
    GMAIL_EMAIL,
    GMAIL_SCOPES,
    GMAIL_TOKEN_JSON,
    NEWSLETTER_SENDERS,
    NO_CONTENT_FOUND,
    logger,
)
from ingest.cleaner import clean_newsletter_content


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


def _parse_json_secret(secret_str: str | None, var_name: str) -> dict[str, Any] | None:
    """Safely parse a JSON secret string from environment variables.

    Handles unescaped control characters (newlines, tabs) and outer wrapping quotes.

    Args:
        secret_str: Raw JSON string from environment.
        var_name: Name of the environment variable for diagnostic logging.

    Returns:
        Parsed dictionary or None if parsing failed.
    """
    if not secret_str or not isinstance(secret_str, str):
        return None

    cleaned = secret_str.strip()
    if cleaned.startswith("'") and cleaned.endswith("'") and len(cleaned) >= 2:
        cleaned = cleaned[1:-1].strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
        logger.error(f"AUTHENTICATION FAILURE: {var_name} parsed to {type(data).__name__}, expected dict.")
        return None
    except json.JSONDecodeError:
        try:
            data = json.loads(cleaned, strict=False)
            if isinstance(data, dict):
                return data
            logger.error(f"AUTHENTICATION FAILURE: {var_name} parsed to {type(data).__name__}, expected dict.")
            return None
        except Exception as e:
            logger.error(f"AUTHENTICATION FAILURE: Error parsing {var_name}: {e}")
            return None
    except Exception as e:
        logger.error(f"AUTHENTICATION FAILURE: Error parsing {var_name}: {e}")
        return None


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
        secret_data = _parse_json_secret(GMAIL_CREDENTIALS_JSON, "GMAIL_CREDENTIALS_JSON")
        token_data = _parse_json_secret(GMAIL_TOKEN_JSON, "GMAIL_TOKEN_JSON")

        if secret_data and token_data:
            try:
                secrets = secret_data.get("installed") or secret_data.get("web") or secret_data
                client_id = secrets.get("client_id")
                client_secret = secrets.get("client_secret")

                if not client_id or not client_secret:
                    logger.error(
                        "NO VALID GMAIL CREDENTIALS: Missing client_id or client_secret in GMAIL_CREDENTIALS_JSON."
                    )
                else:
                    creds = Credentials(
                        token=token_data.get("token"),
                        refresh_token=token_data.get("refresh_token"),
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=client_id,
                        client_secret=client_secret,
                        scopes=token_data.get("scopes", GMAIL_SCOPES),
                    )
            except Exception as e:
                logger.error(f"AUTHENTICATION FAILURE: Error creating Credentials object: {e}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"TOKEN REFRESH FAILURE: Could not refresh Google token: {e}")
                creds = None

        if not creds:
            logger.error("NO VALID GMAIL CREDENTIALS: Manual re-authentication required or check GMAIL_TOKEN_JSON.")
            return None

    try:
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
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
                elif mime_type == "text/html" and len(decoded) > len(collected["html"]):
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


def decode_mime_header(header_value: str | None) -> str:
    """Decode an RFC 2047 encoded MIME header or return plain text.

    Args:
        header_value: Raw header string.

    Returns:
        Decoded human-readable string.
    """
    if not header_value:
        return ""
    try:
        decoded_fragments = decode_header(header_value)
        result = []
        for fragment, charset in decoded_fragments:
            if isinstance(fragment, bytes):
                result.append(fragment.decode(charset or "utf-8", errors="replace"))
            else:
                result.append(str(fragment))
        return "".join(result)
    except Exception:
        return str(header_value)


def extract_email_message_body(msg: Any) -> str:
    """Extract plain text or HTML body from a standard email.message.Message.

    Args:
        msg: Parsed email.message.Message object.

    Returns:
        Cleaned body text or NO_CONTENT_FOUND.
    """
    plain_parts: list[str] = []
    html_parts: list[str] = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in content_disposition:
                continue
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            charset = part.get_content_charset() or "utf-8"
            decoded_text = payload.decode(charset, errors="replace")
            if content_type == "text/plain":
                plain_parts.append(decoded_text)
            elif content_type == "text/html":
                html_parts.append(decoded_text)
    else:
        content_type = msg.get_content_type()
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            decoded_text = payload.decode(charset, errors="replace")
            if content_type == "text/plain":
                plain_parts.append(decoded_text)
            elif content_type == "text/html":
                html_parts.append(decoded_text)

    plain_text = "\n".join(plain_parts)
    html_text = "\n".join(html_parts)

    if plain_text and "click here to read it in full" not in plain_text.lower():
        return clean_text(plain_text)
    if html_text:
        return html_to_readable_text(html_text)
    return clean_text(plain_text) or NO_CONTENT_FOUND


def _fetch_raw_messages_imap(
    email_address: str, app_password: str, newer_than_days: int = 1
) -> list[tuple[NewsletterSnapshot, str]]:
    """Fetch newsletters from Gmail using IMAP with an App Password.

    Args:
        email_address: Gmail account email address.
        app_password: 16-character Google App Password.
        newer_than_days: Only fetch emails from the last N days.

    Returns:
        List of tuples: (NewsletterSnapshot, sender).
    """
    clean_pwd = app_password.replace(" ", "")
    sender_filter = " OR ".join(NEWSLETTER_SENDERS)
    query = f"from:({sender_filter}) newer_than:{newer_than_days}d"
    logger.info(f"Fetching newsletters via IMAP with query: {query}")

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    except Exception:
        logger.exception("Failed to connect to imap.gmail.com:993 via SSL")
        return []

    try:
        mail.login(email_address, clean_pwd)
        mail.select("INBOX", readonly=True)

        status, data = mail.search(None, f'X-GM-RAW "{query}"')
        if status != "OK" or not data or not data[0]:
            logger.info("No messages found matching query via IMAP.")
            return []

        msg_ids = data[0].split()
        logger.info(f"Found {len(msg_ids)} messages via IMAP. Starting download...")

        raw_snapshots: list[tuple[NewsletterSnapshot, str]] = []
        for msg_id_bytes in msg_ids:
            msg_id = msg_id_bytes.decode() if isinstance(msg_id_bytes, bytes) else str(msg_id_bytes)
            try:
                res, msg_data = mail.fetch(msg_id_bytes, "(RFC822)")
                if res != "OK" or not msg_data or not msg_data[0] or not isinstance(msg_data[0], tuple):
                    continue
                raw_bytes = msg_data[0][1]
                msg = email.message_from_bytes(raw_bytes)

                subject = decode_mime_header(msg.get("Subject", "No Subject"))
                sender = decode_mime_header(msg.get("From", "Unknown"))
                raw_date = msg.get("Date")

                try:
                    date_dt = parsedate_to_datetime(raw_date)
                    date = date_dt.isoformat()
                except Exception:
                    date = datetime.now().isoformat()

                body = extract_email_message_body(msg)

                snapshot = NewsletterSnapshot(
                    source_id=generate_source_id(date, sender, subject),
                    chunk_hash=generate_chunk_hash(body),
                    sender=sender,
                    date=date,
                    subject=subject,
                    content=body,
                    ingested_at=datetime.now().isoformat(),
                )
                raw_snapshots.append((snapshot, sender))
            except Exception:
                logger.exception(f"Error parsing IMAP message {msg_id}")

        return raw_snapshots
    except Exception:
        logger.exception("An error occurred during IMAP newsletter retrieval")
        return []
    finally:
        with contextlib.suppress(Exception):
            mail.close()
        with contextlib.suppress(Exception):
            mail.logout()


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


async def _fetch_raw_message(
    service: Any, msg_ref: dict[str, str], lock: asyncio.Lock | None = None
) -> tuple[NewsletterSnapshot | None, str | None]:
    """Fetch a single message from Gmail and build a raw snapshot without cleaning.

    Args:
        service: Gmail API service resource.
        msg_ref: Dictionary containing the message 'id'.
        lock: Optional asyncio.Lock to serialize calls on thread-unsafe service resource.

    Returns:
        A tuple of (NewsletterSnapshot or None, sender_string or None).
    """
    sender = None
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            if lock:
                async with lock:
                    msg = await asyncio.to_thread(
                        service.users().messages().get(userId="me", id=msg_ref["id"], format="full").execute
                    )
            else:
                msg = await asyncio.to_thread(
                    service.users().messages().get(userId="me", id=msg_ref["id"], format="full").execute
                )

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
            ), sender
        except Exception as e:
            if attempt < max_attempts:
                logger.warning(
                    f"Attempt {attempt}/{max_attempts} failed fetching raw message {msg_ref.get('id')}: {e}. Retrying in {attempt * 0.5}s..."
                )
                await asyncio.sleep(attempt * 0.5)
            else:
                logger.error(f"Error fetching raw message {msg_ref.get('id')} after {max_attempts} attempts: {e}")
                return None, sender
    return None, sender


async def _process_message(service: Any, msg_ref: dict[str, str]) -> tuple[NewsletterSnapshot | None, str | None]:
    """Fetch a single message and transform it into a NewsletterSnapshot.

    Args:
        service: Gmail API service resource.
        msg_ref: Dictionary containing the message 'id'.

    Returns:
        A tuple of (NewsletterSnapshot or None, sender_string or None).
    """
    sender = None
    try:
        msg = service.users().messages().get(userId="me", id=msg_ref["id"], format="full").execute()
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

        # --- De-advertisement Pass ---
        cleaned_body = await clean_newsletter_content(body)

        return NewsletterSnapshot(
            source_id=generate_source_id(date, sender, subject),
            chunk_hash=generate_chunk_hash(cleaned_body),
            sender=sender,
            date=date,
            subject=subject,
            content=cleaned_body,
            ingested_at=datetime.now().isoformat(),
        ), sender
    except Exception as e:
        logger.error(f"Error processing message {msg_ref.get('id')}: {e}")
        return None, sender


async def ingest_newsletters(newer_than_days: int = 1) -> list[dict[str, Any]]:
    """Fetch and process newsletters from Gmail.

    Prefers IMAP via GMAIL_APP_PASSWORD and GMAIL_EMAIL when set.
    Falls back to Google OAuth REST API if GMAIL_TOKEN_JSON is provided.

    Args:
        newer_than_days: Only fetch emails from the last N days.

    Returns:
        List of newsletter snapshots as dictionaries.
    """
    raw_results: list[tuple[NewsletterSnapshot, str]] = []
    attempted_senders: set[str] = set()

    if GMAIL_APP_PASSWORD and GMAIL_EMAIL:
        logger.info("Using Gmail IMAP with App Password for newsletter ingestion...")
        raw_results = await asyncio.to_thread(
            _fetch_raw_messages_imap, GMAIL_EMAIL, GMAIL_APP_PASSWORD, newer_than_days
        )
        if not raw_results:
            logger.info("No messages were retrieved via IMAP.")
            return []
        attempted_senders = {sender for _, sender in raw_results if sender}
    else:
        service = get_gmail_service()
        if not service:
            return []

        sender_filter = " OR ".join(NEWSLETTER_SENDERS)
        query = f"from:({sender_filter}) newer_than:{newer_than_days}d"
        logger.info(f"Fetching newsletters with query: {query}")

        max_query_attempts = 3
        messages = []
        for attempt in range(1, max_query_attempts + 1):
            try:
                results = await asyncio.to_thread(
                    service.users().messages().list(userId="me", q=query, maxResults=20).execute
                )
                messages = results.get("messages", [])
                break
            except Exception as error:
                if attempt < max_query_attempts:
                    wait_seconds = attempt * 1.5
                    logger.warning(
                        f"Attempt {attempt}/{max_query_attempts} failed querying Gmail messages: {error}. "
                        f"Retrying in {wait_seconds}s..."
                    )
                    await asyncio.sleep(wait_seconds)
                else:
                    logger.error(f"An error occurred fetching from Gmail after {max_query_attempts} attempts: {error}")
                    return []

        if not messages:
            logger.info(
                f"No messages found matching query. "
                f"Senders checked: {len(NEWSLETTER_SENDERS)}, "
                f"Time window: {newer_than_days} day(s)."
            )
            return []

        logger.info(f"Found {len(messages)} messages. Starting processing...")

        # Phase 1: Fetch all raw message bodies (Gmail API calls locked to protect thread-unsafe service)
        lock = asyncio.Lock()
        fetch_tasks = [_fetch_raw_message(service, msg_ref, lock=lock) for msg_ref in messages]
        fetch_results = await asyncio.gather(*fetch_tasks)

        for raw_snapshot, sender in fetch_results:
            if sender:
                attempted_senders.add(sender)
            if raw_snapshot:
                raw_results.append((raw_snapshot, sender))

    try:
        # Phase 2: Clean all bodies in parallel via LLM
        snapshots = []
        if raw_results:
            cleaning_tasks = [clean_newsletter_content(snapshot.content) for snapshot, _ in raw_results]
            cleaned_bodies = await asyncio.gather(*cleaning_tasks, return_exceptions=True)

            # Phase 3: Assemble cleaned snapshots
            for (raw_snapshot, sender), cleaned_body in zip(raw_results, cleaned_bodies, strict=True):
                if isinstance(cleaned_body, Exception):
                    logger.error(f"Cleaning failed for {sender}: {cleaned_body}. Using raw body.")
                    cleaned_body = raw_snapshot.content
                raw_snapshot.content = cleaned_body
                raw_snapshot.chunk_hash = generate_chunk_hash(cleaned_body)
                snapshots.append(asdict(raw_snapshot))

        # Summarize results by sender
        sender_counts = Counter(s["sender"] for s in snapshots)

        # --- Semantic Fragility Monitoring ---
        # Detect if any sender found in today's messages failed to produce a snapshot
        # This indicates a template change or parsing error.
        for attempted_sender in attempted_senders:
            # Check if this attempted sender resulted in any snapshot
            found = any(attempted_sender.lower() in s["sender"].lower() for s in snapshots)
            if not found:
                logger.warning(
                    f"SEMANTIC FRAGILITY ALERT: Found message(s) from '{attempted_sender}' "
                    f"but yielded 0 valid snapshots. Check if the newsletter template has changed!"
                )

        if snapshots:
            stats = ", ".join([f"{count} from {sender}" for sender, count in sender_counts.items()])
            logger.info(f"Successfully ingested {len(snapshots)} newsletters: {stats}")
        else:
            logger.info("No messages were successfully processed into snapshots.")

        return snapshots
    except HttpError as error:
        logger.error(f"An error occurred fetching from Gmail: {error}")
        return []
