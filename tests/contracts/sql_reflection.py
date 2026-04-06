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
            # More robust table/column parsing
            create_tables = re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(?:public\.)?(\w+)\s*\((.*?)\)\s*;", clean_content, re.DOTALL | re.IGNORECASE)

            for table_name, columns_block in create_tables:
                table_name = table_name.lower()
                if table_name not in schema:
                    schema[table_name] = {}

                # Extract individual columns - handles multiline better by splitting by commas
                # but ignoring commas inside parentheses (e.g. NUMERIC(10,2))
                # Simple balanced paren parser for column splitting
                column_lines = []
                current_line = ""
                paren_count = 0
                for char in columns_block:
                    if char == '(': paren_count += 1
                    elif char == ')': paren_count -= 1

                    if char == ',' and paren_count == 0:
                        column_lines.append(current_line.strip())
                        current_line = ""
                    else:
                        current_line += char
                if current_line.strip():
                    column_lines.append(current_line.strip())

                for line in column_lines:
                    if not line: continue
                    upper_line = line.upper()
                    if any(upper_line.startswith(x) for x in ["CONSTRAINT", "PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "CHECK"]):
                        continue

                    parts = line.split()
                    if len(parts) >= 2:
                        col_name = parts[0].strip('"').lower()
                        # Handle common types like UUID, TEXT, NUMERIC(10,2)
                        col_type = parts[1].upper()
                        nullable = "NOT NULL" not in upper_line

                        schema[table_name][col_name] = {
                            "type": col_type,
                            "nullable": nullable,
                            "default": re.search(r"DEFAULT\s+([^\s,]+)", line, re.I).group(1) if "DEFAULT" in upper_line else None,
                            "is_additive": False
                        }

            # Extract ALTER TABLE ADD COLUMN statements
            alter_adds = re.findall(r"ALTER TABLE (?:IF EXISTS )?(?:public\.)?(\w+)\s+ADD COLUMN (?:IF NOT EXISTS )?(\w+) ([\w\(\)]+)(.*?);", clean_content, re.IGNORECASE | re.DOTALL)

            for table_name, col_name, col_type, constraints in alter_adds:
                table_name = table_name.lower()
                col_name = col_name.lower()
                if table_name in schema:
                    schema[table_name][col_name] = {
                        "type": col_type.upper(),
                        "nullable": "NOT NULL" not in constraints.upper(),
                        "default": re.search(r"DEFAULT\s+([^\s,]+)", constraints, re.I).group(1) if "DEFAULT" in constraints.upper() else None,
                        "is_additive": True
                    }

    return schema
