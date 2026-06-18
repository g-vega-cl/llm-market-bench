"""Tests for the academic paper seeding script."""

from unittest.mock import patch

# We will import the function after creating the script
from scripts.seed_academic_papers import PAPERS, seed_papers


@patch("scripts.seed_academic_papers.add_memory")
def test_seed_academic_papers(mock_add_memory):
    """Test that all papers are seeded with the correct strict parameters."""

    # Mock add_memory to simply return a fake UUID
    mock_add_memory.return_value = "fake-uuid-1234"

    # Run the seeder
    results = seed_papers()

    # Assertions
    assert len(results) == len(PAPERS), "Should return an ID for every paper"
    assert mock_add_memory.call_count == len(PAPERS), f"add_memory should be called exactly {len(PAPERS)} times"

    # Verify the arguments of the first call to ensure correct RAG formatting
    first_call_kwargs = mock_add_memory.call_args_list[0].kwargs

    assert first_call_kwargs["memory_type"] == "ACADEMIC_PAPER"
    assert first_call_kwargs["importance_score"] == 10
    assert first_call_kwargs["check_similarity"] is True

    # Check that the content string was formatted properly with the paper's title
    assert PAPERS[0]["title"] in first_call_kwargs["content"]
    assert PAPERS[0]["core_thesis"] in first_call_kwargs["content"]

    # Verify metadata contains the citation for attribution
    assert first_call_kwargs["metadata"]["source_type"] == "academic_paper"
    assert "citation" in first_call_kwargs["metadata"]
