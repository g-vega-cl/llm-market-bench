import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# --- Configuration ---
# Load environment variables from apps/engine/.env
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / "engine/.env"
load_dotenv(dotenv_path=ENV_PATH)

DATABASE_URL = os.getenv("DATABASE_URL")
DOCS_DIR = BASE_DIR.parent / "docs"
OUTPUT_FILE = DOCS_DIR / "database-schema.md"

# --- Tables to Document (Ordered by Section) ---
SECTIONS = {
    "1. Trading & Portfolios": [
        "portfolios",
        "portfolio_positions",
        "trades",
        "portfolio_performance"
    ],
    "2. Ingestion & Snapshotting": [
        "newsletter_snapshots"
    ],
    "3. Memory & Decisions (pgvector)": [
        "memories",
        "decisions",
        "concept_metrics"
    ],
    "4. Market Data": [
        "market_data_cache",
        "price_history"
    ]
}

TABLE_DESCRIPTIONS = {
    "portfolios": "Stores the current financial state for each AI model.",
    "portfolio_positions": "Tracks active holdings for each portfolio.",
    "trades": "An immutable ledger of all executed trades.",
    "portfolio_performance": "Daily snapshots of portfolio metrics for equity curve visualization.",
    "newsletter_snapshots": "Stores raw content from ingested newsletters.",
    "memories": "Stores global market events for RAG retrieval.",
    "decisions": "Stores reasoning and attribution for every LLM signal. Valid status values: `CREATED`, `EXECUTED`, `VALIDATED`, `REJECTED_MARGIN`, `REJECTED_OWNERSHIP`, `REJECTED_REDUNDANCY`, `REJECTED_TOOL_USAGE`, `REJECTED_VERIFICATION`, `REJECTED_HALLUCINATION`, `REJECTED_PRICE_DEVIATION`, `REJECTED_LIQUIDITY`, `REJECTED_MARKET_CLOSED`, `REJECTED_LIMIT_PRICE`, `ERROR_PROVIDER`.",
    "concept_metrics": "Tracks momentum and frequency of semantic concepts.",
    "market_data_cache": "Temporary storage to minimize external API calls.",
    "price_history": "Permanent record of every price fetch for backtesting and analysis."
}

def get_db_connection():
    """Establishes a connection to the database."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set.")
    return psycopg2.connect(DATABASE_URL)

def get_table_schema(conn, table_name):
    """Fetches column details for a given table."""
    query = """
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = %s
    ORDER BY ordinal_position;
    """
    with conn.cursor() as cur:
        cur.execute(query, (table_name,))
        return cur.fetchall()

def format_type(data_type):
    """Formats PostgreSQL data types for Markdown."""
    type_map = {
        "uuid": "UUID",
        "text": "TEXT",
        "numeric": "NUMERIC",
        "integer": "INT",
        "timestamp with time zone": "TIMESTAMPTZ",
        "timestamp without time zone": "TIMESTAMP",
        "date": "DATE",
        "boolean": "BOOLEAN",
        "double precision": "FLOAT",
        "jsonb": "JSONB",
        "USER-DEFINED": "VECTOR(768)" # Assumption for vector types
    }
    return type_map.get(data_type, data_type.upper())

def generate_markdown(conn):
    """Generates the Markdown content."""
    md_lines = [
        "# Database Schema: AI Wall Street",
        "",
        "This document outlines the Supabase PostgreSQL schema for the AI Wall Street project, including key tables, relationships, and specialized RPC functions for vector search.",
        "",
        "## Overview",
        "",
        "The database manages four primary domains:",
        "1.  **Ingestion:** Raw newsletter data and snapshots.",
        "2.  **Memory & Retrieval:** Long-term memories and trade attribution with vector embeddings.",
        "3.  **Market Data:** Historical prices and real-time cache.",
        "4.  **Trading & Portfolios:** Agent balances, positions, and execution ledger.",
        "",
        "---",
        ""
    ]

    for section_name, tables in SECTIONS.items():
        md_lines.append(f"## {section_name}")
        md_lines.append("")
        
        for table in tables:
            md_lines.append(f"### `{table}`")
            description = TABLE_DESCRIPTIONS.get(table, "Table description pending.")
            md_lines.append(description)
            
            columns = get_table_schema(conn, table)
            if not columns:
                md_lines.append("- *Table not found or no columns.*")
            else:
                for col_name, data_type, _is_nullable in columns:
                    fmt_type = format_type(data_type)
                    # Helper for primary key identification (basic heuristic)
                    pk_info = "Primary key." if col_name == "id" else ""
                    
                    # Specific column descriptions can be added here if we want to hardcode them or fetch from DB comments
                    # For now, we'll keep it simple as a generated list
                    
                    line = f"- `{col_name}` ({fmt_type})"
                    if pk_info:
                        line += f": {pk_info}"
                    md_lines.append(line)
            
            md_lines.append("")
        
        md_lines.append("---")
        md_lines.append("")

    return "\n".join(md_lines)

def main():
    try:
        conn = get_db_connection()
        print("Connected to database.")
        
        markdown_content = generate_markdown(conn)
        
        with open(OUTPUT_FILE, "w") as f:
            f.write(markdown_content)
            
        print(f"Successfully generated documentation at: {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    main()
