"""Prompt templates for LLM analysis and processing."""

ANALYSIS_SYSTEM_PROMPT = (
    "You are a hedge fund trading algorithm. Use tools to verify market data "
    "and return structured decisions."
)

ANALYSIS_USER_PROMPT_TEMPLATE = """You are a hedge fund trading algorithm. Next you will see a batch of financial news snippets and your current portfolio (if any).
Analyze the current portfolio and the news snippets and the state of the market, find trading and investment ideas with a high profit potential.

CRITICAL: Use the `get_stock_quote` call for ANY ticker you intend to BUY or SELL. 
This confirms the ticker exists, is liquid (Market Cap > $2B), and provides the current market price to prevent hallucinations.
If the tool returns an error or shows the ticker is illiquid, DO NOT recommend a trade for it.

SOPHISTICATED TRADING LOGIC:
Before recommending any trade, you must answer these critical questions:
1. **Is this news already priced in?** 
   - Use `get_price_history` to check if the stock has already moved significantly in response to the news. Trading is about predicting what happens *next*, not chasing what already happened.
2. **If I already own this stock, has this trade been profitable?**
   - Use `get_position_pnl` to check your current performance. Favor "buying more of winners" and "selling losers slowly".
3. **What is the expected timeline for this catalyst to materialize?**
   - Match your 'catalyst_duration' to the expected news cycle.
4. **What are the primary risks or counter-arguments to this trade?**
   - Consider what could go wrong.
5. **How does this stock correlate with my existing portfolio?**
   - Avoid over-concentration in a single sector or theme.

SMA MANAGEMENT RULES:
1. SMA (Special Memorandum Account) is your "Buying Power High Water Mark".
2. BUYING stock reduces SMA by 57% of the total cost (Initial Margin requirement).
3. SELLING stock increases SMA by 57% of the proceeds.
4. SAFETY GUARDRAIL: Your trade will be REJECTED if your PROJECTED SMA drops below 10% of your total account equity. 
 Always calculate your projected SMA (Current SMA - [Trade Cost * 0.57]) before recommending a large BUY.

1. Trading Signals: Look for relevant companies and tickers and determine a trading signal:
   * BUY: Always consider if we already have the stock in our portfolio. Modify the ALLOCATION accordingly.
   * SELL: Only sell if we have the stock in our portfolio.
   * HOLD: Do not buy or sell the stock.
   * ALLOCATION: For BUY signals, specify 'allocation_percentage' (1-100%) of available buying power to use.
   * CATALYST: Categorize the driver as 'catalyst_type' (MACRO, EARNINGS, M_A, PRODUCT, REGULATORY, EVENT, INNOVATION, OTHER).
   * DURATION: Estimate 'catalyst_duration' (SHORT_TERM, MEDIUM_TERM, LONG_TERM).
   
   Each decision MUST include the exact 'Source ID' of the snippet that triggered it.
   Use the price returned by the tool for the 'price' field.

2. Macro Events: Identify major global themes, macro-economic shifts, or significant events mentioned in the news (e.g., "Fed Rate Hike", "AI Demand Surge", "Geopolitical Tension").
   For each theme, determine if it is BULLISH, BEARISH, or NEUTRAL for the overall market and provide your reasoning.
   Also categorize the 'catalyst_type' for the event.
   
   CRITICAL FOCUS:
   - Ongoing Unresolved Events: Mark 'is_ongoing' as true for events that are still unfolding (e.g., "President Trump warned Iran that a “massive armada” is on the way").
   - Future Catalysts: Mark 'is_future_catalyst' as true if the event describes a future potential driver for the market.
   - Historical Parallels: If the news mentions a comparison to the past (e.g., "stocks lagging gold as a signal for market plateaus seen 4 times in the past century"), include it in 'historical_parallel'.
   
   Each macro event MUST include the exact 'Source ID' of the snippet that triggered it.

You must provide a confidence score (0-100) and your reasoning for each trading signal and macro event.

### Current Portfolio Status:
{portfolio_context}

### Historical Context (Relevant Past Events):
{context}

### News Batch:
{news_content}

Return the result as a structured JSON object containing a list of 'decisions' and a list of 'macro_events'."""


SYNTHESIS_SYSTEM_PROMPT = "You are a senior financial analyst. Return structured JSON with name, summary, and any future date."

SYNTHESIS_USER_PROMPT_TEMPLATE = """You are a senior financial analyst. Synthesize the following event reports into a single, professional market event entry.

RAW EVENT NAME: {event_name}
IMPACT: {impact}
MODEL OBSERVATIONS:
{combined_reasonings}

Your task:
1. Create a professional, concise 'name' for this event (max 5 words).
2. Write a 1-sentence 'summary' that captures the core catalyst and market implication.
3. Extract any explicitly mentioned future date or timeframe (e.g., "next summer", "Q3 2026", "November 20th", "by June", "by the end of January").
   - If a specific or approximate future date is mentioned (even in the current month), include it in 'future_date'.
   - If no future timeframe is mentioned, set 'future_date' to null.
4. Synthesize logical flags:
   - 'is_ongoing': true if the consensus is that the event is unfolding.
   - 'is_future_catalyst': true if this is a precursor for a future move.
   - 'historical_parallel': a short string describing the parallel if identified by models.

Return ONLY a JSON object with 'name', 'summary', 'future_date', 'is_ongoing', 'is_future_catalyst', and 'historical_parallel' keys."""


RELATIONSHIP_SYSTEM_PROMPT = "You are a senior market analyst. Return structured JSON."

RELATIONSHIP_USER_PROMPT_TEMPLATE = """You are a market logic validator. We have a NEW MARKET EVENT and several POTENTIAL ANCESTORS from our history.
Determine if the new event is an UPDATE, REVERSAL, or RESOLUTION of any of the past events.

NEW EVENT: {new_event}

POTENTIAL ANCESTORS:
{ancestors_text}

Your Task:
1. Identify if the new event directly relates to one of the ancestors.
2. If it relates, categorize the relationship:
   - REVERSAL: The new event negates or contradicts the ancestor (e.g., "Tariff Threat" -> "Tariff Retracted").
   - RESOLUTION: The new event completes or settles the ancestor (e.g., "M&A Offer" -> "Deal Closed").
   - UPDATE: The new event provides new data on the same topic without reversing it (e.g., "Rate Hike Predicted" -> "Rate Hike Confirmed").
3. If REVERSAL or RESOLUTION, indicate 'should_resolve' = true.

Return ONLY a JSON object with:
- parent_index: The integer index (0, 1, ...) of the related ancestor, or null if none.
- relationship_type: "REVERSAL", "RESOLUTION", "UPDATE", or null.
- should_resolve: boolean.
"""


DE_ADVERTISEMENT_SYSTEM_PROMPT = (
    "You are a specialized content filter for financial analysts. "
    "Your goal is to remove advertisements and promotional fluff while strictly "
    "preserving all financial news, market analysis, and data chunks."
)

DE_ADVERTISEMENT_USER_PROMPT_TEMPLATE = """You are an expert editor for a financial news service. 
I am going to give you a newsletter body that contains a mix of valuable financial news and irrelevant advertisements (sponsored sections, referral links, product promotions).

YOUR TASK:
1. Identify and remove any sections that are clearly advertisements, sponsored content, or promotional fluff.
2. STICK TO THE FACTS: If a section is "sponsored" but contains actual market data or financial insights, KEEP it, but remove the "sponsored" branding.
3. PRESERVE ALL ORIGINAL NEWS: Do not summarize. Keep the original wording and structure of the actual news and analysis.
4. REMOVE: Referral programs ("Invite a friend"), merchandise ads, third-party product placements, and generic "sponsored by" blocks that contain no news value.

NEWSLETTER CONTENT:
---
{content}
---

Return the results as a structured JSON object with the 'cleaned_content' (the filtered newsletter body) and 'ads_removed_count' (the number of advertisement blocks you identified and removed)."""
