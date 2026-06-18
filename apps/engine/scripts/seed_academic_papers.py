"""Seeds the top 10 empirical asset pricing papers into the pgvector memory store."""

import logging

# Import your existing memory store logic
from memory.store import add_memory

logger = logging.getLogger("engine")

# The Curated & Expanded Academic Dataset
PAPERS = [
    {
        "title": "The Cross-Section of Expected Stock Returns",
        "citation": "Fama & French, 1992, The Journal of Finance",
        "pillar": "Factor Investing & Risk Premiums",
        "core_thesis": "Market beta alone is insufficient to explain average stock returns. Fama and French demonstrate that two easily measured variables—size (market capitalization) and value (book-to-market equity)—combine to capture the cross-sectional variation in average stock returns.",
        "mechanism": "The persistent outperformance of small-cap and high book-to-market stocks is a rational market reward for bearing systemic, non-diversifiable distress risk. Small firms are more vulnerable to macroeconomic shocks, and 'value' firms often have depressed prices due to poor recent performance or high leverage, requiring a higher expected return to attract investors.",
        "application": "Active factor managers and 'smart beta' ETFs structurally tilt their portfolios toward value and smaller companies to systematically harvest this risk premium over long time horizons.",
        "example_scenario": "If an agent is evaluating a portfolio that consistently beats the S&P 500, it must check the portfolio's holdings. If the holdings are predominantly small-cap banks or beaten-down industrial stocks (high book-to-market), the agent should identify this as harvesting a known Fama-French risk premium, not necessarily pure stock-picking alpha.",
    },
    {
        "title": "Common Risk Factors in the Returns on Stocks and Bonds",
        "citation": "Fama & French, 1993, Journal of Financial Economics",
        "pillar": "Factor Investing & Risk Premiums",
        "core_thesis": "Introduces the seminal Three-Factor Model, expanding the Capital Asset Pricing Model (CAPM) by integrating the market risk factor with size (SMB: Small Minus Big) and value (HML: High Minus Low) factors.",
        "mechanism": "Return outperformance is mathematically decomposed into compensation for shared underlying macroeconomic risk factors. By regressing a portfolio's returns against the Market, SMB, and HML, you can isolate whether a strategy actually has unique predictive power (Alpha) or is simply riding systemic risk factors.",
        "application": "This is the gold standard for benchmarking. Institutional allocators use it to strip away factor exposure from a fund manager's track record to see if they are truly skilled.",
        "example_scenario": "An agent proposes an AI-driven trading strategy claiming 15% annual returns. Before approving, the evaluation system should run a Fama-French regression. If the Alpha (intercept) drops to zero after accounting for SMB and HML, the agent's strategy is simply a disguised small-cap value fund.",
    },
    {
        "title": "Value and Momentum Everywhere",
        "citation": "Asness, Moskowitz, & Pedersen, 2013, The Journal of Finance",
        "pillar": "Factor Investing & Risk Premiums",
        "core_thesis": "Value and momentum return premia are ubiquitous and consistent across eight diverse global asset classes and markets (equities, bonds, currencies, commodities). Crucially, value and momentum are negatively correlated across asset classes.",
        "mechanism": "While global funding liquidity risk partially explains the premium, the negative correlation is the holy grail. Value strategies buy 'losers' that are cheap, while momentum strategies buy 'winners' that are trending. Because they trigger at different times in a market cycle, combining them drastically reduces portfolio volatility.",
        "application": "Multi-factor quantitative hedge funds explicitly pair value and momentum strategies together (e.g., a 50/50 allocation) to achieve a higher Sharpe ratio than either strategy could achieve alone.",
        "example_scenario": "When building a diversified agent portfolio, if one sub-agent is strictly executing a deep-value strategy, the master agent should deploy a momentum strategy alongside it to hedge against extended 'value winters' (periods where cheap stocks stay cheap for years).",
    },
    {
        "title": "Contrarian Investment, Extrapolation, and Risk",
        "citation": "Lakonishok, Shleifer, & Vishny, 1994, The Journal of Finance",
        "pillar": "Behavioral Finance & Market Anomalies",
        "core_thesis": "Value strategies outperform because they systematically exploit the sub-optimal, extrapolated forecasts of naive investors. This paper directly attacks the Fama-French argument that value is a 'risk premium'.",
        "mechanism": "'Glamour' stocks (high past growth, high valuations) are mispriced because investors irrationally extrapolate past high earnings growth too far into the future. Conversely, investors extrapolate the poor performance of 'value' stocks, driving their prices artificially low. Mean-reversion occurs when reality fails to meet these extreme expectations.",
        "application": "Building contrarian portfolios that explicitly bet against high-growth 'glamour' stocks and buy out-of-favor companies, capitalizing on predictable price mean-reversion.",
        "example_scenario": "An agent sees a tech stock trading at 100x P/E because it grew revenue by 50% for three consecutive years. Using Lakonishok's thesis, the agent should recognize this as a highly dangerous 'glamour' stock where any slight earnings miss will trigger a violent downward repricing due to shattered extrapolation.",
    },
    {
        "title": "The Limits of Arbitrage",
        "citation": "Shleifer & Vishny, 1995, NBER Working Paper Series",
        "pillar": "Behavioral Finance & Market Anomalies",
        "core_thesis": "Textbook arbitrage requires no capital and entails no risk. In reality, professional arbitrage is heavily capital-constrained and inherently risky, allowing obvious mispricings to persist for long periods.",
        "mechanism": "Arbitrageurs rely on client capital. If an irrational mispricing deepens before it corrects (e.g., a cheap stock gets even cheaper), the fund suffers mark-to-market losses. Spooked clients withdraw their capital, forcing the arbitrageur to liquidate their position at the worst possible time, abandoning the trade before the mispricing corrects.",
        "application": "This forms the foundation of modern algorithmic risk management, dictating strict leverage limits, stop-losses, and the understanding that 'markets can remain irrational longer than you can remain solvent.'",
        "example_scenario": "An agent spots a mathematically certain pairs-trading arbitrage between two dual-listed shell companies. However, instead of using 100% of the portfolio margin to exploit it, the agent caps the trade at 5% of AUM, recognizing that the spread could irrationally widen for months and trigger a margin call.",
    },
    {
        "title": "A Model of Investor Sentiment",
        "citation": "Barberis, Shleifer, & Vishny, 1997, NBER Working Paper Series",
        "pillar": "Behavioral Finance & Market Anomalies",
        "core_thesis": "A psychological model of belief formation that mathematically produces both short-term underreaction to earnings announcements and long-term overreaction to strings of consistent news.",
        "mechanism": "Driven by cognitive heuristics: 'Conservatism' causes investors to underreact to single, isolated pieces of unexpected good news (leading to post-earnings announcement drift). However, 'Representativeness' causes investors to overreact when they see a consistent pattern (like 4 quarters of growth), mistakenly assuming the company is a permanent high-growth entity.",
        "application": "Event-driven hedge funds deploy NLP algorithms to buy stocks immediately after a sudden positive earnings surprise, knowing the broader market will take weeks to fully price in the good news due to conservatism.",
        "example_scenario": "A stagnant legacy company suddenly announces a breakthrough product and double earnings. The stock jumps 5%. The trading agent should initiate a long position, predicting that human conservatism has caused an underreaction, and the stock will continue to drift upward over the next 60 days.",
    },
    {
        "title": "Does the Stock Market Overreact?",
        "citation": "De Bondt & Thaler, 1985, The Journal of Finance",
        "pillar": "Behavioral Finance & Market Anomalies",
        "core_thesis": "Based on violations of Bayes' rule in experimental psychology, prior 'loser' portfolios significantly outperform prior 'winner' portfolios over a subsequent 3-to-5-year period.",
        "mechanism": "Persistent investor overreaction to unexpected and dramatic news events results in a severe mean-reversion anomaly. When a company suffers terrible news over a few years, market pessimism drastically overshoots reality, pricing the stock as if it will go bankrupt. When it merely survives, the stock surges.",
        "application": "Deep-value and turnaround investing rely on systematically buying assets that have suffered severe, extended drawdowns (e.g., down 80% over 3 years) knowing the pessimism is mathematically overstated.",
        "example_scenario": "A sector is hit by a regulatory crackdown and the entire industry's stocks fall 70% over two years. The agent screens for companies with enough cash to survive 3 years and buys the biggest 'losers', betting on Thaler's long-term overreaction mean-reversion.",
    },
    {
        "title": "Returns to Buying Winners and Selling Losers",
        "citation": "Jegadeesh & Titman, 1993, The Journal of Finance",
        "pillar": "Anomalies and Empirical Evidence",
        "core_thesis": "Rigorously documents the momentum anomaly. Strategies that buy stocks that have performed well in the past 3 to 12 months, and sell stocks that performed poorly, generate significant positive returns.",
        "mechanism": "The profitability of relative strength momentum cannot be explained by systematic risk. It is driven by delayed price reactions to firm-specific information, institutional herding, and the gradual dissemination of information through the market.",
        "application": "Cross-sectional momentum algorithms are used heavily by CTAs and quantitative trend-followers, strictly buying the top decile of 6-month performers and shorting the bottom decile, rebalancing monthly.",
        "example_scenario": "An agent observes a stock that has steadily climbed 40% over 6 months without any major news spikes. Instead of calling it 'overvalued' and shorting it, the agent buys the stock, adhering to the 3-to-12-month momentum continuation anomaly.",
    },
    {
        "title": "On Persistence in Mutual Fund Performance",
        "citation": "Carhart, 1997, The Journal of Finance",
        "pillar": "Anomalies and Empirical Evidence",
        "core_thesis": "Introduces the four-factor model by appending a momentum factor (PR1YR) to the Fama-French three-factor model. Demonstrates that apparent active 'skill' is almost entirely explained by holding past winners.",
        "mechanism": "Active fund managers who beat the market one year usually fail the next. The few who exhibit 'persistence' aren't stock-picking geniuses; their portfolios just heavily load on the momentum factor. Once you subtract the momentum beta, the 'alpha' disappears.",
        "application": "Institutional consultants use the Carhart model to fire active managers who charge high fees for fake alpha. Quantitative systems use it to optimize trading execution costs against momentum drift.",
        "example_scenario": "The autoresearcher is evaluating a sub-agent that boasts a 20% return. By passing the agent's trade log through a Carhart Four-Factor regression, it discovers the agent just bought Nvidia and rode the momentum wave. The autoresearcher penalizes the agent for lacking true idiosyncratic alpha.",
    },
    {
        "title": "Do Stock Prices Fully Reflect Information in Accruals and Cash Flows?",
        "citation": "Sloan, 1996, The Accounting Review",
        "pillar": "Anomalies and Empirical Evidence",
        "core_thesis": "Established the 'accrual anomaly'. Earnings derived purely from accounting accruals are significantly less persistent than earnings derived from actual cash flows, but the market fails to realize this immediately.",
        "mechanism": "Investors fixate naively on bottom-line net income (EPS). They fail to distinguish between high-quality earnings (backed by operating cash flow) and low-quality earnings (driven by accounting adjustments like uncollected receivables or inventory build-ups). When the accruals eventually reverse in future quarters, the stock tanks.",
        "application": "A primary metric for 'Quality' factor investing. Quantitative screeners routinely short high-accrual companies (perceiving earnings manipulation) while overweighting firms with robust, cash-backed earnings.",
        "example_scenario": "An agent flags a company reporting record Net Income, which usually triggers a buy. However, a deeper check reveals Operating Cash Flow is deeply negative because of massive uncollected accounts receivable. The agent identifies this as a dangerous Sloan 'accrual anomaly' and shorts the stock ahead of the next earnings report.",
    },
    {
        "title": "The Overnight Return Anomaly (The Night Effect)",
        "citation": "Lou, Polk, & Skouras, 2019, Journal of Financial Economics",
        "pillar": "Temporal & Calendar Anomalies",
        "core_thesis": "The vast majority of historical net-positive market returns occur while the market is closed (between 4:00 PM and 9:30 AM EST). Intraday returns are historically flat or negative.",
        "mechanism": "Institutional execution preferences (trading intraday to ensure liquidity) versus information release timing (macro news and earnings released overnight).",
        "application": "Timing execution strategies to capture overnight returns or avoiding intraday long holds during low-volatility regimes.",
        "example_scenario": "An agent holding a long position in S&P 500 ETFs decides to execute purchases close to the market close (3:55 PM EST) rather than at the market open, to capture the historical overnight return premium and avoid intraday decay.",
    },
    {
        "title": "The Turn-of-the-Month Effect",
        "citation": "McConnell & Xu, 2008, Financial Analysts Journal",
        "pillar": "Temporal & Calendar Anomalies",
        "core_thesis": "Disproportionately high market returns occur precisely on the last trading day of the month and the first three days of the new month. The rest of the month's average return is historically effectively zero.",
        "mechanism": "Structural capital inflows hitting the market simultaneously, including 401(k) allocations, bi-weekly payrolls, and institutional portfolio rebalancing.",
        "application": "Concentrating long equity exposure around the four-day turn-of-the-month window and holding cash or market-neutral positions during the middle of the month.",
        "example_scenario": "An agent validates a proposal to increase long index exposure on the 30th/31st of the month, recognizing that structural 401(k) inflows and payroll allocations will create a temporary upward tailwind over the next three days.",
    },
    {
        "title": "The Pre-Holiday Liquidity Vacuum",
        "citation": "Ariel, 1990, Journal of Finance",
        "pillar": "Temporal & Calendar Anomalies",
        "core_thesis": "The single trading day immediately preceding a major market holiday generates returns up to 14 times higher than standard trading days.",
        "mechanism": "Short-sellers covering positions to avoid unhedgeable weekend risk, combined with a general liquidity vacuum as institutional traders leave the desks early.",
        "application": "Long equity bias on the trading day before major US market holidays (e.g., Thanksgiving, July 4th, Christmas).",
        "example_scenario": "An agent checks a buy order proposed for the Wednesday before Thanksgiving. It approves the trade, knowing that short-sellers covering and thin pre-holiday liquidity historically skew the day's returns significantly positive.",
    },
    {
        "title": "The January Effect",
        "citation": "Rozeff & Kinney, 1976, Journal of Financial Economics",
        "pillar": "Temporal & Calendar Anomalies",
        "core_thesis": "Small-cap stocks historically exhibit outsized positive returns during the month of January.",
        "mechanism": "Tax-loss harvesting. Investors dump losing stocks in December for tax write-offs, temporarily depressing their prices, and then capital floods back into these discounted equities in January.",
        "application": "Buying beaten-down small-caps in mid-to-late December and selling them in mid-January, though noting this anomaly has degraded in modern markets due to crowded arbitrage.",
        "example_scenario": "During December, an agent screens for small-cap equities down >30% on the year with solid cash reserves. It plans a short-term trade to buy them before year-end, expecting a tax-loss harvesting recovery bounce in early January.",
    },
    {
        "title": "The Weekend Effect / Monday Effect",
        "citation": "French, 1980, Journal of Financial Economics",
        "pillar": "Temporal & Calendar Anomalies",
        "core_thesis": "Historically, stock returns on Mondays were significantly lower (often negative) compared to the preceding Fridays.",
        "mechanism": "Companies traditionally delayed releasing bad news until Friday night after the close, leading to a delayed sell-off on Monday morning. Modern algorithmic trading has largely arbitraged this effect.",
        "application": "Adjusting Monday morning execution and sentiment targets to account for weekend news accumulation, while remaining cautious of legacy bias.",
        "example_scenario": "An agent evaluates a Monday morning sentiment drop. It checks if the drop is due to systemic weekend news release patterns and avoids panic-selling, recognizing the weekend effect is highly crowded and mean-reverting in modern markets.",
    },
    {
        "title": "Post-Earnings-Announcement Drift (PEAD)",
        "citation": "Bernard & Thomas, 1989, Journal of Accounting Research",
        "pillar": "Information & Event-Driven Anomalies",
        "core_thesis": "When a company announces a severe earnings surprise, the stock price does not adjust to its final fair value immediately; instead, it slowly drifts in the direction of the surprise for up to 60 days.",
        "mechanism": "Human behavioral underreaction. Analysts and investors anchor to their prior valuation models and are psychologically slow to fully accept and price in the new fundamentals.",
        "application": "Entering long positions in stocks with massive positive earnings surprises (and shorting negative surprises) and holding them for a multi-week horizon.",
        "example_scenario": "An agent detects a stock that beat earnings expectations by 15% and has jumped 6% today. Rather than assuming the move is 'fully priced in,' the agent initiates a long position to capture the expected PEAD drift over the next 30 to 45 days.",
    },
    {
        "title": "Pre-FOMC Announcement Drift",
        "citation": "Lucca & Moench, 2015, Journal of Finance",
        "pillar": "Information & Event-Driven Anomalies",
        "core_thesis": "The US equity market experiences statistically massive excess returns in the precise 24-hour window before the Federal Reserve announces its interest rate decisions.",
        "mechanism": "Institutional de-risking. Major funds close out short positions and hedge against uncertainty before the announcement, creating mechanical buying pressure in an informational vacuum.",
        "application": "Going long S&P 500 index futures or index ETFs 24 hours prior to scheduled FOMC announcements and exiting immediately before the official release.",
        "example_scenario": "Twenty-four hours before a scheduled Fed rate decision, an agent initiates a long trade on SPY to harvest the Pre-FOMC announcement drift, scheduling a hard exit for 1:55 PM EST, just before the 2:00 PM release.",
    },
    {
        "title": "The Index Inclusion Effect (The Passive Squeeze)",
        "citation": "Shleifer, 1986, Journal of Finance",
        "pillar": "Structural & Plumbing Anomalies",
        "core_thesis": "A stock experiences severe price volatility and upward pressure simply because it is announced that it will be added to a major index (like the S&P 500).",
        "mechanism": "The legal mandate of passive ETFs and index-tracking funds, which are contractually obligated to purchase the stock regardless of valuation, allowing active market participants to front-run the trade.",
        "application": "Buying a stock immediately upon the announcement of its inclusion in a major index and selling to the passive index funds on the actual effective date of inclusion.",
        "example_scenario": "Upon hearing the announcement that a stock will join the S&P 500 in two weeks, an agent buys the stock, aiming to ride the passive index fund buying squeeze, and schedules the exit for the close of the index rebalance day.",
    },
    {
        "title": "Options Expiration Pinning (Max Pain)",
        "citation": "Ni, Pearson, & Poteshman, 2005, Journal of Financial Economics",
        "pillar": "Structural & Plumbing Anomalies",
        "core_thesis": "On major options expiration dates, highly traded stocks statistically cluster and close exactly on strike prices ending in $0 or $5, representing the 'max pain' point where the most option value expires worthless.",
        "mechanism": "Market Maker Delta Hedging. Major financial institutions hedge their options books by buying and selling the underlying stock, artificially pinning the stock to the strike price where options exposure is minimized.",
        "application": "Trading reversal or range-bound strategies on OPEX day targeting key option strikes, and avoiding breakout trades on highly optioned stocks on the third Friday of the month.",
        "example_scenario": "On OPEX Friday, an agent sees a heavily traded tech stock trading at $150.80 with a massive open interest cluster at the $150.00 strike. The agent refrains from buying a breakout, predicting the stock will be pulled back to close near the $150 strike.",
    },
    {
        "title": "A Five-Factor Asset Pricing Model",
        "citation": "Fama & French, 2015, Journal of Financial Economics",
        "pillar": "Factor Investing & Risk Premiums",
        "core_thesis": "Expands the three-factor model by adding profitability (RMW: Robust Minus Weak operating profitability) and investment (CMA: Conservative Minus Aggressive asset growth) factors to capture return variation.",
        "mechanism": "Firms with high operating profitability and conservative investment strategies systematically outperform. This is a rational premium for backing stable, cash-generative, and disciplined companies.",
        "application": "Tilt portfolios toward high-quality, high-profitability companies that do not engage in empire-building or excessive capital expenditure.",
        "example_scenario": "An agent screens for stocks to hold long-term. It filters out fast-growing firms with massive capital expenditures and negative cash flow, instead selecting firms with high return on equity and conservative asset growth to harvest the profitability and investment premiums.",
    },
]


def format_paper_as_memory(paper: dict) -> str:
    """Formats the paper dictionary into a rich text chunk for the LLM context window."""
    return (
        f"EMPIRICAL ASSET PRICING PRINCIPLE: {paper['title']}\n"
        f"Citation: {paper['citation']}\n"
        f"Category: {paper['pillar']}\n\n"
        f"Core Thesis: {paper['core_thesis']}\n"
        f"Underlying Mechanism: {paper['mechanism']}\n"
        f"Practical Application: {paper['application']}\n"
        f"Agent Trading Example: {paper['example_scenario']}"
    )


def seed_papers() -> list[str]:
    """Iterates through the dataset and pushes to the pgvector memory store."""
    successful_ids = []

    logger.info(f"Starting seeding of {len(PAPERS)} foundational finance papers...")

    for idx, paper in enumerate(PAPERS, 1):
        content = format_paper_as_memory(paper)

        # We use check_similarity=True so we can re-run this script safely
        memory_id = add_memory(
            content=content,
            metadata={"source_type": "academic_paper", "citation": paper["citation"], "pillar": paper["pillar"]},
            status="ACTIVE",
            memory_type="ACADEMIC_PAPER",
            importance_score=10,  # Max importance to ensure it bubbles up in RAG
            check_similarity=True,
            similarity_threshold=0.95,
        )

        if memory_id:
            logger.info(f"[{idx}/{len(PAPERS)}] Seeded: {paper['title']} (ID: {memory_id})")
            successful_ids.append(memory_id)
        else:
            logger.warning(f"[{idx}/{len(PAPERS)}] Skipped (Likely Duplicate): {paper['title']}")

    logger.info(f"Completed seeding. {len(successful_ids)} new papers added to vector store.")
    return successful_ids


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_papers()
