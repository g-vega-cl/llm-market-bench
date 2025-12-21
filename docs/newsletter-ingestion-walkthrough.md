# Walkthrough: Newsletter Ingestion (Step 2)

This document covers the implementation and verification of the Newsletter Ingestion phase (Step 2) of the AI Wall Street Engine.

## Component Overview

The Newsletter Ingestion component is responsible for retrieving unread financial newsletters from Gmail, extracting their content, and preparing them for the downstream consensus and attribution engine.

### Key Features

*   **Gmail API Integration**: Securely fetches emails from specific investment-related senders.
*   **Content Extraction**:
    *   Handles both `text/plain` and `text/html` formats.
    *   Cleans and normalizes text (removing non-ASCII characters, collapsing whitespace).
    *   Converts HTML to readable text using `BeautifulSoup4`.
*   **Attribution Groundwork**:
    *   **`SourceID`**: A unique identifier for each newsletter (e.g., `news_sender_hash`).
    *   **`ChunkHash`**: A SHA-256 fingerprint of the content for auditability.

---

## Implementation Details

### Directory Structure

The engine is located in `apps/engine/`:

```text
llm-market-bench/
├── .env                  # (Not versioned) Stores credentials
└── apps/
    └── engine/
        ├── main.py       # Pipeline entry point
        ├── requirements.txt
        ├── venv/         # Virtual environment
        └── ingest/
            └── newsletter.py  # Ingestion logic
```

### Core Logic: `newsletter.py`

The logic in [newsletter.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/ingest/newsletter.py) follows these steps:
1.  **Authentication**: Loads Gmail credentials and tokens from environment variables (`GMAIL_CREDENTIALS_JSON`, `GMAIL_TOKEN_JSON`).
2.  **Filtering**: Queries for emails from trusted senders (Morning Brew, Daily Upside, etc.) received in the last 24 hours.
3.  **Extraction**: Extracts the best available text version of the email body.
4.  **Hashing**: Generates the `source_id` and `chunk_hash`.

### Execution: `main.py`

The engine can be triggered using the following command:

```bash
python main.py ingest
```

---

## Verification Results

### Success Criteria
- [x] Successfully authenticates with Gmail using environment variables.
- [x] Fetches newsletters from the specified senders.
- [x] Correctly extracts and cleans newsletter content.
- [x] Generates unique `SourceID` and `ChunkHash` for each entry.

### Sample Output

When running `python main.py ingest`, the engine produces a JSON structure similar to this:

```json
{
  "source_id": "news_squad_thedailyupside_com_9253e05a",
  "chunk_hash": "6f80829788e176b189ef2aa8186b1deaef754cb3ad0922dd6c3d37138b846a37",
  "sender": "The Daily Upside <squad@thedailyupside.com>",
  "date": "Mon, 22 Dec 2025 03:03:55 +1100",
  "subject": "Generational Wealth of Their Own",
  "content": "December 21, 2025\nPRESENTED BY FISHER INVESTMENTS...\n",
  "ingested_at": "2025-12-21T13:55:25.098895"
}
```

## Environment Configuration

Dependencies are listed in [requirements.txt](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/requirements.txt):
*   `google-api-python-client`
*   `google-auth-oauthlib`
*   `beautifulsoup4`
*   `python-dotenv`
