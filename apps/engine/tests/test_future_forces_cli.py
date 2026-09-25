"""Unit tests for Future Forces CLI command dispatch and auto-mode resolution."""

from unittest.mock import AsyncMock, patch

import pytest


def test_command_constant_defined():
    """Verify COMMAND_FUTURE_FORCES is exported in core.config."""
    from core.config import COMMAND_FUTURE_FORCES

    assert COMMAND_FUTURE_FORCES == "future-forces"


@pytest.mark.asyncio
async def test_future_forces_auto_mode_market_open():
    """Verify mode='auto' resolves to 'all' when market is open."""
    from tasks.future_forces_task import run_future_forces_task

    with (
        patch("tasks.future_forces_task.get_supabase_client"),
        patch("tasks.future_forces_task.Portfolio") as mock_port_cls,
        patch("tasks.future_forces_task.is_market_open_with_logging", new_callable=AsyncMock) as mock_mkt,
        patch("tasks.future_forces_task.run_sentinel_audit", new_callable=AsyncMock) as mock_sentinel,
        patch("tasks.future_forces_task.seed_baseline_future_forces", new_callable=AsyncMock),
    ):
        mock_mkt.return_value = True
        mock_port = mock_port_cls.return_value
        mock_port.id = "test-portfolio-id"
        mock_port.positions = {}
        mock_port.cash_balance = 10000.0
        mock_port.total_equity = 10000.0
        mock_port.initialize = AsyncMock()
        mock_sentinel.return_value = {"retained": ["Test Force"]}

        res = await run_future_forces_task(mode="auto", dry_run=True)
        assert "sentinel" in res
        assert "rebalance" in res or "rebalance_orders" in res


@pytest.mark.asyncio
async def test_future_forces_auto_mode_market_closed():
    """Verify mode='auto' resolves to 'sentinel' when market is closed."""
    from tasks.future_forces_task import run_future_forces_task

    with (
        patch("tasks.future_forces_task.get_supabase_client"),
        patch("tasks.future_forces_task.Portfolio") as mock_port_cls,
        patch("tasks.future_forces_task.is_market_open_with_logging", new_callable=AsyncMock) as mock_mkt,
        patch("tasks.future_forces_task.run_sentinel_audit", new_callable=AsyncMock) as mock_sentinel,
        patch("tasks.future_forces_task.seed_baseline_future_forces", new_callable=AsyncMock),
    ):
        mock_mkt.return_value = False
        mock_port = mock_port_cls.return_value
        mock_port.id = "test-portfolio-id"
        mock_port.positions = {}
        mock_port.cash_balance = 10000.0
        mock_port.total_equity = 10000.0
        mock_port.initialize = AsyncMock()
        mock_sentinel.return_value = {"retained": ["Test Force"]}

        res = await run_future_forces_task(mode="auto", dry_run=True)
        assert "sentinel" in res
        assert "rebalance_orders" not in res


def test_main_cli_parser_future_forces():
    """Verify main.py CLI parses 'future-forces' command and options."""
    import sys

    from core.config import COMMAND_FUTURE_FORCES

    test_args = ["main.py", COMMAND_FUTURE_FORCES, "--mode", "sentinel", "--dry-run", "--force-market"]

    with patch.object(sys, "argv", test_args):
        # Import main after argv patch
        import main

        def _dummy_run(coro):
            coro.close()
            return {}

        with (
            patch("tasks.future_forces_task.run_future_forces_task", new_callable=AsyncMock) as mock_task,
            patch("asyncio.run", side_effect=_dummy_run) as mock_asyncio_run,
        ):
            # Capture the parsed args and verify execution dispatch
            main.main()
            mock_asyncio_run.assert_called_once()
            assert mock_task.called
