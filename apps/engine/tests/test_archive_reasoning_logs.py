from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from scripts.archive_reasoning_logs import archive_llm_reasoning_logs


def test_archive_reasoning_logs_batching():
    # Mock data
    mock_logs = [
        {
            "id": f"log-{i}",
            "task_type": "INGESTION",
            "model_provider": "openai",
            "model_name": "gpt-4o",
            "prompt": [{"role": "user", "content": "hello"}],
            "response": {"result": "ok"},
            "metadata": {},
            "created_at": (datetime.now(UTC) - timedelta(days=20)).isoformat(),
        }
        for i in range(5)
    ]

    mock_supabase = MagicMock()
    # First call returns mock_logs, second call returns empty list to end pagination
    mock_select = MagicMock()
    mock_select.execute.side_effect = [
        MagicMock(data=mock_logs),
        MagicMock(data=[]),
    ]
    mock_supabase.table.return_value.select.return_value.lt.return_value.order.return_value.limit.return_value = (
        mock_select
    )
    mock_supabase.table.return_value.delete.return_value.in_.return_value.execute.return_value = MagicMock(
        data=mock_logs
    )

    mock_archive_client = MagicMock()
    mock_post_res = MagicMock()
    mock_post_res.status_code = 201
    mock_post_res.raise_for_status.return_value = None
    mock_archive_client.post.return_value = mock_post_res

    stats = archive_llm_reasoning_logs(
        supabase_client=mock_supabase,
        archive_http_client=mock_archive_client,
        cutoff_days=14,
        batch_size=5,
        vacuum=False,
    )

    assert stats["migrated_count"] == 5
    assert stats["deleted_count"] == 5
    assert mock_archive_client.post.call_count == 1
