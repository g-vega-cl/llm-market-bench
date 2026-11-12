"""Hermetic tests for import_news_cli."""

from pathlib import Path
from unittest.mock import patch

from recipes.import_news_cli import main


def test_import_news_cli_missing_dir(tmp_path: Path):
    non_existent = tmp_path / "does_not_exist"
    with patch("sys.argv", ["import_news_cli.py", "--scraper-dir", str(non_existent)]):
        ret = main()
        assert ret == 1


def test_import_news_cli_dry_run(tmp_path: Path):
    scraper_dir = tmp_path / "scraper"
    output_dir = scraper_dir / "output"
    output_dir.mkdir(parents=True)

    sample_file = output_dir / "news_2026_03.jsonl"
    sample_file.write_text(
        '{"title": "Test Title", "url": "https://example.com/1", "date_published": "2026-03-01T10:00:00Z", "source": "Bloomberg", "full_text": "Content", "company": "Nvidia"}\n',
        encoding="utf-8",
    )

    with patch("sys.argv", ["import_news_cli.py", "--scraper-dir", str(scraper_dir), "--dry-run"]):
        ret = main()
        assert ret == 0
