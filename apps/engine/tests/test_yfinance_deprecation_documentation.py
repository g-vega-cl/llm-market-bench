import pathlib


def test_yfinance_deprecation_is_documented():
    """Verify that yfinance deprecation is documented in both fundamental-analysis.md and README.md."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent.parent

    # 1. Verify wiki/concepts/fundamental-analysis.md
    wiki_path = repo_root / "wiki" / "concepts" / "fundamental-analysis.md"
    assert wiki_path.exists(), f"Wiki page not found at {wiki_path}"
    wiki_content = wiki_path.read_text().lower()

    # Assert that yfinance is mentioned and marked as deprecated
    assert "yfinance" in wiki_content
    assert "deprecated" in wiki_content

    # Assert there is a clear instruction/explanation that it shouldn't be used to fetch data
    assert any(
        phrase in wiki_content
        for phrase in ["should not be used", "must not be used", "shouldn't be used", "no longer used", "removed"]
    )

    # 2. Verify README.md
    readme_path = repo_root / "README.md"
    assert readme_path.exists(), f"README.md not found at {readme_path}"
    readme_content = readme_path.read_text().lower()

    assert "yfinance" in readme_content
    assert "deprecated" in readme_content
