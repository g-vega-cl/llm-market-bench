"""Ingestion modules for the AI Wall Street engine.

This package contains:
- newsletter: Gmail newsletter ingestion and processing
"""

from .newsletter import ingest_newsletters

__all__ = ["ingest_newsletters"]
