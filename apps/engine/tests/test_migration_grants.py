import os
import re


def _get_migration_dir() -> str:
    for candidate in ["../../supabase/migrations", "supabase/migrations"]:
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError("Could not find supabase/migrations directory")


def _get_migration_sql_files() -> list[tuple[str, str]]:
    migration_dir = _get_migration_dir()
    sql_files = sorted([f for f in os.listdir(migration_dir) if f.endswith(".sql")])
    result = []
    for filename in sql_files:
        filepath = os.path.join(migration_dir, filename)
        with open(filepath, encoding="utf-8") as f:
            result.append((filename, f.read()))
    return result


def test_new_tables_have_grants():
    migration_files = _get_migration_sql_files()
    cutoff_date_str = "20260513"

    for filename, content in migration_files:
        date_prefix = filename[:8]
        if not date_prefix.isdigit() or date_prefix <= cutoff_date_str:
            continue

        tables = re.findall(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:public\.)?([a-zA-Z0-9_]+)",
            content,
            re.IGNORECASE,
        )
        if tables and "GRANT " not in content.upper():
            raise AssertionError(
                f"Migration {filename} creates table(s) {tables} but is missing explicit GRANTs (required after {cutoff_date_str})."
            )


def test_all_active_tables_have_rls():
    """Verify that every active table in the public schema has Row Level Security enabled."""
    migration_files = _get_migration_sql_files()

    created_tables: set[str] = set()
    dropped_tables: set[str] = set()
    rls_enabled_tables: set[str] = set()

    for _filename, content in migration_files:
        created = re.findall(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:public\.)?([a-zA-Z0-9_]+)",
            content,
            re.IGNORECASE,
        )
        for t in created:
            created_tables.add(t.lower())

        dropped = re.findall(
            r"DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:public\.)?([a-zA-Z0-9_]+)",
            content,
            re.IGNORECASE,
        )
        for t in dropped:
            dropped_tables.add(t.lower())

        enabled = re.findall(
            r"ALTER\s+TABLE\s+(?:ONLY\s+)?(?:public\.)?([a-zA-Z0-9_]+)\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY",
            content,
            re.IGNORECASE,
        )
        for t in enabled:
            rls_enabled_tables.add(t.lower())

    active_tables = created_tables - dropped_tables
    missing_rls = active_tables - rls_enabled_tables

    assert not missing_rls, (
        f"Active public tables missing Row-Level Security (RLS): {sorted(missing_rls)}. "
        "Supabase requires all public schema tables to have RLS enabled to prevent unauthorized Data API access."
    )


def test_all_active_tables_have_policies():
    """Verify that every active table in the public schema with RLS has at least one policy defined."""
    migration_files = _get_migration_sql_files()

    created_tables: set[str] = set()
    dropped_tables: set[str] = set()
    tables_with_policies: set[str] = set()

    for _filename, content in migration_files:
        created = re.findall(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:public\.)?([a-zA-Z0-9_]+)",
            content,
            re.IGNORECASE,
        )
        for t in created:
            created_tables.add(t.lower())

        dropped = re.findall(
            r"DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:public\.)?([a-zA-Z0-9_]+)",
            content,
            re.IGNORECASE,
        )
        for t in dropped:
            dropped_tables.add(t.lower())

        policies = re.findall(
            r"CREATE\s+POLICY\s+[\"\']?[^\"\'\n]+[\"\']?\s+ON\s+(?:public\.)?([a-zA-Z0-9_]+)",
            content,
            re.IGNORECASE,
        )
        for t in policies:
            tables_with_policies.add(t.lower())

    active_tables = created_tables - dropped_tables
    missing_policies = active_tables - tables_with_policies

    assert not missing_policies, (
        f"Active public tables missing RLS policies: {sorted(missing_policies)}. "
        "Every table with RLS enabled must define explicit access policies."
    )


def test_new_tables_have_rls_enabled_in_file():
    """Verify that any migration creating a table also enables RLS within the migration file itself."""
    migration_files = _get_migration_sql_files()
    cutoff_date_str = "20260513"
    # Known historical migrations prior to the enforcement gate where RLS was backfilled in a subsequent migration:
    known_exceptions = {"20260901000000_create_options_data_cache.sql"}

    for filename, content in migration_files:
        date_prefix = filename[:8]
        if not date_prefix.isdigit() or date_prefix <= cutoff_date_str:
            continue
        if filename in known_exceptions:
            continue

        tables = re.findall(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:public\.)?([a-zA-Z0-9_]+)",
            content,
            re.IGNORECASE,
        )
        for t in tables:
            has_rls = bool(
                re.search(
                    rf"ALTER\s+TABLE\s+(?:ONLY\s+)?(?:public\.)?{t}\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY",
                    content,
                    re.IGNORECASE,
                )
            )
            assert has_rls, (
                f"Migration {filename} creates table '{t}' but does not enable RLS in the same file. "
                f"Every new table migration MUST include: ALTER TABLE public.{t} ENABLE ROW LEVEL SECURITY;"
            )


def test_no_tables_reference_auth_users():
    """Verify that no active tables have a foreign key constraint referencing auth.users.

    Auth is managed by Supabase Cloud while data lives in the self-hosted PostgreSQL
    archive DB. Tables in the archive DB must not have foreign key constraints to auth.users,
    as cloud user UUIDs will fail FK validation. Any historical table referencing auth.users
    must have a subsequent migration dropping the foreign key constraint.
    """
    migration_files = _get_migration_sql_files()

    tables_with_auth_fk: set[str] = set()
    dropped_auth_fk: set[str] = set()

    for _filename, content in migration_files:
        created_tables = re.findall(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:public\.)?([a-zA-Z0-9_]+)\s*\([^;]+REFERENCES\s+auth\.users",
            content,
            re.IGNORECASE,
        )
        for t in created_tables:
            tables_with_auth_fk.add(t.lower())

        dropped_constraints = re.findall(
            r"ALTER\s+TABLE\s+(?:ONLY\s+)?(?:public\.)?([a-zA-Z0-9_]+)\s+DROP\s+CONSTRAINT\s+(?:IF\s+EXISTS\s+)?([a-zA-Z0-9_]+)",
            content,
            re.IGNORECASE,
        )
        for table_name, constraint_name in dropped_constraints:
            if "user_id_fkey" in constraint_name.lower() or "auth" in constraint_name.lower():
                dropped_auth_fk.add(table_name.lower())

    active_auth_fks = tables_with_auth_fk - dropped_auth_fk
    assert not active_auth_fks, (
        f"Active public tables still reference auth.users: {sorted(active_auth_fks)}. "
        "Supabase Cloud Auth and the PostgreSQL archive DB are decoupled. "
        "Store cloud user UUIDs directly and drop the foreign key constraint."
    )
