"""CLI command to import stock-news-scraper articles into recipe_news_corpus."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure apps/engine is on sys.path when invoked directly as CLI script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import logger
from core.db import get_supabase_client
from recipes.news_corpus import import_stock_news_corpus


def main() -> int:
    parser = argparse.ArgumentParser(description="Import stock news scraper articles into recipe_news_corpus")
    parser.add_argument(
        "--scraper-dir",
        type=str,
        default="/home/cv/Documents/Code/stock-news-scraper",
        help="Path to stock-news-scraper repository root",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for database upserts",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate files without inserting into database",
    )

    args = parser.parse_args()
    scraper_path = Path(args.scraper_dir)
    output_path = scraper_path / "output"

    if not output_path.exists():
        logger.error(f"Output directory does not exist: {output_path}")
        return 1

    # Find corpus and news jsonl files
    files: list[Path] = []
    corpus_dir = output_path / "corpus"
    if corpus_dir.exists():
        files.extend(sorted(corpus_dir.glob("*.jsonl")))

    files.extend(sorted(output_path.glob("news_*.jsonl")))

    if not files:
        logger.warning(f"No JSONL news files found in {output_path}")
        return 0

    logger.info(f"Found {len(files)} news files to import from {output_path}")

    total_imported = 0
    total_skipped = 0

    if args.dry_run:
        logger.info("Running in DRY-RUN mode (zero database writes)")
        # We can pass a dummy client or just parse records
        from recipes.news_corpus import parse_and_normalize_article

        for f in files:
            count = 0
            with open(f, encoding="utf-8") as fp:
                for line in fp:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw = json.loads(line)
                        rec = parse_and_normalize_article(raw)
                        if rec:
                            count += 1
                    except Exception:
                        pass
            logger.info(f"[DRY-RUN] Validated {count} records in {f.name}")
            total_imported += count
        logger.info(f"[DRY-RUN] Complete. Total valid records: {total_imported}")
        return 0

    sb_client = get_supabase_client()
    for f in files:
        logger.info(f"Importing {f.name}...")
        try:
            stats = import_stock_news_corpus([f], sb_client=sb_client, batch_size=args.batch_size)
            inserted = stats.get("inserted", 0)
            skipped = stats.get("skipped_or_invalid", 0)
            total_imported += inserted
            total_skipped += skipped
            logger.info(f"Imported {inserted} articles ({skipped} skipped) from {f.name}")
        except Exception:
            logger.exception(f"Failed importing {f.name}")

    logger.info(f"Done. Successfully imported {total_imported} articles ({total_skipped} skipped).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
