"""SQL Schema Reflection Utility.

Parses Supabase migration files to extract the source of truth for the DB schema.
"""

import os
import re
from typing import Dict, List, Optional

def get_sql_schema_from_migrations(migrations_path: str) -> Dict[str, Dict[str, dict]]:
    """Parses SQL files to extract table and column definitions.

    Returns:
        A dictionary mapping table names to column definitions.
        Example: {"decisions": {"ticker": {"type": "TEXT", "nullable": False}, ...}}
    """
    schema = {}
    migration_files = sorted([f for f in os.listdir(migrations_path) if f.endswith(".sql")])

    for filename in migration_files:
        filepath = os.path.join(migrations_path, filename)
        with open(filepath, "r") as f:
            content = f.read()

            # Pre-clean content: remove SQL comments
            clean_content = re.sub(r'--.*$', '', content, flags=re.MULTILINE)

            # Extract CREATE TABLE statements
            create_tables = re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(?:public\.)?(\w+) \((.*?)\);", clean_content, re.DOTALL | re.IGNORECASE)

            for table_name, columns_block in create_tables:
                if table_name not in schema:
                    schema[table_name] = {}

                # Extract individual columns
                column_lines = [line.strip() for line in columns_block.split(",") if line.strip()]

                for line in column_lines:
                    if any(line.upper().startswith(x) for x in ["CONSTRAINT", "PRIMARY KEY", "FOREIGN KEY", "UNIQUE"]):
                        continue
                    parts = line.split()
                    if len(parts) >= 2:
                        col_name = parts[0].strip('"').lower()
                        col_type = parts[1].upper()
                        nullable = "NOT NULL" not in line.upper()

                        schema[table_name][col_name] = {
                            "type": col_type,
                            "nullable": nullable
                        }

            # Extract ALTER TABLE ADD COLUMN statements
            alter_adds = re.findall(r"ALTER TABLE (?:IF EXISTS )?(?:public\.)?(\w+)\s+ADD COLUMN (?:IF NOT EXISTS )?(\w+) ([\w\(\)]+)(.*?);", clean_content, re.IGNORECASE | re.DOTALL)

            for table_name, col_name, col_type, constraints in alter_adds:
                table_name = table_name.lower()
                col_name = col_name.lower()
                if table_name in schema:
                    schema[table_name][col_name] = {
                        "type": col_type.upper(),
                        "nullable": "NOT NULL" not in constraints.upper()
                    }

    return schema
