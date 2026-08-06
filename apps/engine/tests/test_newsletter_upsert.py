"""Isolated unit tests for newsletter snapshot database operations and fallback logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.db import bulk_upsert_newsletter_snapshots, upsert_newsletter_snapshot
from main import _stage_ingest_and_snapshot


class TestNewsletterDbOperations:
    """Isolated unit tests for upsert_newsletter_snapshot and bulk_upsert_newsletter_snapshots."""

    def test_upsert_newsletter_snapshot_success(self):
        """Test happy path for upsert_newsletter_snapshot."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_response = MagicMock()
        mock_response.data = [{"id": "123", "source_id": "news_1"}]
        mock_table.upsert.return_value.execute.return_value = mock_response

        data = {
            "source_id": "news_1",
            "chunk_hash": "hash_1",
            "sender": "sender_1",
            "subject": "subject_1",
            "content": "content_1",
            "date": "2026-05-27T12:00:00Z",
        }

        result = upsert_newsletter_snapshot(mock_client, data)
        assert result == {"id": "123", "source_id": "news_1"}
        mock_client.table.assert_called_once_with("newsletter_snapshots")
        mock_table.upsert.assert_called_once_with(
            {
                "source_id": "news_1",
                "chunk_hash": "hash_1",
                "sender": "sender_1",
                "subject": "subject_1",
                "content": "content_1",
                "date": "2026-05-27T12:00:00Z",
            },
            on_conflict="date,source_id",
        )

    def test_upsert_newsletter_snapshot_error(self):
        """Test exception path for upsert_newsletter_snapshot."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.upsert.return_value.execute.side_effect = Exception("Database failure")

        data = {
            "source_id": "news_1",
            "chunk_hash": "hash_1",
            "sender": "sender_1",
            "subject": "subject_1",
            "content": "content_1",
            "date": "2026-05-27T12:00:00Z",
        }

        with pytest.raises(Exception) as exc_info:
            upsert_newsletter_snapshot(mock_client, data)
        assert "Database failure" in str(exc_info.value)

    def test_bulk_upsert_newsletter_snapshots_empty(self):
        """Test bulk upsert returns immediately with an empty list."""
        mock_client = MagicMock()
        result = bulk_upsert_newsletter_snapshots(mock_client, [])
        assert result == []
        mock_client.table.assert_not_called()

    def test_bulk_upsert_newsletter_snapshots_success(self):
        """Test happy path for bulk_upsert_newsletter_snapshots."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_response = MagicMock()
        mock_response.data = [{"id": "123", "source_id": "news_1"}, {"id": "124", "source_id": "news_2"}]
        mock_table.upsert.return_value.execute.return_value = mock_response

        data = [
            {
                "source_id": "news_1",
                "chunk_hash": "hash_1",
                "sender": "sender_1",
                "subject": "subject_1",
                "content": "content_1",
                "date": "2026-05-27T12:00:00Z",
            },
            {
                "source_id": "news_2",
                "chunk_hash": "hash_2",
                "sender": "sender_2",
                "subject": "subject_2",
                "content": "content_2",
                "date": "2026-05-27T12:00:00Z",
            },
        ]

        result = bulk_upsert_newsletter_snapshots(mock_client, data)
        assert result == [{"id": "123", "source_id": "news_1"}, {"id": "124", "source_id": "news_2"}]
        mock_client.table.assert_called_once_with("newsletter_snapshots")
        mock_table.upsert.assert_called_once_with(
            [
                {
                    "source_id": "news_1",
                    "chunk_hash": "hash_1",
                    "sender": "sender_1",
                    "subject": "subject_1",
                    "content": "content_1",
                    "date": "2026-05-27T12:00:00Z",
                },
                {
                    "source_id": "news_2",
                    "chunk_hash": "hash_2",
                    "sender": "sender_2",
                    "subject": "subject_2",
                    "content": "content_2",
                    "date": "2026-05-27T12:00:00Z",
                },
            ],
            on_conflict="date,source_id",
        )

    def test_bulk_upsert_newsletter_snapshots_error(self):
        """Test exception path for bulk_upsert_newsletter_snapshots."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.upsert.return_value.execute.side_effect = Exception("Bulk database failure")

        data = [
            {
                "source_id": "news_1",
                "chunk_hash": "hash_1",
                "sender": "sender_1",
                "subject": "subject_1",
                "content": "content_1",
                "date": "2026-05-27T12:00:00Z",
            }
        ]

        with pytest.raises(Exception) as exc_info:
            bulk_upsert_newsletter_snapshots(mock_client, data)
        assert "Bulk database failure" in str(exc_info.value)


@pytest.mark.asyncio
class TestStageIngestFallback:
    """Isolated unit tests verifying the fallback logic in _stage_ingest_and_snapshot."""

    async def test_stage_ingest_no_data(self):
        """Test that stage returns early if no newsletters are found."""
        with patch("main.ingest_newsletters", new_callable=AsyncMock) as mock_ingest:
            mock_ingest.return_value = []

            data, client = await _stage_ingest_and_snapshot()
            assert data is None
            assert client is not None

    async def test_stage_ingest_bulk_upsert_happy_path(self):
        """Test that stage successfully uses bulk upsert and does not trigger fallback."""
        mock_data = [
            {
                "source_id": "news_1",
                "chunk_hash": "h1",
                "sender": "s1",
                "subject": "sub1",
                "content": "c1",
                "date": "d1",
            },
            {
                "source_id": "news_2",
                "chunk_hash": "h2",
                "sender": "s2",
                "subject": "sub2",
                "content": "c2",
                "date": "d2",
            },
        ]

        with (
            patch("main.ingest_newsletters", new_callable=AsyncMock) as mock_ingest,
            patch("main.get_supabase_client") as mock_get_client,
            patch("main.bulk_upsert_newsletter_snapshots") as mock_bulk,
            patch("main.upsert_newsletter_snapshot") as mock_single,
        ):
            mock_ingest.return_value = mock_data
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            result_data, result_client = await _stage_ingest_and_snapshot()

            assert result_data == mock_data
            assert result_client == mock_client
            mock_bulk.assert_called_once_with(mock_client, mock_data)
            mock_single.assert_not_called()

    async def test_stage_ingest_bulk_upsert_fails_fallback_succeeds(self):
        """Test fallback to individual upserts when bulk upsert fails."""
        mock_data = [
            {
                "source_id": "news_1",
                "chunk_hash": "h1",
                "sender": "s1",
                "subject": "sub1",
                "content": "c1",
                "date": "d1",
            },
            {
                "source_id": "news_2",
                "chunk_hash": "h2",
                "sender": "s2",
                "subject": "sub2",
                "content": "c2",
                "date": "d2",
            },
        ]

        with (
            patch("main.ingest_newsletters", new_callable=AsyncMock) as mock_ingest,
            patch("main.get_supabase_client") as mock_get_client,
            patch("main.bulk_upsert_newsletter_snapshots") as mock_bulk,
            patch("main.upsert_newsletter_snapshot") as mock_single,
            patch("main.logger") as mock_logger,
        ):
            mock_ingest.return_value = mock_data
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_bulk.side_effect = Exception("Bulk failed")

            result_data, result_client = await _stage_ingest_and_snapshot()

            assert result_data == mock_data
            assert result_client == mock_client
            mock_bulk.assert_called_once_with(mock_client, mock_data)
            assert mock_single.call_count == 2
            mock_single.assert_any_call(mock_client, mock_data[0])
            mock_single.assert_any_call(mock_client, mock_data[1])
            mock_logger.warning.assert_called_once_with("Bulk upsert failed, falling back to individual upserts.")

    async def test_stage_ingest_bulk_upsert_fails_and_fallback_has_partial_errors(self):
        """Test fallback to individual upserts handles exceptions on individual records."""
        mock_data = [
            {
                "source_id": "news_1",
                "chunk_hash": "h1",
                "sender": "s1",
                "subject": "sub1",
                "content": "c1",
                "date": "d1",
            },
            {
                "source_id": "news_2",
                "chunk_hash": "h2",
                "sender": "s2",
                "subject": "sub2",
                "content": "c2",
                "date": "d2",
            },
        ]

        with (
            patch("main.ingest_newsletters", new_callable=AsyncMock) as mock_ingest,
            patch("main.get_supabase_client") as mock_get_client,
            patch("main.bulk_upsert_newsletter_snapshots") as mock_bulk,
            patch("main.upsert_newsletter_snapshot") as mock_single,
            patch("main.logger") as mock_logger,
        ):
            mock_ingest.return_value = mock_data
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_bulk.side_effect = Exception("Bulk failed")
            # First item upsert fails, second item upsert succeeds
            mock_single.side_effect = [Exception("Item 1 failed"), {"id": "124"}]

            result_data, result_client = await _stage_ingest_and_snapshot()

            assert result_data == mock_data
            assert result_client == mock_client
            mock_bulk.assert_called_once_with(mock_client, mock_data)
            assert mock_single.call_count == 2
            mock_logger.exception.assert_called_once_with("Error saving snapshot for news_1")
            mock_logger.info.assert_any_call("Successfully saved 1/2 snapshots to Supabase.")
