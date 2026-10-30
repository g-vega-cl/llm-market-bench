"""Lightweight Server-Sent Events (SSE) broadcaster and tape updater.

Runs a pure asyncio HTTP/SSE server streaming rolling 1-minute candlestick bars
and lightweight technicals to connected frontend clients, and updates the database
tape snapshot without running heavy LLM inference loops.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from datetime import UTC, datetime
from typing import Any

from core.config import logger
from trading.live_intraday_agent import calculate_technical_snapshot


class TapeBroadcaster:
    """In-memory pub/sub broker for active candlestick bars and technicals."""

    def __init__(self) -> None:
        self.latest_bars: list[dict[str, Any]] = []
        self.latest_technicals: dict[str, Any] = {}
        self.last_updated: str = ""
        self._subscribers: set[asyncio.Queue[str]] = set()

    @property
    def client_count(self) -> int:
        return len(self._subscribers)

    def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        self._subscribers.discard(q)

    def get_snapshot_payload(self) -> dict[str, Any]:
        return {
            "bars": self.latest_bars,
            "technicals": self.latest_technicals,
            "updated_at": self.last_updated or datetime.now(UTC).isoformat(),
        }

    def publish_bars(
        self,
        bars: list[dict[str, Any]],
        technicals: dict[str, Any] | None = None,
    ) -> None:
        """Update in-memory state and fan out delta to active subscriber queues."""
        if not bars:
            return

        self.latest_bars = bars[-60:]
        self.latest_technicals = technicals or calculate_technical_snapshot(self.latest_bars)
        self.last_updated = datetime.now(UTC).isoformat()

        latest_bar = self.latest_bars[-1]
        delta_payload = {
            "bar": latest_bar,
            "technicals": self.latest_technicals,
            "updated_at": self.last_updated,
        }
        event_msg = f"event: bar\ndata: {json.dumps(delta_payload)}\n\n"

        for q in list(self._subscribers):
            try:
                q.put_nowait(event_msg)
            except asyncio.QueueFull:
                logger.warning("Subscriber queue full; dropping frame")


async def update_latest_tape_in_db(sb_client: Any, bars: list[dict[str, Any]]) -> bool:
    """Update newest market_feeling row with fresh bars and technicals."""
    if not sb_client or not bars:
        return False

    def _sync_update() -> bool:
        try:
            res = (
                sb_client.table("market_feeling")
                .select("id, trades_summary")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if not res.data:
                return False

            row = res.data[0]
            row_id = row.get("id")
            if not row_id:
                return False

            summary = row.get("trades_summary") or {}
            summary["bars"] = bars[-60:]
            summary["bars_count"] = len(summary["bars"])
            summary["technicals"] = calculate_technical_snapshot(summary["bars"])

            sb_client.table("market_feeling").update(
                {
                    "trades_summary": summary,
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            ).eq("id", row_id).execute()
            return True
        except Exception:
            logger.exception("Failed to update latest tape in market_feeling")
            return False

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync_update)


class TapeHttpServer:
    """Pure asyncio HTTP/1.1 and SSE server running on a single TCP port."""

    def __init__(self, broadcaster: TapeBroadcaster) -> None:
        self.broadcaster = broadcaster

    async def handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            request_line = await reader.readline()
            if not request_line:
                writer.close()
                await writer.wait_closed()
                return

            line_str = request_line.decode("iso-8859-1", errors="replace").strip()
            parts = line_str.split()
            if len(parts) < 2:
                writer.close()
                await writer.wait_closed()
                return

            method, path = parts[0].upper(), parts[1]

            # Read headers until empty line
            while True:
                h = await reader.readline()
                if not h or h in (b"\r\n", b"\n"):
                    break

            if method == "OPTIONS":
                cors_response = (
                    b"HTTP/1.1 204 No Content\r\n"
                    b"Access-Control-Allow-Origin: *\r\n"
                    b"Access-Control-Allow-Methods: GET, OPTIONS\r\n"
                    b"Access-Control-Allow-Headers: *\r\n"
                    b"Content-Length: 0\r\n\r\n"
                )
                writer.write(cors_response)
                await writer.drain()
                writer.close()
                await writer.wait_closed()
                return

            if path == "/api/tape/health":
                body = json.dumps(
                    {
                        "status": "ok",
                        "clients": self.broadcaster.client_count,
                        "bars_count": len(self.broadcaster.latest_bars),
                    }
                ).encode("utf-8")
                resp = (
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: application/json\r\n"
                    b"Access-Control-Allow-Origin: *\r\n"
                    b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body
                )
                writer.write(resp)
                await writer.drain()
                writer.close()
                await writer.wait_closed()
                return

            if path.startswith("/api/tape/stream"):
                sse_headers = (
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: text/event-stream\r\n"
                    b"Cache-Control: no-cache, no-transform\r\n"
                    b"Connection: keep-alive\r\n"
                    b"Access-Control-Allow-Origin: *\r\n"
                    b"X-Accel-Buffering: no\r\n\r\n"
                )
                writer.write(sse_headers)
                await writer.drain()

                queue = self.broadcaster.subscribe()
                try:
                    # Send snapshot immediately on connect
                    snapshot = self.broadcaster.get_snapshot_payload()
                    initial_event = f"event: snapshot\ndata: {json.dumps(snapshot)}\n\n".encode()
                    writer.write(initial_event)
                    await writer.drain()

                    while not reader.at_eof():
                        read_task = asyncio.create_task(reader.read(1))
                        queue_task = asyncio.create_task(queue.get())
                        done, pending = await asyncio.wait(
                            [read_task, queue_task],
                            timeout=15.0,
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        for task in pending:
                            task.cancel()

                        if read_task in done:
                            # Client closed connection
                            break

                        if queue_task in done:
                            msg = queue_task.result()
                            writer.write(msg.encode("utf-8"))
                            await writer.drain()
                        elif not done:
                            # Keepalive ping for Cloudflare / Nginx timeouts
                            writer.write(b": ping\n\n")
                            await writer.drain()
                except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
                    pass
                finally:
                    self.broadcaster.unsubscribe(queue)
                    writer.close()
                    with contextlib.suppress(Exception):
                        await writer.wait_closed()
                return

            # Default 404
            not_found = b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n"
            writer.write(not_found)
            await writer.drain()
            writer.close()
            await writer.wait_closed()
        except Exception:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass


async def start_tape_server(
    broadcaster: TapeBroadcaster,
    host: str = "0.0.0.0",
    port: int = 8090,
) -> tuple[asyncio.Server, int]:
    """Start the lightweight SSE server and return the server instance and bound port."""
    server_handler = TapeHttpServer(broadcaster)
    server = await asyncio.start_server(server_handler.handle_client, host, port)
    sockets = server.sockets
    bound_port = sockets[0].getsockname()[1] if sockets else port
    return server, bound_port
