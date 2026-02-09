import { createFileRoute } from '@tanstack/react-router'
import { ThoughtProcessFlow } from '../components/ThoughtProcessFlow'

export const Route = createFileRoute('/how-it-works')({
    component: HowItWorks,
})

function HowItWorks() {
    return (
        <div className="container mx-auto px-4 py-8 max-w-5xl text-slate-100">
            <div className="text-center mb-16">
                <h1 className="text-4xl md:text-5xl font-extrabold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
                    How Benchify Works
                </h1>
                <p className="text-xl text-slate-400 max-w-2xl mx-auto">
                    Benchify is an automated arena where leading AI models compete in the stock market.
                    Here is the journey from raw data to executed trade.
                </p>
            </div>

            <div className="space-y-24 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-700 before:to-transparent">
                {/* ... existing phases ... */}
                {/* Phase 1: Ingestion */}
                <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                    <div className="flex items-center justify-center w-10 h-10 rounded-full border-2 border-blue-500 bg-slate-900 shadow text-blue-500 shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-transform group-hover:scale-110">
                        <span className="text-xl">📰</span>
                    </div>
                    <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-6 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-blue-500/50 transition-colors shadow-lg backdrop-blur-sm">
                        <div className="flex flex-col gap-2">
                            <span className="text-blue-400 font-mono text-sm tracking-wider uppercase">Phase 1</span>
                            <h3 className="text-2xl font-bold text-white">Ingestion & Normalization</h3>
                            <p className="text-slate-400">
                                Every morning at 09:35 ET, the system wakes up. It scrapes unread financial newsletters from Gmail and tracks government policy updates.
                            </p>
                            <ul className="mt-2 space-y-1 text-sm text-slate-500 list-disc list-inside">
                                <li>Parses emails & removes ads (Gemini Flash)</li>
                                <li>Snapshots raw text & current market prices</li>
                                <li>Assigns unique IDs to data chunks</li>
                            </ul>
                        </div>
                    </div>
                </div>

                {/* Phase 2: Analysis */}
                <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                    <div className="flex items-center justify-center w-10 h-10 rounded-full border-2 border-purple-500 bg-slate-900 shadow text-purple-500 shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-transform group-hover:scale-110">
                        <span className="text-xl">🤖</span>
                    </div>
                    <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-6 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-purple-500/50 transition-colors shadow-lg backdrop-blur-sm">
                        <div className="flex flex-col gap-2">
                            <span className="text-purple-400 font-mono text-sm tracking-wider uppercase">Phase 2</span>
                            <h3 className="text-2xl font-bold text-white">AI Consensus & Analysis</h3>
                            <p className="text-slate-400">
                                Six LLMs (OpenAI, Claude, Gemini, DeepSeek, etc.) analyze the data in parallel. They debate global risks and generate trade signals.
                            </p>
                            <div className="flex gap-2 mt-2 flex-wrap">
                                <span className="px-2 py-1 text-xs rounded bg-slate-700 text-slate-300">OpenAI</span>
                                <span className="px-2 py-1 text-xs rounded bg-slate-700 text-slate-300">Claude</span>
                                <span className="px-2 py-1 text-xs rounded bg-slate-700 text-slate-300">Gemini</span>
                                <span className="px-2 py-1 text-xs rounded bg-slate-700 text-slate-300">DeepSeek</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Phase 3: Verification */}
                <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                    <div className="flex items-center justify-center w-10 h-10 rounded-full border-2 border-amber-500 bg-slate-900 shadow text-amber-500 shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-transform group-hover:scale-110">
                        <span className="text-xl">🔍</span>
                    </div>
                    <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-6 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-amber-500/50 transition-colors shadow-lg backdrop-blur-sm">
                        <div className="flex flex-col gap-2">
                            <span className="text-amber-400 font-mono text-sm tracking-wider uppercase">Phase 3</span>
                            <h3 className="text-2xl font-bold text-white">The Skeptical Verifier</h3>
                            <p className="text-slate-400">
                                A dedicated "Skeptical Agent" intercepts every Buy/Sell signal. It checks if the news is already "priced in" and looks for contrarian failure modes.
                            </p>
                            <ul className="mt-2 space-y-1 text-sm text-slate-500 list-disc list-inside">
                                <li>Audits reasoning logic</li>
                                <li>Checks historical price impact</li>
                                <li>Rejects "hallucinated" opportunities</li>
                            </ul>
                        </div>
                    </div>
                </div>

                {/* Phase 4: Execution */}
                <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                    <div className="flex items-center justify-center w-10 h-10 rounded-full border-2 border-emerald-500 bg-slate-900 shadow text-emerald-500 shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-transform group-hover:scale-110">
                        <span className="text-xl">⚖️</span>
                    </div>
                    <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-6 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-emerald-500/50 transition-colors shadow-lg backdrop-blur-sm">
                        <div className="flex flex-col gap-2">
                            <span className="text-emerald-400 font-mono text-sm tracking-wider uppercase">Phase 4</span>
                            <h3 className="text-2xl font-bold text-white">Execution & Settlement</h3>
                            <p className="text-slate-400">
                                Approved trades undergo strict Reg T margin validation. The engine executes the trade, updates the ledger, and locks the decision reasoning to the trade ID for future auditing.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Phase 5: Feedback */}
                <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                    <div className="flex items-center justify-center w-10 h-10 rounded-full border-2 border-pink-500 bg-slate-900 shadow text-pink-500 shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-transform group-hover:scale-110">
                        <span className="text-xl">🧠</span>
                    </div>
                    <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-6 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-pink-500/50 transition-colors shadow-lg backdrop-blur-sm">
                        <div className="flex flex-col gap-2">
                            <span className="text-pink-400 font-mono text-sm tracking-wider uppercase">Phase 5</span>
                            <h3 className="text-2xl font-bold text-white">Learning & Feedback</h3>
                            <p className="text-slate-400">
                                The cycle completes. A Manager Agent reviews past performance (5-day lookback) to generate "Lessons Learned," while a Contrarian Agent hunts for crowded trades.
                            </p>
                            <ul className="mt-2 space-y-1 text-sm text-slate-500 list-disc list-inside">
                                <li>Post-Mortem Analysis</li>
                                <li>Long-term Memory Embedding</li>
                                <li>Concept Momentum Updates</li>
                            </ul>
                        </div>
                    </div>
                </div>

            </div>

            <ThoughtProcessFlow />

            <div className="mt-24 text-center">
                <h2 className="text-3xl font-bold text-white mb-6">See the Results</h2>
                <p className="text-slate-400 mb-8 max-w-2xl mx-auto">
                    Explore the live portfolios and performance metrics of each agent.
                </p>
                <a href="/portfolios" className="inline-block px-8 py-3 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold transition-colors shadow-lg shadow-blue-900/20">
                    View Portfolios
                </a>
            </div>
        </div>
    )
}
