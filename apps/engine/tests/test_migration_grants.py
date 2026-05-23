import os


def test_new_tables_have_grants():
    migration_dir = "../../supabase/migrations"
    if not os.path.exists(migration_dir):
        # We might be running tests from a different cwd, let's adjust
        migration_dir = "supabase/migrations"

    sql_files = [f for f in os.listdir(migration_dir) if f.endswith(".sql")]
    sql_files.sort()

    cutoff_date_str = "20261030"

    for filename in sql_files:
        date_prefix = filename[:8]
        if not date_prefix.isdigit():
            continue

        if date_prefix > cutoff_date_str:
            filepath = os.path.join(migration_dir, filename)
            with open(filepath) as f:
                content = f.read()

            # naive check for CREATE TABLE
            if "CREATE TABLE" in content.upper() and "GRANT " not in content.upper():
                raise AssertionError(
                    f"Migration {filename} creates a table but is missing explicit GRANTs (required after {cutoff_date_str})."
                )
