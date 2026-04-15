"""Shared pytest fixtures for root-level tests."""

import os
import pytest

# Set dummy environment variables BEFORE imports happen during test collection
# This prevents get_supabase_client() from raising ValueError at import/init time
if not os.getenv("SUPABASE_PROJECT_URL"):
    os.environ["SUPABASE_PROJECT_URL"] = "https://mock.supabase.co"
if not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "mock-key"

@pytest.fixture(autouse=True, scope="session")
def setup_test_env():
    """No-op fixture to ensure session env is ready (already set at module level)."""
    pass
