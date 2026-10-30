"""Hermetic unit tests for live intraday tape SSE streaming and database updater."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from trading.tape_stream import (
    TapeBroadcaster,
    start_tape_server,
    update_latest_tape_in_db,
)


@pytest.fixture
def sample_bars():
    return [
        {
            "time": "2026-10-30T16:00:00Z",
            "open": 580.0,
            "high": 581.0,
            "low": 579.5,
            "close": 580.5,
            "volume": 1000.0,
        },
        {
            "time": "2026-10-30T16:01:00Z",
            "open": 580.5,
            "high": 581.5,
            "low": 580.2,
            "close": 581.2,
            "volume": 1500.0,
        },
    ]


def test_broadcaster_subscribe_and_snapshot(sample_bars):
    broadcaster = TapeBroadcaster()
    broadcaster.publish_bars(sample_bars)

    snapshot = broadcaster.get_snapshot_payload()
    assert len(snapshot["bars"]) == 2
    assert snapshot["technicals"]["last_close"] == 581.2
    assert "updated_at" in snapshot

    q = broadcaster.subscribe()
    assert broadcaster.client_count == 1

    broadcaster.unsubscribe(q)
    assert broadcaster.client_count == 0


@pytest.mark.asyncio
async def test_broadcaster_publish_event_delivery(sample_bars):
    broadcaster = TapeBroadcaster()
    q = broadcaster.subscribe()

    broadcaster.publish_bars(sample_bars)
    assert not q.empty()

    event_msg = await q.get()
    assert "event: bar\n" in event_msg
    assert "581.2" in event_msg

    broadcaster.unsubscribe(q)


@pytest.mark.asyncio
async def test_update_latest_tape_in_db_success(sample_bars):
    mock_sb = MagicMock()
    mock_select = MagicMock()
    mock_select.data = [
        {
            "id": "row-uuid-123",
            "trades_summary": {
                "action": "BUY",
                "allocation_pct": 10,
                "why_explanation": "Bullish momentum",
            },
        }
    ]
    mock_sb.table().select().order().limit().execute.return_value = mock_select
    mock_sb.table().update().eq().execute.return_value = MagicMock()

    result = await update_latest_tape_in_db(mock_sb, sample_bars)
    assert result is True

    update_call = mock_sb.table().update.call_args[0][0]
    trades_summary = update_call["trades_summary"]
    assert trades_summary["bars"] == sample_bars
    assert trades_summary["bars_count"] == 2
    assert trades_summary["action"] == "BUY"
    assert "technicals" in trades_summary
    assert trades_summary["technicals"]["last_close"] == 581.2


@pytest.mark.asyncio
async def test_update_latest_tape_in_db_empty_or_none():
    assert await update_latest_tape_in_db(None, []) is False
    assert await update_latest_tape_in_db(MagicMock(), []) is False

    mock_sb = MagicMock()
    mock_select = MagicMock()
    mock_select.data = []
    mock_sb.table().select().order().limit().execute.return_value = mock_select
    assert await update_latest_tape_in_db(mock_sb, [{"close": 580.0}]) is False


@pytest.mark.asyncio
async def test_tape_http_server_health_and_cors():
    broadcaster = TapeBroadcaster()
    server, port = await start_tape_server(broadcaster, host="127.0.0.1", port=0)

    try:
        # 1. Health check
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(b"GET /api/tape/health HTTP/1.1\r\nHost: localhost\r\n\r\n")
        await writer.drain()

        data = await reader.read(1024)
        response_text = data.decode()
        assert "200 OK" in response_text
        assert '"status": "ok"' in response_text
        writer.close()
        await writer.wait_closed()

        # 2. CORS OPTIONS check
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(b"OPTIONS /api/tape/stream HTTP/1.1\r\nHost: localhost\r\n\r\n")
        await writer.drain()

        data = await reader.read(1024)
        response_text = data.decode()
        assert "204 No Content" in response_text
        assert "Access-Control-Allow-Origin: *" in response_text
        writer.close()
        await writer.wait_closed()
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_tape_http_server_sse_stream_snapshot_and_delta(sample_bars):
    broadcaster = TapeBroadcaster()
    broadcaster.publish_bars(sample_bars)
    server, port = await start_tape_server(broadcaster, host="127.0.0.1", port=0)

    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(b"GET /api/tape/stream HTTP/1.1\r\nHost: localhost\r\n\r\n")
        await writer.drain()

        # Read initial SSE headers + snapshot
        data = await asyncio.wait_for(reader.read(4096), timeout=2.0)
        response_text = data.decode()
        assert "text/event-stream" in response_text
        assert "event: snapshot" in response_text
        assert "581.2" in response_text

        # Yield to let server enter its queue wait loop
        await asyncio.sleep(0.01)

        # Publish a new delta while client is connected
        new_bars = sample_bars + [
            {
                "time": "2026-10-30T16:02:00Z",
                "open": 581.2,
                "high": 582.0,
                "low": 581.0,
                "close": 581.8,
                "volume": 2000.0,
            }
        ]
        broadcaster.publish_bars(new_bars)

        # Read bar delta
        delta_data = await asyncio.wait_for(reader.read(2048), timeout=2.0)
        delta_text = delta_data.decode()
        assert "event: bar" in delta_text
        assert "581.8" in delta_text

        writer.close()
        await writer.wait_closed()
    finally:
        server.close()
        await server.wait_closed()
