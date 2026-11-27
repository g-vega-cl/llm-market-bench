"""Max Pain portfolio audit island: leftover detection and live-first auto-heal.

Detects 0DTE positions left open past the session close and, in auto-heal mode,
prefers a real exit pass over a modeled exit. Extracted from the general
portfolio auditor to keep that island under the 800-LOC ceiling.
"""

from datetime import datetime
from typing import Any

from core.config import logger
from execution.max_pain import SYS_MAX_PAIN_OWNER_ID, reconcile_unliquidated_max_pain_positions


async def _attempt_live_max_pain_exit(client: Any, portfolio_id: str) -> bool:
    """Run one live Max Pain exit pass; return True when the book is flat afterwards."""
    try:
        from tasks.max_pain_task import run_max_pain_task

        await run_max_pain_task(action="exit", dry_run=False)
    except Exception:
        logger.exception("Live Max Pain exit pass failed; falling back to modeled exit")
        return False

    res = client.table("portfolio_positions").select("quantity").eq("portfolio_id", portfolio_id).execute()
    remaining = [p for p in (res.data or []) if int(p.get("quantity") or 0) > 0]
    return not remaining


async def audit_max_pain_portfolio(
    client: Any,
    port_by_owner: dict[str, Any],
    target_date: str | None,
    dates_to_check: list[str],
    now_ny: datetime,
    auto_heal: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Flag unliquidated sys-max-pain positions; heal with a live pass before falling back."""
    anomalies: list[dict[str, Any]] = []
    healed: list[dict[str, Any]] = []
    flagged: list[dict[str, Any]] = []

    mp_port = port_by_owner.get(SYS_MAX_PAIN_OWNER_ID)
    if not mp_port:
        return anomalies, healed, flagged

    mp_pid = mp_port["id"]
    mp_pos_res = (
        client.table("portfolio_positions")
        .select("ticker, quantity, average_cost_basis, last_updated_at")
        .eq("portfolio_id", mp_pid)
        .execute()
    )
    mp_positions = [pos for pos in (mp_pos_res.data or []) if int(pos.get("quantity") or 0) > 0]
    if not mp_positions:
        return anomalies, healed, flagged

    today_ny_str = now_ny.date().isoformat()
    is_after_daily_close = (
        now_ny.hour >= 16
        or now_ny.weekday() in (5, 6)
        or now_ny.hour < 9
        or (now_ny.hour == 9 and now_ny.minute < 30)
        or bool(target_date and target_date < today_ny_str)
        or any(str(pos.get("last_updated_at") or "")[:10] < today_ny_str for pos in mp_positions)
    )
    if is_after_daily_close:
        mp_audit_date = target_date or (dates_to_check[-1] if dates_to_check else today_ny_str)
        anomaly = {
            "date": mp_audit_date,
            "portfolio_id": mp_pid,
            "owner_id": SYS_MAX_PAIN_OWNER_ID,
            "type": "UNLIQUIDATED_MAX_PAIN_POSITION",
            "details": f"Max Pain portfolio holds {len(mp_positions)} unliquidated 0DTE position(s) after session close: {[x['ticker'] for x in mp_positions]}",
        }
        anomalies.append(anomaly)
        if auto_heal:
            if await _attempt_live_max_pain_exit(client, mp_pid):
                healed.append(
                    {
                        "date": mp_audit_date,
                        "portfolio_id": mp_pid,
                        "owner_id": SYS_MAX_PAIN_OWNER_ID,
                        "type": "UNLIQUIDATED_MAX_PAIN_POSITION",
                        "action": "AUTO_HEALED_MAX_PAIN_EXIT",
                        "exit_mode": "LIVE_PASS",
                    }
                )
            else:
                rec = await reconcile_unliquidated_max_pain_positions(
                    portfolio_row=mp_port,
                    positions=mp_positions,
                    audit_date=mp_audit_date,
                    client=client,
                )
                healed.append(
                    {
                        "date": mp_audit_date,
                        "portfolio_id": mp_pid,
                        "owner_id": SYS_MAX_PAIN_OWNER_ID,
                        "type": "UNLIQUIDATED_MAX_PAIN_POSITION",
                        "action": "AUTO_HEALED_MAX_PAIN_EXIT",
                        "new_equity": rec.get("new_equity"),
                        "exit_mode": rec.get("exit_mode", "MODELED_CLOSE"),
                    }
                )
        else:
            flagged.append(anomaly)

    return anomalies, healed, flagged
