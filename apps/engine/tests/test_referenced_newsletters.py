"""TDD Test for get_referenced_newsletter_snapshots RPC."""

from unittest.mock import MagicMock, patch

import pytest

import core.db


@pytest.fixture
def mock_supabase():
    with patch("core.db.get_supabase_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


def test_get_referenced_newsletter_snapshots(mock_supabase):
    ref_src = "test_referenced_src_unique_12345"
    unref_src = "test_unreferenced_src_unique_12345"

    # Mock the return value of client.rpc().execute()
    mock_data = [
        {
            "source_id": ref_src,
            "sender": "test_sender",
            "subject": "test_subject_1",
            "content": "This is referenced content.",
            "date": "2026-06-18T13:00:00Z",
        }
    ]
    mock_response = MagicMock()
    mock_response.data = mock_data
    mock_supabase.rpc.return_value.execute.return_value = mock_response

    # Call the get_supabase_client via the core.db module namespace so the patch takes effect
    client = core.db.get_supabase_client()
    response = client.rpc("get_referenced_newsletter_snapshots", {"target_source_ids": [ref_src, unref_src]}).execute()

    # Assertions
    # 1. Assert that the RPC function was called correctly
    mock_supabase.rpc.assert_called_once_with(
        "get_referenced_newsletter_snapshots", {"target_source_ids": [ref_src, unref_src]}
    )

    # 2. Assert that the returned mock data is correct
    assert response.data == mock_data
    assert len(response.data) == 1
    assert response.data[0]["source_id"] == ref_src
    assert response.data[0]["content"] == "This is referenced content."
