import { createFileRoute } from '@tanstack/react-router';
import _howItWorksData from '~/config/how-it-works.json';
import { MODELS } from '~/config/models';

interface HowItWorksItem {
    phase: number;
    icon: string;
    title: string;
    description: string;
    badge?: string;
    bullets?: string[];
    tags?: string[];
}

const howItWorksData = _howItWorksData as HowItWorksItem[];

import { ThoughtProcessFlow } from '../components/ThoughtProcessFlow';

export const Route = createFileRoute('/how-it-works')({
    component: HowItWorks,
});

const PHASE_THEMES: Record<
    number,
    {
        border: string;
        text: string;
        hoverBorder: string;
        textMuted: string;
        bgBadge: string;
        textBadge: string;
        borderBadge: string;
    }
> = {
    1: {
        border: 'border-blue-500',
        text: 'text-blue-500',
        hoverBorder: 'hover:border-blue-500/50',
        textMuted: 'text-blue-400',
        bgBadge: 'bg-blue-500/20',
        textBadge: 'text-blue-300',
        borderBadge: 'border-blue-500/30',
    },
    2: {
        border: 'border-indigo-500',
        text: 'text-indigo-500',
        hoverBorder: 'hover:border-indigo-500/50',
        textMuted: 'text-indigo-400',
        bgBadge: 'bg-indigo-500/20',
        textBadge: 'text-indigo-300',
        borderBadge: 'border-indigo-500/30',
    },
    3: {
        border: 'border-purple-500',
        text: 'text-purple-500',
        hoverBorder: 'hover:border-purple-500/50',
        textMuted: 'text-purple-400',
        bgBadge: 'bg-purple-500/20',
        textBadge: 'text-purple-300',
        borderBadge: 'border-purple-500/30',
    },
    4: {
        border: 'border-teal-500',
        text: 'text-teal-500',
        hoverBorder: 'hover:border-teal-500/50',
        textMuted: 'text-teal-400',
        bgBadge: 'bg-teal-500/20',
        textBadge: 'text-teal-300',
        borderBadge: 'border-teal-500/30',
    },
    5: {
        border: 'border-amber-500',
        text: 'text-amber-500',
        hoverBorder: 'hover:border-amber-500/50',
        textMuted: 'text-amber-400',
        bgBadge: 'bg-amber-500/20',
        textBadge: 'text-amber-300',
        borderBadge: 'border-amber-500/30',
    },
    6: {
        border: 'border-emerald-500',
        text: 'text-emerald-500',
        hoverBorder: 'hover:border-emerald-500/50',
        textMuted: 'text-emerald-400',
        bgBadge: 'bg-emerald-500/20',
        textBadge: 'text-emerald-300',
        borderBadge: 'border-emerald-500/30',
    },
    7: {
        border: 'border-pink-500',
        text: 'text-pink-500',
        hoverBorder: 'hover:border-pink-500/50',
        textMuted: 'text-pink-400',
        bgBadge: 'bg-pink-500/20',
        textBadge: 'text-pink-300',
        borderBadge: 'border-pink-500/30',
    },
};

const BOLD_BULLET_HEADINGS = [
    'Layer 1',
    'Layer 2',
    'Layer 3',
    'Layer 4',
    'Hard Tool Enforcement',
    'Ownership Pre-Validation',
    '50% Confidence Penalty',
    'Strategic Reasoning Audit',
    'Calendar & Seasonal Strategies',
    'FMP-Verified Market Hours',
    '5.0% Price Banding',
    'Reg T Margin Validation',
    '10% Minimum Position Rule',
    'Atomic Settlement',
    'Two-Phase Attribution Locking',
    'Real-time P&L',
    'Immediate Consistency',
    'Alpaca Broker Mirroring',
    'Manager Agent',
    'Government Tracking',
    'Cause & Effect Analysis',
    'Dynamic Ticker Discovery',
    'Long-term Memory',
    'Semantic Deduplication',
    'Global Macro Snapshot',
    'Portfolio Initialization',
    'Light Context Injection',
    'Calendar Strategy',
    'Asynchronous Chunk Batching',
    'Web Search',
    'Stock Screener',
    'DiscoveryAgent',
    'DeepSeek Thinking Mode',
    'Semantic Grouping',
    'Weighted Consensus',
    'Temporal Deduplication',
    'Relationship Analysis',
    'Trend & Momentum',
    'Scenario Analysis',
    'Horizon Watch',
    'FMP Market Status Check',
    'Dust Cleanup',
];

function HowItWorks() {
    return (
        <div className="flex flex-col min-h-screen px-4 md:px-8 py-8 text-slate-100">
            <div className="flex flex-col w-full gap-12">
                <div className="text-center flex flex-col gap-4">
                    <h1 className="text-lg font-bold font-display uppercase tracking-wider text-white">
                        How Benchify Works
                    </h1>
                    <p className="text-xs font-normal text-slate-400 max-w-2xl mx-auto">
                        Benchify is an automated arena where leading AI models compete in the stock
                        market. Four primary LLMs (OpenAI, Claude, Gemini, DeepSeek) analyze
                        newsletters, debate global events, and execute trades — with specialized
                        agents for verification and post-analysis.
                    </p>
                    <div className="flex gap-2 justify-center flex-wrap">
                        <span className="px-2.5 py-1 text-xs font-bold rounded-none bg-zinc-900 border border-zinc-700 text-zinc-300 shadow-sm">
                            OpenAI {MODELS.OPENAI}
                        </span>
                        <span className="px-2.5 py-1 text-xs font-bold rounded-none bg-zinc-900 border border-zinc-700 text-zinc-300 shadow-sm">
                            Claude {MODELS.ANTHROPIC}
                        </span>
                        <span className="px-2.5 py-1 text-xs font-bold rounded-none bg-zinc-900 border border-zinc-700 text-zinc-300 shadow-sm">
                            Gemini {MODELS.GEMINI}
                        </span>
                        <span className="px-2.5 py-1 text-xs font-bold rounded-none bg-zinc-900 border border-zinc-700 text-zinc-300 shadow-sm">
                            DeepSeek {MODELS.DEEPSEEK}
                        </span>
                        <span className="px-2.5 py-1 text-xs font-bold rounded-none bg-zinc-900 border border-zinc-700 text-zinc-300 shadow-sm">
                            MiniMax {MODELS.MINIMAX}
                        </span>
                    </div>
                    <p className="text-xs font-normal text-slate-500">
                        Tripled trigger multiple times daily during US market hours
                    </p>
                </div>

                <div className="flex flex-col gap-12 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-700 before:to-transparent">
                    {howItWorksData.map((item) => {
                        const theme =
                            PHASE_THEMES[item.phase as keyof typeof PHASE_THEMES] ||
                            PHASE_THEMES[1];
                        return (
                            <div
                                key={item.phase}
                                className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active"
                            >
                                <div
                                    className={`flex items-center justify-center w-10 h-10 rounded-none border-2 ${theme.border} bg-slate-900 shadow ${theme.text} shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-transform group-hover:scale-110`}
                                >
                                    <span className="text-sm font-bold">{item.icon}</span>
                                </div>
                                <div
                                    className={`w-full md:w-[calc(50%-2.5rem)] p-6 rounded-none bg-slate-900/60 border border-slate-800 ${theme.hoverBorder} transition-colors shadow-sm`}
                                >
                                    <div className="flex flex-col gap-2">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <span
                                                className={`${theme.textMuted} font-mono text-xs font-bold tracking-wider uppercase`}
                                            >
                                                Phase {item.phase}
                                            </span>
                                            {item.badge && (
                                                <span
                                                    className={`px-2 py-0.5 text-xs font-bold rounded-none ${theme.bgBadge} ${theme.textBadge} border ${theme.borderBadge}`}
                                                >
                                                    {item.badge}
                                                </span>
                                            )}
                                        </div>
                                        <h3 className="text-sm font-bold text-white">
                                            {item.title}
                                        </h3>
                                        <p className="text-xs font-normal text-slate-400">
                                            {item.description}
                                        </p>
                                        {item.bullets && item.bullets.length > 0 && (
                                            <ul className="flex flex-col gap-1 text-xs font-normal text-slate-400 list-disc list-inside">
                                                {item.bullets.map((bullet) => {
                                                    // Check known headings to bold the first section of the bullet point
                                                    for (const heading of BOLD_BULLET_HEADINGS) {
                                                        if (bullet.startsWith(`${heading}:`)) {
                                                            const rest = bullet.slice(
                                                                heading.length + 1,
                                                            );
                                                            return (
                                                                <li key={bullet}>
                                                                    <strong
                                                                        className={theme.textBadge}
                                                                    >
                                                                        {heading}
                                                                    </strong>
                                                                    :{rest}
                                                                </li>
                                                            );
                                                        }
                                                    }
                                                    // Fallback check: if there is a colon, split by colon for generic bullets
                                                    const parts = bullet.split(':');
                                                    if (
                                                        parts.length > 1 &&
                                                        parts[0].length < 35 &&
                                                        !parts[0].includes('(') &&
                                                        !parts[0].includes(' ')
                                                    ) {
                                                        return (
                                                            <li key={bullet}>
                                                                <strong className={theme.textBadge}>
                                                                    {parts[0]}
                                                                </strong>
                                                                :{parts.slice(1).join(':')}
                                                            </li>
                                                        );
                                                    }
                                                    return <li key={bullet}>{bullet}</li>;
                                                })}
                                            </ul>
                                        )}
                                        {item.tags && item.tags.length > 0 && (
                                            <div className="flex gap-2 flex-wrap">
                                                {item.tags.map((tag) => (
                                                    <span
                                                        key={tag}
                                                        className={`px-2 py-1 text-xs font-bold rounded-none ${theme.bgBadge} ${theme.textBadge} border ${theme.borderBadge}`}
                                                    >
                                                        {tag}
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>

                <ThoughtProcessFlow />

                <div className="text-center flex flex-col gap-4 items-center">
                    <h2 className="text-lg font-bold font-display uppercase tracking-wider text-white">
                        See the Results
                    </h2>
                    <p className="text-xs font-normal text-slate-400 max-w-md">
                        Explore the live portfolios and performance metrics of each agent.
                    </p>
                    <a
                        href="/portfolios"
                        className="inline-block px-6 py-2.5 rounded-none bg-accent hover:bg-accent/90 text-white text-xs font-bold transition-colors shadow-sm"
                    >
                        View Portfolios
                    </a>
                </div>
            </div>
        </div>
    );
}
