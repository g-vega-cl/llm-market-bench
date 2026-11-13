"""Ingestion modules for the AI Wall Street engine.

This package contains:
- newsletter: Gmail newsletter ingestion and processing
"""

__all__ = ["ingest_newsletters"]


def __getattr__(name: str):
    """Lazily resolve top-level ingestion exports to avoid package import cycles."""
    if name == "ingest_newsletters":
        from .newsletter import ingest_newsletters

        return ingest_newsletters
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
