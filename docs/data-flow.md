# Data Flow: Newsletter Ingestion to Trading Decisions

This document provides a detailed step-by-step walkthrough of the complete data pipeline, from fetching newsletters via Gmail to generating LLM-based trading decisions and storing them with full attribution.

## Overview

The pipeline has four main phases:

1. **Ingestion**: Fetch newsletters from Gmail, clean them, generate unique identifiers
2. **Context Retrieval**: Embed queries and retrieve historical context from vector store
3. **LLM Analysis**: Send enriched prompts to 4 LLM providers in parallel
4. **Attribution**: Save decisions with complete traceability back to source

---

## Example: Processing 4 Newsletters

### Input Data

```
Newsletter 1: "TSLA Rally Expected" (500 chars)
Newsletter 2: "Fed Rate Hike Impact" (300 chars)
Newsletter 3: "AI Boom Analysis" (450 chars)
Newsletter 4: "Crypto Crash Warning" (250 chars)
```

---

## Phase 1: Ingestion (Gmail → Supabase)

### Step 1.1: Fetch Message List from Gmail

**File**: `apps/engine/ingest/newsletter.py:293-301`

```python
# Gmail API Call #1
results = service.users().messages().list(
    userId="me",
    q="from:(newsletter1@example.com OR newsletter2@example.com OR ...)",
    newer_than:1d,
    maxResults=20
).execute()

# Returns: 4 message IDs
# [msg_id_001, msg_id_002, msg_id_003, msg_id_004]
```

**API Usage**: 1 Gmail API call to list all unread newsletters

---

### Step 1.2: Fetch and Process Each Message

**File**: `apps/engine/ingest/newsletter.py:228-272`

```
For each of the 4 message IDs:

Gmail API Call #2 (msg_id_001):
  service.users().messages().get(
    userId="me",
    id="msg_id_001",
    format="full"
  ).execute()

  Returns: Full email payload including headers and body

Message 1 Structure:
  ├─ From: newsletter1@example.com
  ├─ Date: 2024-12-25T10:00:00Z
  ├─ Subject: "TSLA Rally Expected"
  └─ Content (base64url encoded):
      <html>Tesla stock expected to rally...
      ...with 500 character HTML content...</html>

Processing Steps:
  1. Extract headers (From, Date, Subject)
  2. Parse email body with extract_email_body()
  3. Decode base64url (decode_base64_url)
  4. Parse HTML with BeautifulSoup
  5. Clean text (remove non-ASCII, normalize whitespace)

  Result: "Tesla stock expected to rally due to..."
```

**API Usage**: 4 Gmail API calls (one per message)

**Code Flow**:
- `ingest_newsletters()` calls `_process_message()` for each message ID
- `_process_message()` extracts headers, parses email body
- `extract_email_body()` handles base64 decoding and HTML parsing
- `clean_text()` normalizes the output

---

### Step 1.3: Generate Unique Identifiers

**File**: `apps/engine/ingest/newsletter.py:199-225`

For each newsletter, generate two identifiers:

#### Source ID (Deterministic Hash)

```python
def generate_source_id(date_str, sender, subject):
    """
    Combines date, sender, and subject to create unique identifier.
    Deterministic: same email always produces same source_id.
    """
    sender_clean = re.sub(r"[^a-zA-Z0-9]", "_",
                          sender.split("<")[-1].split(">")[0])
    combined = f"{date_str}_{sender}_{subject}"
    h = hashlib.md5(combined.encode()).hexdigest()[:8]
    return f"news_{sender_clean}_{h}"

# For Newsletter 1:
# Input: date="2024-12-25T10:00:00Z",
#        sender="newsletter1@example.com",
#        subject="TSLA Rally Expected"
# Output: source_id = "news_newsletter1_a7f92c4e"
```

#### Content Hash (SHA-256 Deduplication)

```python
def generate_chunk_hash(content):
    """
    SHA-256 hash of content for deduplication.
    Different content = different hash.
    """
    return hashlib.sha256(content.encode()).hexdigest()

# For Newsletter 1 content: "Tesla stock expected to rally..."
# Output: chunk_hash = "2e4ff8b5a3c2d1e9f7a4b6c8d0e1f2a3..." (64 chars)
```

**Results for all 4 newsletters**:

```
Newsletter 1:
├─ source_id: "news_newsletter1_a7f92c4e"
├─ chunk_hash: "2e4ff8b..."
├─ sender: "newsletter1@example.com"
├─ subject: "TSLA Rally Expected"
├─ date: "2024-12-25T10:00:00Z"
├─ content: "Tesla stock expected to rally due to..."
└─ ingested_at: "2024-12-26T08:30:00Z"

Newsletter 2:
├─ source_id: "news_newsletter2_b1d83f7a"
├─ chunk_hash: "5a3c21d..."
└─ ...

Newsletter 3:
├─ source_id: "news_newsletter3_c9e17b3f"
├─ chunk_hash: "7f8e91a..."
└─ ...

Newsletter 4:
├─ source_id: "news_newsletter4_d4a2c85b"
├─ chunk_hash: "3b6d45c..."
└─ ...
```

---

### Step 1.4: Save to Supabase (newsletter_snapshots table)

**File**: `apps/engine/main.py:41-55`

```python
# Database Insert #1-4 (one per newsletter)
for item in data:  # data contains 4 newsletter dicts
    upsert_newsletter_snapshot(sb_client, item)
```

**Database Schema**: `supabase/migrations/20231221000000_create_newsletters_table.sql`

```sql
CREATE TABLE newsletter_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id TEXT NOT NULL,           -- "news_newsletter1_a7f92c4e"
    chunk_hash TEXT NOT NULL,          -- "2e4ff8b..."
    sender TEXT,                       -- "newsletter1@example.com"
    subject TEXT,                      -- "TSLA Rally Expected"
    content TEXT,                      -- "Tesla stock expected..."
    date TIMESTAMP,                    -- "2024-12-25T10:00:00Z"
    ingested_at TIMESTAMP             -- "2024-12-26T08:30:00Z"
);
```

**Result in Database**:

```
newsletter_snapshots table after Phase 1:
┌────────────────────────┬──────────────────┬────────────────────────┐
│ source_id              │ content (first 50 chars) │ chunk_hash     │
├────────────────────────┼──────────────────┼────────────────────────┤
│ news_newsletter1_a7... │ Tesla stock exp... │ 2e4ff8b...             │
│ news_newsletter2_b1... │ Fed rate hike ma... │ 5a3c21d...             │
│ news_newsletter3_c9... │ AI boom creating...  │ 7f8e91a...             │
│ news_newsletter4_d4... │ Crypto market cra...  │ 3b6d45c...             │
└────────────────────────┴──────────────────┴────────────────────────┘
```

**Phase 1 Summary**:
- 5 Gmail API calls (1 list + 4 get)
- 4 database inserts
- 4 unique source_ids generated
- 4 unique chunk_hashes generated

---

## Phase 2: Context Retrieval & Embedding

### Step 2.1: Extract Query Texts

**File**: `apps/engine/analyze.py:47`

From the 4 stored newsletters, use the full content of each as queries for embedding:

```python
queries = [
    chunk.get("content", "") for chunk in chunks
    if chunk.get("content")
]

# Result:
# [
#   "Tesla stock expected to rally due to strong earnings momentum and positive sentiment across the sector. Multiple analysts predict continued upward movement through Q1 2025...",  # Query 1 (full content)
#   "Fed rate hike may trigger market volatility affecting tech stocks and growth companies. Historical precedent shows 2-3 week correction periods following policy announcements...",         # Query 2 (full content)
#   "AI boom creating unprecedented demand for semiconductor chips. NVIDIA reporting record order backlogs with 12-month lead times...",                              # Query 3 (full content)
#   "Crypto market crash warning signs emerging. Technical indicators suggest potential 30-40% correction in major cryptocurrencies..."                                           # Query 4 (full content)
# ]
```

**Why full content instead of truncated?**
- More semantic information for embeddings
- Better vector similarity matching with historical context
- Improved RAG context retrieval quality

---

### Step 2.2: BATCH Embed All Queries (Single API Call)

**File**: `apps/engine/memory/embeddings.py:27-55`

This is the KEY OPTIMIZATION: all 4 queries embedded in ONE API call, not 4 separate calls.

```python
# Gemini Embedding API Call #1 (SINGLE CALL for all 4 queries)
response = client.models.embed_content(
    model="text-embedding-004",  # 768-dimensional embeddings
    contents=[
        "Tesla stock expected to rally due to strong earnings...",      # Query 1
        "Fed rate hike may trigger market volatility...",              # Query 2
        "AI boom creating unprecedented demand...",                     # Query 3
        "Crypto market crash warning signs emerging..."                # Query 4
    ]
)

# Returns: 4 embedding vectors, each with 768 dimensions
embeddings = [
    [0.234, -0.561, 0.891, ..., 0.123],    # Embedding 1 (768 floats)
    [0.102, 0.445, -0.234, ..., 0.456],    # Embedding 2 (768 floats)
    [-0.456, 0.789, 0.123, ..., -0.789],   # Embedding 3 (768 floats)
    [0.678, -0.234, -0.456, ..., 0.234]    # Embedding 4 (768 floats)
]
```

**Why batch embeddings?**
- 1 API call instead of 4 → lower latency
- Cost efficient → bulk discount
- Still provides individual embeddings for each query

---

### Step 2.3: Query Vector Store (Retrieve Historical Context)

**File**: `apps/engine/memory/store.py:16-66`

For each of the 4 embeddings, perform a vector similarity search:

**Database Schema**: `supabase/migrations/20231224000000_enable_pgvector_and_memories.sql`

```sql
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content TEXT NOT NULL,
    embedding VECTOR(768),        -- 768-dim Gemini embeddings
    metadata JSONB,
    created_at TIMESTAMPTZ
);

-- HNSW Index for fast similarity search
CREATE INDEX memories_embedding_idx ON memories
    USING hnsw (embedding vector_cosine_ops);

-- RPC Function for vector similarity search
CREATE FUNCTION match_memories(
    query_embedding VECTOR(768),
    match_threshold FLOAT,
    match_count INT
) RETURNS TABLE (id UUID, content TEXT, metadata JSONB, similarity FLOAT) AS ...
```

**Supabase RPC Calls #1-4**:

```python
# For Embedding 1
response = client.rpc(
    "match_memories",
    {
        "query_embedding": [0.234, -0.561, 0.891, ...],  # Embedding 1
        "match_threshold": 0.5,                           # Min cosine similarity
        "match_count": 3                                  # Return top 3
    }
).execute()

# Returns: Top 3 similar memories with cosine similarity > 0.5
response.data = [
    {
        "id": "uuid1",
        "content": "Past Tesla analysis from 3 months ago demonstrated...",
        "metadata": {"source": "Tesla earnings report"},
        "similarity": 0.87
    },
    {
        "id": "uuid2",
        "content": "Bull market signal observation from previous quarter...",
        "metadata": {"source": "Technical analysis"},
        "similarity": 0.72
    },
    {
        "id": "uuid3",
        "content": "Tech rally momentum study showing positive indicators...",
        "metadata": {"source": "Market analysis"},
        "similarity": 0.65
    }
]

# For Embedding 2
response = client.rpc(...)
# Returns: Top similar memories about Fed rate hikes
# [
#   {"content": "Previous rate hike aftermath data shows...", "similarity": 0.81},
#   {"content": "Market volatility patterns during FOMC meetings...", "similarity": 0.68}
# ]

# For Embedding 3
response = client.rpc(...)
# Returns: Top similar memories about AI
# [
#   {"content": "AI infrastructure investments accelerating...", "similarity": 0.79}
# ]

# For Embedding 4
response = client.rpc(...)
# Returns: Top similar memories about Crypto
# [
#   {"content": "Crypto downturn predictions from technical analysis...", "similarity": 0.74}
# ]
```

---

### Step 2.4: Aggregate Retrieved Context

**File**: `apps/engine/analyze.py:50-51`

Combine all retrieved context into a single string:

```python
context_results = [
    "- Past Tesla analysis from 3 months ago demonstrated...\n- Bull market signal observation...\n- Tech rally momentum study...",
    "- Previous rate hike aftermath data shows...\n- Market volatility patterns...",
    "- AI infrastructure investments accelerating...",
    "- Crypto downturn predictions from technical analysis..."
]

aggregated_context = "\n".join([c for c in context_results if c])

# Result:
aggregated_context = """
- Past Tesla analysis from 3 months ago demonstrated...
- Bull market signal observation...
- Tech rally momentum study...
- Previous rate hike aftermath data shows...
- Market volatility patterns during FOMC meetings...
- AI infrastructure investments accelerating...
- Crypto downturn predictions from technical analysis...
"""
```

**Phase 2 Summary**:
- 1 Gemini Embedding API call (batch for all 4 queries)
- 4 Supabase RPC calls (vector similarity search)
- Aggregated historical context ready for LLM analysis

---

## Phase 3: LLM Analysis (Parallel Batch Calls)

### Step 3.1: Build Enriched Prompt

**File**: `apps/engine/core/llm.py:97-122`

```python
news_content = ""
for chunk in chunks:  # chunks = 4 newsletters
    news_content += f"""
---
Source ID: {chunk['source_id']}
Content: {chunk['content']}
---
"""

# news_content includes all 4 newsletters with their source_ids

prompt = f"""You are a hedge fund trading algorithm. Next you will see a batch of financial news snippets and your current portfolio (if any).
Analyze the current portfolio and the news snippets and the state of the market, find trading and investment ideas with a high profit potential.
look for relevant companies and tickers and determine a trading signal:
*BUY: Only buy if we don't already have the stock in our portfolio.
*SELL: Only sell if we have the stock in our portfolio.
*HOLD: Do not buy or sell the stock.
You must provide a confidence score (0-100) and your reasoning for each decision.
Each decision MUST include the exact 'Source ID' of the snippet that triggered it.

### Historical Context (Relevant Past Events):
{aggregated_context}

### News Batch:
---
Source ID: news_newsletter1_a7f92c4e
Content: Tesla stock expected to rally due to...
---
Source ID: news_newsletter2_b1d83f7a
Content: Fed rate hike may trigger market...
---
Source ID: news_newsletter3_c9e17b3f
Content: AI boom creating unprecedented...
---
Source ID: news_newsletter4_d4a2c85b
Content: Crypto market crash warning...
---

Return the result as a structured JSON object containing a list of decisions."""
```

**Key aspects of the prompt**:
1. All 4 newsletters sent together (batch processing)
2. Historical context injected from vector retrieval
3. Each newsletter has a Source ID for attribution
4. Instructions for trading signals (BUY/SELL/HOLD)
5. Requires confidence scores and reasoning

---

### Step 3.2: Send to 4 LLMs in Parallel

**File**: `apps/engine/analyze.py:58-75`

All 4 LLM providers are called simultaneously with the same enriched prompt:

```python
# Create 4 async tasks
tasks = [
    llm.analyze_with_provider(
        provider="openai",
        model_name="gpt-4-turbo",
        chunks=chunks,        # All 4 newsletters
        context=aggregated_context
    ),
    llm.analyze_with_provider(
        provider="anthropic",
        model_name="claude-3-5-sonnet",
        chunks=chunks,
        context=aggregated_context
    ),
    llm.analyze_with_provider(
        provider="gemini",
        model_name="gemini-2.0",
        chunks=chunks,
        context=aggregated_context
    ),
    llm.analyze_with_provider(
        provider="deepseek",
        model_name="deepseek-chat",
        chunks=chunks,
        context=aggregated_context
    )
]

# Run all 4 tasks in parallel (not sequentially)
results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Individual API Calls**:

```
OpenAI API Call #1 (gpt-4-turbo):
├─ Input: prompt + all 4 newsletters + historical context
├─ Time: ~3-5 seconds
└─ Returns:
   {
     "decisions": [
       {
         "signal": "BUY",
         "confidence": 85,
         "reasoning": "Tesla fundamentals strong + positive sentiment",
         "ticker": "TSLA",
         "source_id": "news_newsletter1_a7f92c4e"
       },
       {
         "signal": "HOLD",
         "confidence": 60,
         "reasoning": "Fed action creates uncertainty",
         "ticker": "SPY",
         "source_id": "news_newsletter2_b1d83f7a"
       },
       {
         "signal": "BUY",
         "confidence": 78,
         "reasoning": "AI demand surge validates growth thesis",
         "ticker": "NVDA",
         "source_id": "news_newsletter3_c9e17b3f"
       }
     ]
   }

Claude API Call #2 (claude-3-5-sonnet):
├─ Input: Same prompt + all 4 newsletters + historical context
├─ Time: ~2-4 seconds
└─ Returns:
   {
     "decisions": [
       {
         "signal": "BUY",
         "confidence": 92,
         "reasoning": "AI is transformational, NVDA undervalued",
         "ticker": "NVDA",
         "source_id": "news_newsletter3_c9e17b3f"
       },
       {
         "signal": "SELL",
         "confidence": 78,
         "reasoning": "Crypto cycle top confirmed by technicals",
         "ticker": "BTC",
         "source_id": "news_newsletter4_d4a2c85b"
       }
     ]
   }

Gemini API Call #3 (gemini-2.0):
├─ Input: Same prompt
├─ Time: ~3-6 seconds
└─ Returns: Different insights with different reasoning

DeepSeek API Call #4 (deepseek-chat):
├─ Input: Same prompt
├─ Time: ~4-7 seconds
└─ Returns: Different insights

Total Execution Time: ~6-7 seconds (parallel, not sequential 18-22s)
```

**Total Decisions Generated**: 10-15 decisions across all 4 LLMs

---

### Step 3.3: Process Results and Add Metadata

**File**: `apps/engine/analyze.py:77-97`

```python
valid_decisions = []

for i, res in enumerate(results):
    config = MODELS[i]  # Get the model config for this result

    if isinstance(res, Exception):
        logger.error(f"Batch analysis failed for {config['provider']}")
    elif isinstance(res, list):
        for decision in res:
            if isinstance(decision, DecisionObject):
                # Attach model metadata for attribution
                decision.model_provider = config["provider"]    # e.g., "openai"
                decision.model_name = config["model"]          # e.g., "gpt-4-turbo"
                valid_decisions.append(decision)

# Final list of DecisionObjects with complete metadata:
valid_decisions = [
    DecisionObject(
        signal="BUY",
        confidence=85,
        reasoning="Tesla fundamentals strong + positive sentiment",
        ticker="TSLA",
        source_id="news_newsletter1_a7f92c4e",
        model_provider="openai",
        model_name="gpt-4-turbo"
    ),
    DecisionObject(
        signal="HOLD",
        confidence=60,
        reasoning="Fed action creates uncertainty",
        ticker="SPY",
        source_id="news_newsletter2_b1d83f7a",
        model_provider="openai",
        model_name="gpt-4-turbo"
    ),
    DecisionObject(
        signal="BUY",
        confidence=92,
        reasoning="AI is transformational, NVDA undervalued",
        ticker="NVDA",
        source_id="news_newsletter3_c9e17b3f",
        model_provider="anthropic",
        model_name="claude-3-5-sonnet"
    ),
    DecisionObject(
        signal="SELL",
        confidence=78,
        reasoning="Crypto cycle top confirmed by technicals",
        ticker="BTC",
        source_id="news_newsletter4_d4a2c85b",
        model_provider="anthropic",
        model_name="claude-3-5-sonnet"
    ),
    # ... 6-11 more decisions
]
```

**Phase 3 Summary**:
- 4 LLM API calls (1 per provider)
- All executed in parallel with same prompt
- 10-15 decisions generated
- Each decision has full metadata (provider, model, source_id)

---

## Phase 4: Save Decisions with Attribution

### Step 4.1: Save Each Decision

**File**: `apps/engine/main.py:64-76`

```python
saved_decisions = 0
for d in valid_decisions:  # Iterate through 10-15 decisions
    try:
        save_decision(sb_client, d)
        saved_decisions += 1
        logger.info(
            f"[{d.ticker}] {d.signal} (Conf: {d.confidence}%): "
            f"Saved attribution for {d.model_provider}/{d.model_name}"
        )
    except Exception as e:
        logger.error(f"Failed to save decision for {d.ticker}: {e}")
```

**Attribution Service**: `apps/engine/attribution/service.py`

```python
def save_decision(client: Client, decision: DecisionObject) -> dict:
    """Save decision with complete attribution trail."""
    payload = {
        "source_id": decision.source_id,          # Links back to newsletter
        "ticker": decision.ticker,
        "signal": decision.signal,
        "confidence": decision.confidence,
        "reasoning": decision.reasoning,          # LLM explanation
        "model_provider": decision.model_provider,
        "model_name": decision.model_name
    }

    # Database Insert #5-16 (one per decision)
    client.table("decisions").insert(payload).execute()
```

---

### Step 4.2: Final State of Database

**Database Schema**: Decisions table

```sql
CREATE TABLE decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id TEXT NOT NULL,           -- Links to newsletter_snapshots
    ticker TEXT NOT NULL,              -- "TSLA", "SPY", "NVDA", etc.
    signal TEXT NOT NULL,              -- "BUY", "SELL", "HOLD"
    confidence INTEGER,                -- 0-100
    reasoning TEXT,                    -- Full LLM explanation
    model_provider TEXT,               -- "openai", "anthropic", "gemini", "deepseek"
    model_name TEXT,                   -- "gpt-4-turbo", "claude-3-5-sonnet", etc.
    created_at TIMESTAMPTZ DEFAULT now()
);
```

**Final decisions table contents**:

```
┌─────────────────────────┬────────┬────────┬─────┬────────────┬──────────┬──────────────────┐
│ source_id               │ ticker │ signal │ conf│ reasoning  │ provider │ model_name       │
├─────────────────────────┼────────┼────────┼─────┼────────────┼──────────┼──────────────────┤
│ news_newsletter1_a7f... │ TSLA   │ BUY    │ 85  │ Tesla...   │ openai   │ gpt-4-turbo      │
│ news_newsletter1_a7f... │ TSLA   │ BUY    │ 92  │ Tesla...   │ anthropic│ claude-3-5-sonnet│
│ news_newsletter2_b1d... │ SPY    │ HOLD   │ 60  │ Fed...     │ openai   │ gpt-4-turbo      │
│ news_newsletter3_c9e... │ NVDA   │ BUY    │ 78  │ AI...      │ openai   │ gpt-4-turbo      │
│ news_newsletter3_c9e... │ NVDA   │ BUY    │ 92  │ AI trans..│ anthropic│ claude-3-5-sonnet│
│ news_newsletter4_d4a... │ BTC    │ SELL   │ 78  │ Crypto...  │ anthropic│ claude-3-5-sonnet│
│ news_newsletter4_d4a... │ BTC    │ SELL   │ 82  │ Crypto...  │ gemini   │ gemini-2.0       │
│ news_newsletter2_b1d... │ QQQ    │ SELL   │ 71  │ Tech...    │ deepseek │ deepseek-chat    │
│ ...                     │ ...    │ ...    │ ... │ ...        │ ...      │ ...              │
└─────────────────────────┴────────┴────────┴─────┴────────────┴──────────┴──────────────────┘

Key Features:
- source_id traces each decision back to original newsletter
- Multiple decisions per ticker from different models (consensus)
- Confidence scores enable filtering/weighting
- Complete audit trail preserved
```

**Phase 4 Summary**:
- 10-15 database inserts (one per decision)
- All decisions linked to source via source_id
- Complete attribution metadata preserved
- Ready for portfolio management or reporting

---

## Complete Pipeline Summary

### API Calls Summary

```
INGESTION PHASE:
├─ Gmail API Call #1:  List all new newsletters
├─ Gmail API Calls #2-5: Fetch 4 individual messages (one each)
└─ Total: 5 Gmail API calls

CONTEXT RETRIEVAL PHASE:
├─ Gemini Embedding API Call #1: Batch embed 4 queries (KEY OPTIMIZATION)
├─ Database RPC Calls #1-4: Vector similarity search (4 calls)
└─ Total: 1 Gemini API call + 4 DB RPCs

LLM ANALYSIS PHASE:
├─ OpenAI API Call #1: Batch analyze all 4 newsletters
├─ Claude API Call #2: Batch analyze all 4 newsletters
├─ Gemini API Call #3: Batch analyze all 4 newsletters
├─ DeepSeek API Call #4: Batch analyze all 4 newsletters
└─ Total: 4 LLM API calls (parallel execution)

ATTRIBUTION PHASE:
├─ Database Inserts #5-16: Save 10-15 decisions
└─ Total: 10-15 DB writes

GRAND TOTAL:
• Gmail: 5 API calls
• Gemini Embeddings: 1 API call
• Vector Database: 4 RPC calls (fast DB operations)
• LLM Providers: 4 API calls (parallel)
• Supabase: 19-20 total database operations
```

### Database Operations

```
newsletter_snapshots table:
  4 inserts (one per newsletter, with source_id + chunk_hash)

memories table:
  (searched via RPC, not inserted in this phase)
  could be updated later with new insights

decisions table:
  10-15 inserts (one per decision)
```

### Execution Timeline

```
Time 0ms:     Start Gmail fetch (ingest_newsletters)
Time 100ms:   Receive 4 message IDs
Time 300ms:   Complete fetching all 4 messages
Time 350ms:   Finish processing and insert to newsletter_snapshots
Time 360ms:   Extract queries and start Gemini embedding
Time 500ms:   Receive embeddings
Time 550ms:   Complete vector similarity searches
Time 600ms:   Start 4 LLM provider calls in parallel
Time 6500ms:  All 4 LLM calls complete (longest is ~6 seconds)
Time 6600ms:  Process results and attach metadata
Time 6750ms:  Save all 10-15 decisions to decisions table
Time 6800ms:  Pipeline complete

Total Pipeline Time: ~6.8 seconds
(Would be 12+ seconds without batch embedding optimization)
```

### Data Transformations

```
Gmail (raw emails)
    ↓ (extract_email_body, clean_text)
NewsletterSnapshot objects (4)
    ↓ (insert to DB)
newsletter_snapshots table rows (4)
    ↓ (use full content as queries)
Query texts (4 - full newsletter content)
    ↓ (batch embed)
Embeddings vectors (4 x 768-dim)
    ↓ (vector similarity search)
Context snippets (variable)
    ↓ (aggregate)
aggregated_context string
    ↓ (combine with newsletters)
Enriched prompt (single string with all 4 newsletters + context)
    ↓ (send to 4 LLMs in parallel)
DecisionObjects (10-15 across 4 models)
    ↓ (attach model metadata)
DecisionObjects with model_provider + model_name (10-15)
    ↓ (insert to DB)
decisions table rows (10-15)
```

### Key Optimizations

1. **Batch Embedding**: 1 Gemini API call for 4 queries instead of 4 calls
2. **Parallel LLM Analysis**: 4 LLM providers called simultaneously, not sequentially
3. **Batch Newsletter Analysis**: Each LLM analyzes all 4 newsletters in one prompt
4. **Vector Indexing**: HNSW index on pgvector for fast similarity search
5. **Attribution Traceability**: source_id links decisions back to source newsletters

---

## Files Referenced

| File | Purpose |
|------|---------|
| `apps/engine/main.py` | Pipeline orchestration and entry point |
| `apps/engine/ingest/newsletter.py` | Gmail fetching and text processing |
| `apps/engine/analyze.py` | RAG context retrieval + LLM orchestration |
| `apps/engine/core/llm.py` | Multi-provider LLM clients |
| `apps/engine/memory/embeddings.py` | Gemini batch embedding |
| `apps/engine/memory/store.py` | Vector store retrieval logic |
| `apps/engine/attribution/service.py` | Decision persistence + attribution |
| `supabase/migrations/20231221000000_*.sql` | Newsletter table schema |
| `supabase/migrations/20231224000000_*.sql` | pgvector + memories table setup |
