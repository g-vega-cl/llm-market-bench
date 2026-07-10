"""Tests for PCA Utilities."""

from unittest.mock import MagicMock

from analysis.pca_utils import update_pca_coordinates


def test_pca_index_shifting():
    """Test that malformed/skipped vectors do not cause index shifting in updates."""
    mock_client = MagicMock()

    # Mock response data for concept_metrics
    # Concept 2 has a malformed vector, which should be skipped.
    # Concept 1 and Concept 3 are valid.
    mock_data = [
        {
            "id": "id-1",
            "concept_name": "concept-1",
            "concept_vector": [1.0] * 768,
            "mention_count": 5,
        },
        {
            "id": "id-2",
            "concept_name": "concept-2",
            "concept_vector": "invalid-json-string-causing-parse-failure",
            "mention_count": 2,
        },
        {
            "id": "id-3",
            "concept_name": "concept-3",
            "concept_vector": [2.0] * 768,
            "mention_count": 10,
        },
    ]

    # Setup the mock query chain:
    # client.table("concept_metrics").select("*").limit(10000).execute()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_limit = MagicMock()
    mock_execute = MagicMock()

    mock_client.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.limit.return_value = mock_limit
    mock_limit.execute.return_value = mock_execute
    mock_execute.data = mock_data

    # Setup the mock upsert chain:
    # client.table("concept_metrics").upsert(batch).execute()
    mock_upsert = MagicMock()
    mock_table.upsert.return_value = mock_upsert
    mock_upsert.execute.return_value = MagicMock()

    # Call the target function
    update_pca_coordinates(mock_client)

    # Verify upsert calls
    assert mock_table.upsert.called
    upsert_args = mock_table.upsert.call_args[0][0]

    # There should only be 2 updated concepts (Concept 1 and Concept 3)
    assert len(upsert_args) == 2

    # Concept 1 should map to id-1
    assert upsert_args[0]["id"] == "id-1"
    assert upsert_args[0]["concept_name"] == "concept-1"

    # Concept 3 should map to id-3 (not id-2!)
    assert upsert_args[1]["id"] == "id-3"
    assert upsert_args[1]["concept_name"] == "concept-3"
