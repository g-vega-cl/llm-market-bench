import { Button } from '@llm-market-bench/ui-design-system';
import type React from 'react';
import { useState } from 'react';

interface Step {
    id: number;
    title: string;
    icon: string;
    description: string;
    details: React.ReactNode;
}

export function ThoughtProcessFlow() {
    const [activeStep, setActiveStep] = useState(0);

    const steps: Step[] = [
        {
            id: 0,
            title: 'Phase 1: Ingestion',
            icon: '📥',
            description: 'The engine receives a raw newsletter and cleans it for processing.',
            details: (
                <div className="space-y-4">
                    <div>
                        <span className="text-xs font-mono text-slate-500 uppercase tracking-widest">
                            Raw Input (Gmail)
                        </span>
                        <div className="mt-1 p-3 rounded bg-slate-900/80 border border-slate-700 text-xs font-mono text-slate-400 overflow-x-auto">
                            {'<html>'}... Breaking: Tesla (TSLA) Q4 deliveries exceed all analyst
                            expectations. Elon Musk hints at new AI factory in Texas. [AD: Buy the
                            best mattresses here!] ...{'</html>'}
                        </div>
                    </div>
                    <div>
                        <span className="text-xs font-mono text-emerald-500 uppercase tracking-widest">
                            Gemini De-advertised Output
                        </span>
                        <div className="mt-1 p-3 rounded bg-emerald-900/20 border border-emerald-900/50 text-xs font-mono text-emerald-300">
                            Tesla (TSLA) Q4 deliveries exceeded expectations. High probability of
                            positive earnings impact.
                        </div>
                    </div>
                </div>
            ),
        },
        {
            id: 1,
            title: 'Phase 2: RAG Retrieval',
            icon: '🧠',
            description:
                'The engine queries pgvector for historical context using Gemini embeddings.',
            details: (
                <div className="space-y-4">
                    <div>
                        <span className="text-xs font-mono text-purple-400 uppercase tracking-widest">
                            Top pgvector Matches (Similarity {'>'} 0.85)
                        </span>
                        <div className="mt-2 space-y-2">
                            <div className="p-3 rounded bg-slate-900/80 border-l-2 border-purple-500 text-xs text-slate-300">
                                <span className="text-purple-400 font-bold">[MARKET EVENT]</span>{' '}
                                Oct 2024: TSLA Q3 earnings beat led to 12% price surge over 5 days.
                            </div>
                            <div className="p-3 rounded bg-slate-900/80 border-l-2 border-purple-500 text-xs text-slate-300">
                                <span className="text-purple-400 font-bold">[LESSON LEARNED]</span>{' '}
                                "Avoid TSLA during trade war rhetoric even with delivery beats."
                                (Manager Agent, Dec 2024)
                            </div>
                        </div>
                    </div>
                </div>
            ),
        },
        {
            id: 2,
            title: 'Phase 3: LLM Analysis',
            icon: '🤖',
            description: 'Claude 4.5 Sonnet analyzes the data and uses live market tools.',
            details: (
                <div className="space-y-4">
                    <div>
                        <span className="text-xs font-mono text-blue-400 uppercase tracking-widest">
                            Provider: Anthropic / Claude-3-5-Sonnet
                        </span>
                        <div className="mt-2 p-3 rounded bg-slate-900 border border-slate-700 italic text-sm text-slate-300">
                            "The Q4 delivery beat is a massive catalyst. Based on historical context
                            from Oct 2024, I expect momentum. Calling tool to verify current
                            liquidity..."
                        </div>
                    </div>
                    <div className="flex items-center gap-3 p-2 rounded bg-blue-900/20 border border-blue-900/50 text-xs font-mono text-blue-300">
                        <span className="animate-pulse">🛠️</span>
                        <span>
                            get_stock_quote(ticker: "TSLA") -{'>'} <b>$248.50</b> (Mkt Cap: $789B)
                        </span>
                    </div>
                    <div className="p-2 px-3 rounded bg-emerald-500/20 text-emerald-400 font-bold text-center border border-emerald-500/30">
                        SIGNAL: BUY | CONFIDENCE: 88%
                    </div>
                </div>
            ),
        },
        {
            id: 3,
            title: 'Phase 4: Skeptical Audit',
            icon: '🛡️',
            description: "A skeptic audits the decision to ensure it's not a hallucination.",
            details: (
                <div className="space-y-4">
                    <div>
                        <span className="text-xs font-mono text-amber-500 uppercase tracking-widest">
                            Audit SOP: "Silver to our Gold"
                        </span>
                        <div className="mt-2 p-3 rounded bg-slate-900 border border-slate-700 text-xs text-slate-300">
                            "Signal verified. However, volatility is high (IV: 45%). Checking
                            alternative sector plays to hedge risk..."
                        </div>
                    </div>
                    <div className="flex items-center gap-3 p-2 rounded bg-amber-900/20 border border-amber-900/50 text-xs font-mono text-amber-300">
                        <span>🛠️</span>
                        <span>
                            get_sector_alternatives(ticker: "TSLA") -{'>'} <b>RIVN, LCID</b>
                        </span>
                    </div>
                    <div className="p-2 px-3 rounded bg-blue-500/20 text-blue-400 font-bold text-center border border-blue-500/30 text-sm">
                        STATUS: APPROVED (ADJUSTED ALLOCATION - 5% → 3%)
                    </div>
                </div>
            ),
        },
        {
            id: 4,
            title: 'Phase 5: Trade Execution',
            icon: '⚖️',
            description: 'The engine validates margin and commits the trade to the ledger.',
            details: (
                <div className="flex flex-col gap-4">
                    <div className="grid grid-cols-2 gap-2 text-xs font-mono uppercase">
                        <div className="p-2 bg-slate-900/50 border border-slate-800 rounded-none shadow-sm">
                            Reg T Check: <span className="text-emerald-500 font-bold">Passed</span>
                        </div>
                        <div className="p-2 bg-slate-900/50 border border-slate-800 rounded-none shadow-sm">
                            Margin Check: <span className="text-emerald-500 font-bold">Passed</span>
                        </div>
                    </div>
                    <div className="p-4 rounded-none bg-slate-900/80 border border-emerald-500/30 shadow-sm flex flex-col gap-2">
                        <div className="flex justify-between items-center">
                            <span className="text-emerald-400 font-bold text-xs">
                                TRADE EXECUTED
                            </span>
                            <span className="text-xs font-mono text-slate-500">ID: tr_8a92f2</span>
                        </div>
                        <div className="text-lg font-bold font-mono text-white">BUY TSLA</div>
                        <div className="text-xs font-normal text-slate-400">
                            40 shares @ $248.50 | Total: $9,940.00
                        </div>
                        <div className="pt-3 border-t border-slate-700/50 text-xs font-normal text-slate-500 italic">
                            Attribution Locked: Decision reasoning linked to Trade ID.
                        </div>
                    </div>
                </div>
            ),
        },
    ];

    return (
        <section className="mt-12 py-12 px-6 rounded-none bg-slate-900/40 border border-slate-800 backdrop-blur-md relative overflow-hidden shadow-sm">
            <div className="absolute top-0 right-0 -translate-y-1/2 translate-x-1/3 w-96 h-96 bg-blue-500/10 blur-3xl pointer-events-none" />

            <div className="max-w-4xl mx-auto flex flex-col gap-8">
                <div className="text-center flex flex-col gap-2">
                    <h2 className="text-lg font-bold font-display uppercase tracking-wider text-white">
                        Deep Dive: Follow a Single Thought
                    </h2>
                    <p className="text-slate-400 text-xs font-normal">
                        Click through the actual data flow of a real-world TSLA trade generated by
                        Benchify.
                    </p>
                </div>

                <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,8rem),1fr))] gap-4 items-stretch">
                    {steps.map((step, idx) => (
                        <Button
                            key={step.id}
                            variant={activeStep === idx ? 'solid' : 'outline'}
                            colorScheme="info"
                            className="flex-col p-4 rounded-none transition-all duration-300 shadow-sm"
                            onClick={() => setActiveStep(idx)}
                        >
                            <span
                                className={`text-lg mb-2 transition-transform duration-300 ${activeStep === idx ? 'scale-125' : 'group-hover:scale-110'}`}
                            >
                                {step.icon}
                            </span>
                            <span
                                className={`text-xs font-bold uppercase tracking-widest text-center ${activeStep === idx ? 'text-blue-400' : 'text-slate-500'}`}
                            >
                                Step {idx + 1}
                            </span>
                        </Button>
                    ))}
                </div>

                <div className="relative min-h-[350px] flex items-center justify-center">
                    {steps.map((step, idx) => (
                        <div
                            key={step.id}
                            className={`absolute inset-0 transition-all duration-500 flex flex-col md:flex-row gap-8 items-center ${
                                activeStep === idx
                                    ? 'opacity-100 translate-y-0 pointer-events-auto'
                                    : 'opacity-0 translate-y-8 pointer-events-none'
                            }`}
                        >
                            <div className="w-full md:w-1/3 text-center md:text-left flex flex-col gap-2">
                                <span className="text-blue-500 font-mono text-xs font-bold uppercase tracking-widest block">
                                    {step.title}
                                </span>
                                <h3 className="text-sm font-bold text-white leading-tight">
                                    {step.description}
                                </h3>
                                <div className="hidden md:flex flex-wrap gap-2 mt-auto">
                                    <div className="w-1.5 h-1.5 rounded-none bg-blue-500 animate-pulse" />
                                    <div className="w-1.5 h-1.5 rounded-none bg-blue-500/60" />
                                    <div className="w-1.5 h-1.5 rounded-none bg-blue-500/30" />
                                </div>
                            </div>
                            <div className="w-full md:w-2/3 p-6 rounded-none bg-slate-900/60 border border-slate-800 shadow-sm relative flex flex-col gap-4">
                                <div className="absolute top-0 right-0 p-3 opacity-10">
                                    <span className="text-lg font-bold">{step.icon}</span>
                                </div>
                                {step.details}
                            </div>
                        </div>
                    ))}
                </div>

                <div className="flex justify-between items-center border-t border-slate-800 pt-6">
                    <Button
                        variant="outline"
                        colorScheme="neutral"
                        className="px-6 py-2 text-xs font-bold"
                        disabled={activeStep === 0}
                        onClick={() => setActiveStep((prev) => Math.max(0, prev - 1))}
                    >
                        ← Prev
                    </Button>
                    <div className="flex gap-1.5">
                        {steps.map((_, idx) => (
                            <div
                                key={idx}
                                className={`h-2 transition-all duration-300 rounded-none ${activeStep === idx ? 'bg-blue-500 w-6' : 'bg-slate-700 w-2'}`}
                            />
                        ))}
                    </div>
                    <Button
                        colorScheme="info"
                        className="px-6 py-2 text-xs font-bold shadow-sm"
                        disabled={activeStep === steps.length - 1}
                        onClick={() =>
                            setActiveStep((prev) => Math.min(steps.length - 1, prev + 1))
                        }
                    >
                        Next →
                    </Button>
                </div>
            </div>
        </section>
    );
}
