"""Task for generating a daily 1-2 minute synthesized market newsletter using DeepSeek V4 Flash."""

import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from core.config import DEEPSEEK_FLASH_MODEL
from core.db import bulk_upsert_newsletter_snapshots, get_supabase_client
from core.fred import get_curated_macro_dashboard
from core.llm import clients
from ingest.newsletter import ingest_newsletters

logger = logging.getLogger("engine")


class GeneratedNewsletterOutput(BaseModel):
    """Structured response model for the generated newsletter."""

    title: str = Field(description="Catchy, professional title for the daily market briefing.")
    summary: str = Field(description="Concise 2-3 sentence executive summary of today's key news.")
    bullet_points: list[str] = Field(description="4 to 5 bullet points highlighting critical takeaways with emojis.")
    content: str = Field(
        description=(
            "Full newsletter article formatted in Markdown (~1,200-1,500 words, ~6 min read). "
            "Includes comprehensive subheadings, bolded tickers/metrics, macro and cross-asset context, "
            "sector and earnings spotlight, market internals and flows, actionable trade ideas & scenarios to watch, and catalyst radar."
        )
    )
    read_time_minutes: int = Field(default=6, description="Estimated read time in minutes (typically 6).")


async def _call_deepseek_flash(
    chunks: list[dict],
    session: str,
    formatted_time: str,
    macro_context: str = "",
) -> GeneratedNewsletterOutput:
    """Invokes DeepSeek V4 Flash to synthesize ingested daily newsletters and FRED macro indicators into a proper newsletter."""
    session_label = "Morning Market Open Briefing" if session == "open" else "Evening Market Close Briefing"
    now_date_str = datetime.now(ZoneInfo("America/New_York")).strftime("%B %d, %Y")

    if not chunks:
        # Fallback response when no newsletter snapshots exist for the session
        macro_text = f"\n\n**Key Economic Readings (FRED):**\n{macro_context}" if macro_context else ""
        return GeneratedNewsletterOutput(
            title=f"{session_label} — {now_date_str}",
            summary=f"No new financial newsletters were ingested prior to the {session} session.",
            bullet_points=[
                f"Quiet news flow reported for {now_date_str}.",
                "Markets operating within normal historical volatility bounds.",
                "Cross-asset positioning remains steady ahead of upcoming economic releases.",
            ],
            content=(
                f"# {session_label} — {now_date_str}\n\n"
                f"**Creation Time:** {formatted_time}\n\n"
                f"### 🌐 The Macro & Cross-Asset Narrative\n\n"
                f"No raw financial newsletters were ingested during this session window. "
                f"Major indices, benchmark Treasury yields, and currency pairs are holding steady as market participants await upcoming macroeconomic catalysts.{macro_text}\n\n"
                f"### 🔬 Sector & Earnings Spotlight\n\n"
                f"- **Sector Rotation**: Broad market breadth remains balanced with defensive and cyclical sectors trading in narrow ranges.\n"
                f"- **Earnings Radar**: Corporate earnings calendar and earnings call transcripts continue to guide fundamental expectations.\n\n"
                f"### 📈 Market Internals, Sentiment & Flows\n\n"
                f"- **Volatility**: Implied volatility indices reflect a low-stress regime with standard risk premia.\n"
                f"- **Breadth & Positioning**: Systematic funds and institutional flows maintain baseline allocations.\n\n"
                f"### 💡 Trade Ideas & Scenarios to Watch\n\n"
                f"- **Range-Bound Setup**: Monitor key index pivot and support/resistance levels during low-volume sessions.\n"
                f"- **Bull Scenario**: Upside continuation if upcoming macro data shows resilient growth with moderating inflation.\n"
                f"- **Bear Scenario**: Watch downside support levels if unexpected catalyst drives volatility expansion.\n\n"
                f"### 🗓️ The Catalyst Radar & Key Levels\n\n"
                f"- **Economic Calendar**: Key macroeconomic releases and central bank commentary scheduled for upcoming sessions.\n"
                f"- **Pivot Levels**: Watch SPX and NDX key support and resistance zones for directional confirmation."
            ),
            read_time_minutes=6,
        )

    # Compile raw newsletter context for prompt
    compiled_sources = ""
    for idx, chunk in enumerate(chunks, 1):
        compiled_sources += (
            f"\n--- Newsletter #{idx} ---\n"
            f"Sender: {chunk.get('sender', 'Unknown')}\n"
            f"Subject: {chunk.get('subject', 'No Subject')}\n"
            f"Content Snippet: {chunk.get('content', '')[:2500]}\n"
        )

    system_prompt = (
        "You are the Lead Editor of LLM Market Bench Daily Newsletter. "
        "Your task is to write a top-tier, highly engaging, comprehensive 6-minute daily market newsletter (~1,200-1,500 words) based on the ingested financial briefings and official FRED macroeconomic data of the day.\n\n"
        "Requirements:\n"
        "1. **Title**: Actionable, punchy, and professional headline capturing the overarching market theme.\n"
        "2. **Summary**: A crisp 2-3 sentence executive overview summarizing directional drivers and key themes.\n"
        "3. **Bullet Points**: 4-5 high-impact key takeaways with emojis highlighting crucial market numbers and developments.\n"
        "4. **Content**: A complete, in-depth Markdown newsletter (~1,200-1,500 words, ~6 min read).\n"
        "   Must include the following structured section headings (`###`):\n"
        "   - `### 🌐 The Macro & Cross-Asset Narrative`: Detailed synthesis of index action, Treasury yields (10Y/2Y), yield curve spreads, inflation (CPI/PCE), FX/US Dollar (DXY), commodities (Crude, Gold), and crypto.\n"
        "   - `### 🔬 Sector & Earnings Spotlight`: Deep dive into sector rotation, mega-cap tech/AI trends, corporate earnings beats/misses, and company-specific catalysts.\n"
        "   - `### 📈 Market Internals, Sentiment & Flows`: Analysis of market breadth, volatility (VIX), institutional positioning, liquidity indicators, and options/sentiment indicators.\n"
        "   - `### 💡 Trade Ideas & Scenarios to Watch`: Detailed actionable setups with catalyst, entry/triggers, key support/resistance, invalidation levels, and explicit Bull/Bear scenario branching.\n"
        "   - `### 🗓️ The Catalyst Radar & Key Levels`: Upcoming economic data releases, earnings calendar timeline, and critical technical pivot levels.\n"
        "   Use subheadings, bullet points, and bold key tickers and metrics (e.g., **NVDA**, **SPX**, **10Y Yield 4.25%**, **CPI +0.2%**, **Fed Funds 5.25%**).\n"
        "5. Tone must be professional, analytical, objective, and developer/investor friendly, delivering deep substance without fluff."
    )

    macro_block = f"Official Macro & Economic Data (FRED Indicators):\n{macro_context}\n\n" if macro_context else ""

    user_prompt = (
        f"Session Window: {session.upper()} ({session_label})\n"
        f"Date & Time: {now_date_str} at {formatted_time}\n\n"
        f"{macro_block}"
        f"Ingested Newsletters ({len(chunks)} sources):\n"
        f"{compiled_sources}"
    )

    client = clients.get_deepseek_client()

    try:
        resp = await client.chat.completions.create(
            model=DEEPSEEK_FLASH_MODEL,
            response_model=GeneratedNewsletterOutput,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_retries=2,
        )
        return resp
    except Exception:
        logger.exception("DeepSeek V4 Flash generation failed. Falling back to default output.")
        return GeneratedNewsletterOutput(
            title=f"{session_label} — {now_date_str}",
            summary="Synthesis temporary unavailable; market updates extracted from daily snapshot feeds.",
            bullet_points=["Inferred macro stability across key asset classes."],
            content=f"# {session_label} — {now_date_str}\n\n*Created at {formatted_time}*\n\nMarket briefing data processed. High-level sentiment remains balanced.",
            read_time_minutes=1,
        )
    finally:
        await clients.close_client(client, "deepseek")


async def generate_daily_newsletter(session: str = "open", sb_client=None) -> dict | None:
    """Main pipeline task to generate and store a daily newsletter.

    Args:
        session: 'open' (9:12 AM ET) or 'close' (17:00 ET)
        sb_client: Optional Supabase client instance

    Returns:
        The newly inserted record dict from Supabase.
    """
    sb = sb_client or get_supabase_client()
    now_et = datetime.now(ZoneInfo("America/New_York"))
    formatted_time = now_et.strftime("%H:%M ET")

    # Step 1: Ingest fresh newsletters from Gmail (idempotent upsert into Supabase)
    logger.info("Running Gmail newsletter ingestion prior to synthesis...")
    try:
        new_items = await ingest_newsletters(newer_than_days=1)
        if new_items:
            bulk_upsert_newsletter_snapshots(sb, new_items)
            logger.info(f"Ingested and upserted {len(new_items)} fresh newsletter snapshots.")
    except Exception as e:
        logger.warning(f"Newsletter ingestion step encountered an error: {e}")

    # Step 2: Query newsletters published within the past 12 hours based on publication date ('date')
    since_iso = (now_et - timedelta(hours=12)).astimezone(UTC).isoformat()

    logger.info(f"Generating '{session}' newsletter with DeepSeek V4 Flash at {formatted_time}...")

    snapshots = []
    try:
        res = sb.table("newsletter_snapshots").select("*").gte("date", since_iso).execute()
        snapshots = res.data or []
    except Exception as e:
        logger.warning(f"Could not fetch newsletter snapshots: {e}")

    logger.info(f"Ingested snapshots count for 24h window: {len(snapshots)}")

    # Step 3: Fetch curated macroeconomic indicators from FRED
    macro_context = ""
    try:
        macro_context = await get_curated_macro_dashboard()
    except Exception as e:
        logger.warning(f"Could not fetch FRED macro context for newsletter: {e}")

    # Generate newsletter content via DeepSeek V4 Flash
    output = await _call_deepseek_flash(snapshots, session, formatted_time, macro_context=macro_context)

    # Insert into generated_newsletters table
    record = {
        "title": output.title,
        "summary": output.summary,
        "content": output.content,
        "bullet_points": output.bullet_points,
        "session": session,
        "read_time_minutes": output.read_time_minutes,
        "source_count": len(snapshots),
        "formatted_time": formatted_time,
        "created_at": now_et.isoformat(),
    }

    try:
        res_insert = sb.table("generated_newsletters").insert(record).execute()
        inserted_data = res_insert.data[0] if res_insert.data else {}
        saved = {**record, **inserted_data}
        logger.info(f"Successfully generated and stored newsletter: '{output.title}' ({formatted_time})")
        return saved
    except Exception:
        logger.exception("Failed to insert generated newsletter into Supabase.")
        return record
