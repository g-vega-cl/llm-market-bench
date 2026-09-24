"""Historical Market Analog Research Engine.

Identifies historical macroeconomic and market precedent episodes, pulls empirical
cross-asset price return tapes across the precedent timeframe, and synthesizes
actionable profit playbooks and falsification triggers using ChatGPT Luna (with thinking).
"""

from datetime import UTC, datetime
from typing import Any

import httpx
import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from core import config
from core.config import logger
from core.db import get_supabase_client


class HistoricalPrecedentCandidate(BaseModel):
    """Structured extraction of the most relevant historical market precedent."""

    title: str = Field(..., description="Name of historical episode (e.g. August 2024 Yen Carry Trade Unwind)")
    start_date: str = Field(..., description="Start date of episode (YYYY-MM-DD)")
    end_date: str = Field(..., description="Peak or resolution date of episode (YYYY-MM-DD)")
    trigger_description: str = Field(..., description="What specifically catalyzed or triggered the move")
    macro_backdrop: str = Field(..., description="Macroeconomic environment during that episode")
    relevance_score: float = Field(..., description="Relevance and structural alignment score from 0.0 to 1.0")


class AssetReturnTape(BaseModel):
    """Empirical price performance of an asset across the historical episode."""

    ticker: str = Field(..., description="Asset ticker symbol")
    asset_class: str = Field(..., description="Asset class description")
    start_price: float = Field(..., description="Price at episode start date")
    end_price: float = Field(..., description="Price at episode end date")
    return_pct: float = Field(..., description="Percentage price change across window")
    reaction_status: str = Field(..., description="Classification: GAINED, DROPPED, or FLAT")


class PlaybookSynthesis(BaseModel):
    """Structured actionable playbook synthesized from empirical reaction tape and today's macro divergence."""

    summary_takeaway: str = Field(..., description="Core historical takeaway and market sequence")
    key_divergences_today: list[str] = Field(
        default_factory=list, description="Structural macro or valuation differences today"
    )
    long_expression: str = Field(..., description="Highest-probability long or outperform expression")
    hedge_fade_expression: str = Field(..., description="Hedge, short, or mean-reversion fade expression")
    falsification_trigger: str = Field(..., description="Explicit market signal that invalidates this analog thesis")
    predicted_outcome: str = Field(..., description="Predicted trajectory if current market follows this analog")


class HistoricalAnalogReport(BaseModel):
    """Complete consolidated historical analog research report."""

    situation: str
    precedent: HistoricalPrecedentCandidate
    empirical_tape: list[AssetReturnTape]
    playbook: PlaybookSynthesis
    markdown_report: str


DEFAULT_MACRO_BENCHMARKS: list[tuple[str, str]] = [
    ("SPY", "Equities (S&P 500)"),
    ("QQQ", "Tech (Nasdaq 100)"),
    ("TLT", "20+Y Treasury"),
    ("IEF", "7-10Y Treasury"),
    ("GLD", "Gold"),
    ("USO", "Crude Oil"),
    ("UUP", "US Dollar Index"),
    ("BTCUSD", "Bitcoin"),
]


def get_historical_analogs_openai_client(api_key: str | None = None) -> Any:
    """Create an async OpenAI client wrapped with Instructor Mode.JSON to allow thinking."""
    key = api_key or config.OPENAI_API_KEY
    raw_client = AsyncOpenAI(api_key=key, timeout=httpx.Timeout(180.0))
    return instructor.from_openai(raw_client, mode=instructor.Mode.JSON)


get_openai_client = get_historical_analogs_openai_client


def get_market_data_manager() -> Any:
    """Instantiates MarketDataManager."""
    from execution.market_data import MarketDataManager

    return MarketDataManager()


async def generate_embedding(text: str) -> list[float] | None:
    """Generates embedding for memory storage."""
    try:
        from memory.embeddings import get_embedding

        return get_embedding(text)
    except Exception as e:
        logger.warning(f"Failed to generate embedding for historical analog: {e}")
        return None


async def identify_historical_precedent(
    situation: str, client: Any | None = None, model: str | None = None
) -> HistoricalPrecedentCandidate:
    """Invokes gpt-5.6-luna with thinking to identify the single best historical analog episode."""
    cl = client or get_openai_client()
    target_model = model or config.OPENAI_MODEL

    prompt = (
        f'You are Benchify\'s Chief Macro Historian. Given current situation:\n"{situation}"\n'
        "Identify the single most relevant historical precedent episode (1970–present). "
        "Pinpoint exact dates (start_date, end_date YYYY-MM-DD), trigger, macro backdrop, and relevance score (0.0-1.0)."
    )
    return await cl.chat.completions.create(
        model=target_model,
        response_model=HistoricalPrecedentCandidate,
        messages=[
            {
                "role": "system",
                "content": "You are a quantitative macro historian specialized in finding high-conviction market analogs.",
            },
            {"role": "user", "content": prompt},
        ],
        reasoning_effort="medium",
    )


async def fetch_empirical_market_tape(
    start_date: str, end_date: str, focus_assets: list[str] | None = None, market_data_manager: Any | None = None
) -> list[AssetReturnTape]:
    """Retrieves actual historical price performance for core macro benchmarks and focus assets across the episode."""
    mdm = market_data_manager or get_market_data_manager()
    target_tickers: list[tuple[str, str]] = list(DEFAULT_MACRO_BENCHMARKS)
    if focus_assets:
        for ticker in focus_assets:
            clean = ticker.strip().upper()
            if clean and not any(t[0] == clean for t in target_tickers):
                target_tickers.append((clean, f"Focus Asset ({clean})"))

    try:
        start_dt = datetime.strptime(start_date[:10], "%Y-%m-%d").date()
        today = datetime.now(UTC).date()
        days_requested = max(30, (today - start_dt).days + 15)
    except Exception:
        days_requested = 120

    results: list[AssetReturnTape] = []
    for ticker, asset_class in target_tickers:
        try:
            history = await mdm.get_history(ticker, days=days_requested)
            if not history or len(history) < 2:
                continue
            sorted_history = sorted(history, key=lambda x: str(x.get("fetched_at", "")))
            in_window = [
                h for h in sorted_history if start_date[:10] <= str(h.get("fetched_at", ""))[:10] <= end_date[:10]
            ]
            start_row = in_window[0] if len(in_window) >= 2 else sorted_history[0]
            end_row = in_window[-1] if len(in_window) >= 2 else sorted_history[-1]

            start_price, end_price = float(start_row["price"]), float(end_row["price"])
            if start_price <= 0.0:
                continue
            return_pct = round(((end_price - start_price) / start_price) * 100.0, 2)
            status = "GAINED" if return_pct >= 1.0 else ("DROPPED" if return_pct <= -1.0 else "FLAT")

            results.append(
                AssetReturnTape(
                    ticker=ticker,
                    asset_class=asset_class,
                    start_price=round(start_price, 2),
                    end_price=round(end_price, 2),
                    return_pct=return_pct,
                    reaction_status=status,
                )
            )
        except Exception as e:
            logger.debug(f"Could not calculate tape for {ticker}: {e}")
            continue

    return results


async def synthesize_analog_playbook(
    situation: str,
    precedent: HistoricalPrecedentCandidate,
    tape: list[AssetReturnTape],
    horizon: str = "1m",
    client: Any | None = None,
    model: str | None = None,
) -> PlaybookSynthesis:
    """Invokes gpt-5.6-luna with thinking to synthesize an actionable playbook based on real empirical price tape."""
    cl = client or get_openai_client()
    target_model = model or config.OPENAI_MODEL

    tape_summary = (
        "\n".join(
            [
                f"- {item.ticker} ({item.asset_class}): ${item.start_price:.2f} -> ${item.end_price:.2f} ({item.return_pct:+.2f}%) [{item.reaction_status}]"
                for item in tape
            ]
        )
        or "No historical price tape data available."
    )

    prompt = (
        f'CURRENT SITUATION:\n"{situation}"\n\n'
        f"HISTORICAL PRECEDENT:\n- {precedent.title} ({precedent.start_date} to {precedent.end_date})\n"
        f"- Trigger: {precedent.trigger_description}\n- Macro Backdrop: {precedent.macro_backdrop}\n"
        f"- Target Forecast Horizon: {horizon}\n\n"
        f"EMPIRICAL PRICE TAPE (ACTUAL VERIFIED RETURNS):\n{tape_summary}\n\n"
        "Synthesize: 1) Core takeaway sequence, 2) Key structural divergences today, 3) Long expression, "
        "4) Hedge/Fade expression, 5) Falsification trigger, 6) Predicted trajectory."
    )

    return await cl.chat.completions.create(
        model=target_model,
        response_model=PlaybookSynthesis,
        messages=[
            {
                "role": "system",
                "content": "You are a quantitative macro strategist providing asymmetric trading playbooks.",
            },
            {"role": "user", "content": prompt},
        ],
        reasoning_effort="medium",
    )


def format_analog_markdown(
    situation: str, precedent: HistoricalPrecedentCandidate, tape: list[AssetReturnTape], playbook: PlaybookSynthesis
) -> str:
    """Formats the historical analog report into clean, token-efficient Markdown without ANSI escapes."""
    lines: list[str] = [
        f"### Historical Analog: {precedent.title} ({precedent.start_date} to {precedent.end_date})",
        f"**Situation Analyzed**: {situation}",
        f"**Precedent Background**: {precedent.trigger_description}",
        f"**Macro Context**: {precedent.macro_backdrop}",
        f"**Historical Relevance Score**: {int(precedent.relevance_score * 100)}%",
        "",
        "#### Empirical Cross-Asset Reaction Tape",
        "| Ticker | Asset Class | Start Price | End Price | Return | Status |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for item in tape:
        sign = "+" if item.return_pct > 0 else ""
        lines.append(
            f"| {item.ticker} | {item.asset_class} | ${item.start_price:.2f} | ${item.end_price:.2f} | {sign}{item.return_pct:.2f}% | {item.reaction_status} |"
        )

    lines.extend(["", "#### Key Divergences Today"])
    for div in playbook.key_divergences_today:
        lines.append(f"- {div}")

    lines.extend(
        [
            "",
            "#### Actionable Profit Playbook",
            f"- **Core Takeaway**: {playbook.summary_takeaway}",
            f"- **Long / Outperform Expression**: {playbook.long_expression}",
            f"- **Hedge / Fade Expression**: {playbook.hedge_fade_expression}",
            f"- **Falsification Trigger**: {playbook.falsification_trigger}",
            f"- **Predicted Outcome**: {playbook.predicted_outcome}",
        ]
    )

    return "\n".join(lines)


async def persist_analog_memory(report: HistoricalAnalogReport, sb_client: Any | None = None) -> str | None:
    """Vector-embeds and persists the historical analog report into the Supabase memories table."""
    sb = sb_client or get_supabase_client()
    content = (
        f"[HISTORICAL ANALOG] {report.precedent.title} ({report.precedent.start_date} to {report.precedent.end_date}): "
        f"{report.playbook.summary_takeaway} | Long: {report.playbook.long_expression} | Hedge: {report.playbook.hedge_fade_expression}"
    )

    embedding = await generate_embedding(content)
    payload = {
        "content": content,
        "embedding": embedding,
        "memory_type": "HISTORICAL_ANALOG",
        "importance_score": 8,
        "target_date": report.precedent.end_date,
        "metadata": {
            "situation": report.situation,
            "title": report.precedent.title,
            "start_date": report.precedent.start_date,
            "end_date": report.precedent.end_date,
            "relevance_score": report.precedent.relevance_score,
            "long_expression": report.playbook.long_expression,
            "hedge_fade_expression": report.playbook.hedge_fade_expression,
            "falsification_trigger": report.playbook.falsification_trigger,
        },
    }

    try:
        resp = sb.table("memories").insert(payload).execute()
        if resp.data and len(resp.data) > 0:
            return resp.data[0].get("id")
    except Exception as e:
        logger.warning(f"Failed to persist historical analog to Supabase: {e}")

    return None


async def research_historical_market_analog(
    situation: str,
    focus_assets: list[str] | None = None,
    horizon: str = "1m",
    sb_client: Any | None = None,
    market_data_manager: Any | None = None,
    openai_client: Any | None = None,
    model_name: str | None = None,
) -> str:
    """Executes end-to-end historical analog research, empirical tape extraction, and playbook synthesis."""
    if not situation or not situation.strip():
        return "Error: No market situation or query provided for historical analog research."

    try:
        precedent = await identify_historical_precedent(
            situation=situation.strip(),
            client=openai_client,
            model=model_name,
        )

        tape = await fetch_empirical_market_tape(
            start_date=precedent.start_date,
            end_date=precedent.end_date,
            focus_assets=focus_assets,
            market_data_manager=market_data_manager,
        )

        playbook = await synthesize_analog_playbook(
            situation=situation.strip(),
            precedent=precedent,
            tape=tape,
            horizon=horizon,
            client=openai_client,
            model=model_name,
        )

        markdown_report = format_analog_markdown(
            situation=situation.strip(),
            precedent=precedent,
            tape=tape,
            playbook=playbook,
        )

        report_obj = HistoricalAnalogReport(
            situation=situation.strip(),
            precedent=precedent,
            empirical_tape=tape,
            playbook=playbook,
            markdown_report=markdown_report,
        )
        await persist_analog_memory(report_obj, sb_client=sb_client)

        return markdown_report

    except Exception as e:
        logger.exception("Error executing research_historical_market_analog: %s", e)
        return f"Error executing historical market analog research: {str(e)}"
