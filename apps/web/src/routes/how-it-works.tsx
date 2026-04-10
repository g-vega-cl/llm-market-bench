import { createFileRoute } from '@tanstack/react-router'
import { ThoughtProcessFlow } from '../components/ThoughtProcessFlow'

export const Route = createFileRoute('/how-it-works')({
    component: HowItWorks,
})

function HowItWorks() {
    return (
        <div className="flex flex-col min-h-screen px-4 md:px-8 py-8 text-slate-100">
            <div className="flex flex-col w-full">
                <div className="text-center mb-16">
                    <h1 className="text-4xl md:text-5xl font-extrabold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
                        How Benchify Works
                    </h1>
                    <p className="text-xl text-slate-400">
                        Benchify is an automated arena where leading AI models compete in the stock market.
                        Four primary LLMs (OpenAI, Claude, Gemini, DeepSeek) analyze newsletters, debate global events,
                        and execute trades — with specialized agents for verification, contrarian positioning, and post-analysis.
                    </p>
                    <div className="flex gap-2 justify-center mt-4 flex-wrap">
                        <span className="px-3 py-1 text-sm rounded-full bg-green-500/20 text-green-300 border border-green-500/30">OpenAI gpt-5.4-nano</span>
                        <span className="px-3 py-1 text-sm rounded-full bg-orange-500/20 text-orange-300 border border-orange-500/30">Claude claude-haiku-4-5</span>
                        <span className="px-3 py-1 text-sm rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">Gemini gemini-3.1-flash-lite-preview</span>
                        <span className="px-3 py-1 text-sm rounded-full bg-violet-500/20 text-violet-300 border border-violet-500/30">DeepSeek deepseek-reasoner</span>
                    </div>
                    <p className="text-lg text-slate-500 mt-4">
                        Tripled trigger daily at <strong className="text-blue-300">09:30, 12:30, 15:30 ET</strong> during market hours
                    </p>
                </div>

                <div className="space-y-24 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-700 before:to-transparent">
                    {/* Phase 1: Ingestion */}
                    <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                        <div className="flex items-center justify-center w-10 h-10 rounded-full border-2 border-blue-500 bg-slate-900 shadow text-blue-500 shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-transform group-hover:scale-110">
                            <span className="text-xl">📰</span>
                        </div>
                        <div className="w-full md:w-[calc(50%-2.5rem)] p-6 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-blue-500/50 transition-colors shadow-lg backdrop-blur-sm">
                            <div className="flex flex-col gap-2">
                                <div className="flex items-center gap-2 flex-wrap">
                                    <span className="text-blue-400 font-mono text-sm tracking-wider uppercase">Phase 1</span>
                                    <span className="px-2 py-0.5 text-xs rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">Tripled Trigger: 09:30, 12:30, 15:30 ET</span>
                                </div>
                                <h3 className="text-2xl font-bold text-white">Ingestion & Normalization</h3>
                                <p className="text-slate-400">
                                    GitHub Actions fires the pipeline at market open, midday, and afternoon. The engine enforces a <strong className="text-blue-300">Holiday-Aware Market Hours Check</strong> via FMP API (5-minute TTL caching) to skip execution outside 09:30-16:00 ET, weekends, or US holidays.
                                </p>
                                <ul className="mt-2 space-y-1 text-sm text-slate-500 list-disc list-inside">
                                    <li>Scrapes unread emails from Gmail; removes ads via Gemini Flash</li>
                                    <li>Economic Calendar ingestion from Trading Economics (bi-weekly)</li>
                                    <li>Data snapshotting with idempotency keys (source_id, chunk_hash)</li>
                                    <li><strong className="text-blue-300">FMP Market Status Check</strong> with class-level caching to avoid redundant API calls</li>
                                </ul>
                                <div className="flex gap-2 mt-2 flex-wrap">
                                    <span className="px-2 py-1 text-xs rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">FMP Cache</span>
                                    <span className="px-2 py-1 text-xs rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">Gmail API</span>
                                    <span className="px-2 py-1 text-xs rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">Trading Economics</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Phase 2: Analysis */}
                    <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                        <div className="flex items-center justify-center w-10 h-10 rounded-full border-2 border-purple-500 bg-slate-900 shadow text-purple-500 shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-transform group-hover:scale-110">
                            <span className="text-xl">🤖</span>
                        </div>
                        <div className="w-full md:w-[calc(50%-2.5rem)] p-6 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-purple-500/50 transition-colors shadow-lg backdrop-blur-sm">
                            <div className="flex flex-col gap-2">
                                <span className="text-purple-400 font-mono text-sm tracking-wider uppercase">Phase 2</span>
                                <h3 className="text-2xl font-bold text-white">AI Consensus & Analysis</h3>
                                <p className="text-slate-400">
                                    Four LLMs analyze data in parallel using the <strong className="text-purple-300">PromptFactory</strong> for semantically identical instructions. The engine injects a <strong className="text-purple-300">Global Macro Snapshot</strong> (16 assets, regime detection at 2σ) for Risk-On/Risk-Off awareness. It initializes portfolios and fetches current market prices for all unique holdings <em>before</em> analysis.
                                </p>
                                <div className="flex gap-2 mt-2 flex-wrap">
                                    <span className="px-2 py-1 text-xs rounded bg-green-500/20 text-green-300 border border-green-500/30">OpenAI gpt-5.4-nano</span>
                                    <span className="px-2 py-1 text-xs rounded bg-orange-500/20 text-orange-300 border border-orange-500/30">Claude claude-haiku-4-5</span>
                                    <span className="px-2 py-1 text-xs rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">Gemini gemini-3.1-flash-lite-preview</span>
                                    <span className="px-2 py-1 text-xs rounded bg-violet-500/20 text-violet-300 border border-violet-500/30">DeepSeek deepseek-reasoner</span>
                                </div>
                                <ul className="mt-2 space-y-1 text-sm text-slate-500 list-disc list-inside">
                                    <li><strong className="text-purple-300">Asynchronous Chunk Batching</strong>: 20 chunks per LLM call to prevent token truncation</li>
                                    <li><strong className="text-purple-300">Web Search</strong>: Claude (`web_search_20250305`) and Gemini (`google_search`) with automatic citations</li>
                                    <li><strong className="text-purple-300">Stock Screener</strong>: `run_stock_screener` tool for liquidity-filtered asset discovery</li>
                                    <li><strong className="text-purple-300">DiscoveryAgent</strong>: Alpha Discovery via tool-calling loop (up to 3 steps) for "Investable Assets" mapping</li>
                                    <li><strong className="text-purple-300">DeepSeek Thinking Mode</strong>: CoT reasoning with `reasoning_content` preservation</li>
                                </ul>
                                <div className="flex gap-2 mt-2 flex-wrap">
                                    <span className="px-2 py-1 text-xs rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">PromptFactory</span>
                                    <span className="px-2 py-1 text-xs rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">Global Macro Tracker</span>
                                    <span className="px-2 py-1 text-xs rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">Web Search + Citations</span>
                                    <span className="px-2 py-1 text-xs rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">DiscoveryAgent</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Phase 3: Verification */}
                    <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                        <div className="flex items-center justify-center w-10 h-10 rounded-full border-2 border-amber-500 bg-slate-900 shadow text-amber-500 shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-transform group-hover:scale-110">
                            <span className="text-xl">🔍</span>
                        </div>
                        <div className="w-full md:w-[calc(50%-2.5rem)] p-6 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-amber-500/50 transition-colors shadow-lg backdrop-blur-sm">
                            <div className="flex flex-col gap-2">
                                <span className="text-amber-400 font-mono text-sm tracking-wider uppercase">Phase 3</span>
                                <h3 className="text-2xl font-bold text-white">The Skeptical Verifier</h3>
                                <p className="text-slate-400">
                                    A dedicated "Skeptical Agent" intercepts every Buy/Sell signal using the <strong className="text-amber-300">same intelligence profile</strong> as the original generator. It performs a <strong className="text-amber-300">4-Layer Enforcement</strong> audit and checks if news is "priced in" via history, identifies failure modes, and searches for "Silver to our Gold" alternatives.
                                </p>
                                <ul className="mt-2 space-y-1 text-sm text-slate-500 list-disc list-inside">
                                    <li><strong className="text-amber-300">Layer 1</strong>: Pre-Prompt Strengthening (enhanced system prompts with few-shot examples)</li>
                                    <li><strong className="text-amber-300">Layer 2</strong>: Prompt Context Enhancement (portfolio source of truth, held tickers list)</li>
                                    <li><strong className="text-amber-300">Layer 3</strong>: History scanning for actual tool calls via native function calling</li>
                                    <li><strong className="text-amber-300">Layer 4</strong>: Structured output enforcement with `price_source` field declaration</li>
                                </ul>
                                <ul className="mt-2 space-y-1 text-sm text-slate-500 list-disc list-inside">
                                    <li><strong className="text-amber-300">Hard Tool Enforcement</strong>: `get_stock_quote`, `calculate_buy_quantity`, `calculate_sell_quantity` must be actual function calls — text claims are hallucinations</li>
                                    <li><strong className="text-amber-300">Ownership Pre-Validation</strong>: SELL signals for unheld tickers are rejected pre-analysis</li>
                                    <li><strong className="text-amber-300">50% Confidence Penalty</strong>: Decisions without verified tool calls receive automatic reduction</li>
                                    <li><strong className="text-amber-300">Strategic Reasoning Audit</strong>: Validates logical consistency of "sell X to fund Y" patterns</li>
                                    <li><strong className="text-amber-300">Calendar & Seasonal Strategies</strong>: Turn of Month, Payday Anomaly adherence checks</li>
                                </ul>
                                <div className="flex gap-2 mt-2 flex-wrap">
                                    <span className="px-2 py-1 text-xs rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">4-Layer Enforcement</span>
                                    <span className="px-2 py-1 text-xs rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">Hard Tool Enforcement</span>
                                    <span className="px-2 py-1 text-xs rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">Ownership Validation</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Phase 4: Execution */}
                    <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                        <div className="flex items-center justify-center w-10 h-10 rounded-full border-2 border-emerald-500 bg-slate-900 shadow text-emerald-500 shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-transform group-hover:scale-110">
                            <span className="text-xl">⚖️</span>
                        </div>
                        <div className="w-full md:w-[calc(50%-2.5rem)] p-6 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-emerald-500/50 transition-colors shadow-lg backdrop-blur-sm">
                            <div className="flex flex-col gap-2">
                                <span className="text-emerald-400 font-mono text-sm tracking-wider uppercase">Phase 4</span>
                                <h3 className="text-2xl font-bold text-white">Execution & Settlement</h3>
                                <p className="text-slate-400">
                                    Approved trades undergo strict guardrails. The engine executes trades with <strong className="text-emerald-300">Atomic Settlement</strong> ("Commit at End" pattern) and links decisions to trades via <strong className="text-emerald-300">Two-Phase Attribution Locking</strong>.
                                </p>
                                <ul className="mt-2 space-y-1 text-sm text-slate-500 list-disc list-inside">
                                    <li><strong className="text-emerald-300">FMP-Verified Market Hours</strong>: Holiday-aware with 5-minute TTL caching</li>
                                    <li><strong className="text-emerald-300">5.0% Price Banding</strong>: Rejects trades where AI price deviates &gt;5% from market</li>
                                    <li><strong className="text-emerald-300">Reg T Margin Validation</strong>: Buying power check with $1,000 absolute minimum for BUYs</li>
                                    <li><strong className="text-emerald-300">10% Minimum Position Rule</strong>: Auto-upsize for BUYs; 100% sell for SELLS below floor</li>
                                    <li><strong className="text-emerald-300">Atomic Settlement</strong>: Cash/positions update only if ledger entry succeeds — prevents "Phantom Deductions"</li>
                                    <li><strong className="text-emerald-300">Two-Phase Attribution Locking</strong>: Decision (status=VALIDATED) → Trade → Decision (status=EXECUTED, trade_id)</li>
                                </ul>
                                <ul className="mt-2 space-y-1 text-sm text-slate-500 list-disc list-inside">
                                    <li><strong className="text-emerald-300">Real-time P&L</strong>: SQL View calculates `(market_price - avg_cost) * quantity` on-the-fly</li>
                                    <li><strong className="text-emerald-300">Immediate Consistency</strong>: Reg T metrics persisted immediately after every trade</li>
                                </ul>
                                <div className="flex gap-2 mt-2 flex-wrap">
                                    <span className="px-2 py-1 text-xs rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Reg T Compliance</span>
                                    <span className="px-2 py-1 text-xs rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Atomic Settlement</span>
                                    <span className="px-2 py-1 text-xs rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Attribution Locking</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Phase 5: Feedback */}
                    <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                        <div className="flex items-center justify-center w-10 h-10 rounded-full border-2 border-pink-500 bg-slate-900 shadow text-pink-500 shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-transform group-hover:scale-110">
                            <span className="text-xl">🧠</span>
                        </div>
                        <div className="w-full md:w-[calc(50%-2.5rem)] p-6 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-pink-500/50 transition-colors shadow-lg backdrop-blur-sm">
                            <div className="flex flex-col gap-2">
                                <span className="text-pink-400 font-mono text-sm tracking-wider uppercase">Phase 5</span>
                                <h3 className="text-2xl font-bold text-white">Learning & Feedback</h3>
                                <p className="text-slate-400">
                                    The cycle completes. Specialized agents perform post-analysis while the system maintains long-term memory via pgvector RAG with <strong className="text-pink-300">Scenario Analysis</strong> for context awareness.
                                </p>
                                <ul className="mt-2 space-y-1 text-sm text-slate-500 list-disc list-inside">
                                    <li><strong className="text-pink-300">Manager Agent</strong>: Post-analysis at 5, 14, 30-day intervals; generates "Lessons Learned" stored as `LESSON_LEARNED` memories</li>
                                    <li><strong className="text-pink-300">Contrarian Agent</strong>: Identifies crowded trades and missed risks using `List[ContrarianAgentResponse]` for multi-block robustness</li>
                                    <li><strong className="text-pink-300">Government Tracking</strong>: Monthly audit of incentives/policies with strict compliance enforcement</li>
                                    <li><strong className="text-pink-300">Cause & Effect Analysis</strong>: Bi-weekly (Tuesdays & Fridays) with semantic deduplication (pgvector, 24h lookback, 0.90 similarity)</li>
                                    <li><strong className="text-pink-300">Dynamic Ticker Discovery</strong>: FMP API for sector proxies, ETFs, derivative play tickers</li>
                                </ul>
                                <ul className="mt-2 space-y-1 text-sm text-slate-500 list-disc list-inside">
                                    <li><strong className="text-pink-300">Long-term Memory</strong>: pgvector store with Scenario Analysis (multi-outcome + trading plans)</li>
                                    <li><strong className="text-pink-300">Semantic Deduplication</strong>: 24-hour lookback, &gt;0.90 similarity threshold prevents duplicates</li>
                                </ul>
                                <div className="flex gap-2 mt-2 flex-wrap">
                                    <span className="px-2 py-1 text-xs rounded bg-pink-500/20 text-pink-300 border border-pink-500/30">Manager Agent</span>
                                    <span className="px-2 py-1 text-xs rounded bg-pink-500/20 text-pink-300 border border-pink-500/30">Contrarian Agent</span>
                                    <span className="px-2 py-1 text-xs rounded bg-pink-500/20 text-pink-300 border border-pink-500/30">pgvector RAG</span>
                                    <span className="px-2 py-1 text-xs rounded bg-pink-500/20 text-pink-300 border border-pink-500/30">Cause & Effect</span>
                                </div>
                            </div>
                        </div>
                    </div>

                </div>

                <ThoughtProcessFlow />

                <div className="mt-24 text-center">
                    <h2 className="text-3xl font-bold text-white mb-6">See the Results</h2>
                    <p className="text-slate-400 mb-8">
                        Explore the live portfolios and performance metrics of each agent.
                    </p>
                    <a href="/portfolios" className="inline-block px-8 py-3 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold transition-colors shadow-lg shadow-blue-900/20">
                        View Portfolios
                    </a>
                </div>
            </div>
        </div>
    )
}
