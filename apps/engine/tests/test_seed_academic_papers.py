"""Tests for the academic paper seeding script."""

import pathlib
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


def test_docs_have_no_hardcoded_paper_counts():
    """Docs must not hardcode paper counts that rot when PAPERS grows."""
    repo_root = pathlib.Path(__file__).resolve().parents[3]
    targets = [
        repo_root / "apps/engine/scripts/seed_academic_papers.py",
        repo_root / "wiki/entities/academic-paper-seeding.md",
        repo_root / "wiki/index.md",
    ]
    banned = ["top 10", "20 papers", "20 empirical"]
    for path in targets:
        text = path.read_text().lower()
        for phrase in banned:
            assert phrase not in text, f"{path.name} contains stale phrase {phrase!r}"


def test_wiki_covers_all_seeded_papers():
    """Every PAPERS title must appear in the wiki explicit list."""
    repo_root = pathlib.Path(__file__).resolve().parents[3]
    wiki = (repo_root / "wiki/entities/academic-paper-seeding.md").read_text()
    missing = [p["title"] for p in PAPERS if p["title"] not in wiki]
    assert not missing, f"Wiki missing papers: {missing}"


def test_pozsar_shadow_banking_papers_and_prompt_block():
    """Verify Pozsar (2014) papers in PAPERS and modular prompt block."""
    from autoresearch.prompt_blocks import AVAILABLE_PROMPT_BLOCKS, render_prompt_blocks

    pozsar_titles = [
        "Shadow Banking: The Money View (Hierarchy of Money & Institutional Cash Pools)",
        "The Fed Reverse Repo Facility (RRP) Floor & Minimum Haircut Channel",
        "Forced Deleveraging via Bilateral Repo, Margin Calls & Collateral Squeezes",
    ]
    paper_titles = [p["title"] for p in PAPERS]
    for title in pozsar_titles:
        assert title in paper_titles, f"Missing paper title: {title}"

    # Verify prompt block registration and rendering
    assert "shadow_banking_liquidity_plumbing" in AVAILABLE_PROMPT_BLOCKS
    rendered = render_prompt_blocks(["shadow_banking_liquidity_plumbing"])
    assert "SHADOW BANKING & WHOLESALE LIQUIDITY PLUMBING" in rendered
    assert "RRPONTSYD" in rendered
