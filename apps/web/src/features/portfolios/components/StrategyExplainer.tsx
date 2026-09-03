import { Badge, Card } from '@llm-market-bench/ui-design-system';
import * as React from 'react';

interface StrategyExplainerProps {
    ownerId: string;
}

export function StrategyExplainer({ ownerId }: StrategyExplainerProps) {
    const [isExpanded, setIsExpanded] = React.useState(true);

    if (ownerId === 'sys-smid-quality-compounder') {
        return (
            <Card
                variant="glass"
                padding="md"
                className="border border-emerald-500/20 bg-emerald-950/10"
            >
                <button
                    type="button"
                    className="w-full flex items-center justify-between text-left select-none cursor-pointer"
                    onClick={() => setIsExpanded(!isExpanded)}
                >
                    <div className="flex items-center gap-2.5">
                        <span className="text-xl">🌱</span>
                        <div>
                            <h3 className="text-base font-bold text-zinc-900 dark:text-white flex items-center gap-2">
                                Small/Mid-Cap Quality Compounder Strategy
                                <Badge variant="glass" size="xs" colorScheme="success">
                                    Zero-Ceiling Invariant
                                </Badge>
                            </h3>
                            <p className="text-xs text-zinc-500 dark:text-zinc-400">
                                Overcoming the Russell 2000 reconstitution bleed via quality
                                filtering and multi-bagger retention.
                            </p>
                        </div>
                    </div>
                    <span className="text-xs text-zinc-400 hover:text-zinc-200 transition-colors px-2 py-1 rounded">
                        {isExpanded ? 'Collapse ▲' : 'Details ▼'}
                    </span>
                </button>

                {isExpanded && (
                    <div className="mt-4 pt-4 border-t border-zinc-200/20 dark:border-zinc-800 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
                        <div className="space-y-1.5 p-3 rounded-lg bg-zinc-100/50 dark:bg-zinc-900/50">
                            <span className="font-semibold text-zinc-700 dark:text-zinc-200 flex items-center gap-1.5">
                                📚 Academic Thesis
                            </span>
                            <p className="text-zinc-600 dark:text-zinc-400 leading-relaxed">
                                Grounded in Asness et al. (2018){' '}
                                <em>"Size Matters, If You Control Your Junk"</em> and Chen, Noronha,
                                & Singal (2006). Eliminates the ~1.8% annual Russell reconstitution
                                front-running loss and weeds out unprofitable zombies.
                            </p>
                        </div>

                        <div className="space-y-1.5 p-3 rounded-lg bg-zinc-100/50 dark:bg-zinc-900/50">
                            <span className="font-semibold text-zinc-700 dark:text-zinc-200 flex items-center gap-1.5">
                                🎯 Entry Screen ($1B–$10B)
                            </span>
                            <p className="text-zinc-600 dark:text-zinc-400 leading-relaxed">
                                S&P 600 rule: 4 quarters positive GAAP Net Income + positive Free
                                Cash Flow + ROIC &gt; 10% + top quintile 12-month relative momentum.
                                Target portfolio of 25 to 30 concentrated compounders.
                            </p>
                        </div>

                        <div className="space-y-1.5 p-3 rounded-lg bg-zinc-100/50 dark:bg-zinc-900/50">
                            <span className="font-semibold text-zinc-700 dark:text-zinc-200 flex items-center gap-1.5">
                                🚀 The Zero-Ceiling Rule
                            </span>
                            <p className="text-zinc-600 dark:text-zinc-400 leading-relaxed">
                                When a holding grows into a large cap ($20B, $50B, $100B+), it is{' '}
                                <strong>never sold for size reasons</strong>. Bessembinder (2018)
                                showed that 4% of stocks generate all net market wealth;
                                multi-baggers ride indefinitely.
                            </p>
                        </div>

                        <div className="space-y-1.5 p-3 rounded-lg bg-zinc-100/50 dark:bg-zinc-900/50">
                            <span className="font-semibold text-zinc-700 dark:text-zinc-200 flex items-center gap-1.5">
                                🛑 Strict Exit Discipline
                            </span>
                            <p className="text-zinc-600 dark:text-zinc-400 leading-relaxed">
                                Positions are only liquidated if fundamentals break: trailing
                                12-month net income turns negative, 2 consecutive quarters of
                                negative cash flow, or debt leverage spikes. Rebalances quarterly
                                following SEC 10-Q deadlines.
                            </p>
                        </div>
                    </div>
                )}
            </Card>
        );
    }

    if (ownerId === 'sys-sector-ls-consensus') {
        return (
            <Card variant="glass" padding="md" className="border border-blue-500/20 bg-blue-950/10">
                <button
                    type="button"
                    className="w-full flex items-center justify-between text-left select-none cursor-pointer"
                    onClick={() => setIsExpanded(!isExpanded)}
                >
                    <div className="flex items-center gap-2.5">
                        <span className="text-xl">⚖️</span>
                        <div>
                            <h3 className="text-base font-bold text-zinc-900 dark:text-white flex items-center gap-2">
                                Weekly Sector Long/Short Consensus Strategy
                                <Badge variant="glass" size="xs" colorScheme="info">
                                    Market Neutral Tilt
                                </Badge>
                            </h3>
                            <p className="text-xs text-zinc-500 dark:text-zinc-400">
                                Mechanical sector rotation allocating 50% long to predicted best
                                sectors and 50% short to predicted worst sectors.
                            </p>
                        </div>
                    </div>
                    <span className="text-xs text-zinc-400 hover:text-zinc-200 transition-colors px-2 py-1 rounded">
                        {isExpanded ? 'Collapse ▲' : 'Details ▼'}
                    </span>
                </button>

                {isExpanded && (
                    <div className="mt-4 pt-4 border-t border-zinc-200/20 dark:border-zinc-800 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                        <div className="space-y-1.5 p-3 rounded-lg bg-zinc-100/50 dark:bg-zinc-900/50">
                            <span className="font-semibold text-zinc-700 dark:text-zinc-200">
                                📊 Consensus Signal
                            </span>
                            <p className="text-zinc-600 dark:text-zinc-400 leading-relaxed">
                                Aggregates weekly predictions from multi-model sector arenas across
                                major US sector ETFs (XLE, XLF, XLK, XLI, XLP, XLY, XLU, XLV, XLB,
                                XLC, XBI, XOP).
                            </p>
                        </div>

                        <div className="space-y-1.5 p-3 rounded-lg bg-zinc-100/50 dark:bg-zinc-900/50">
                            <span className="font-semibold text-zinc-700 dark:text-zinc-200">
                                ⚔️ Conflict Netting
                            </span>
                            <p className="text-zinc-600 dark:text-zinc-400 leading-relaxed">
                                If any sector ETF appears in both predicted best and predicted worst
                                sets across models, it is dropped from both sides to eliminate
                                contradictory exposures.
                            </p>
                        </div>

                        <div className="space-y-1.5 p-3 rounded-lg bg-zinc-100/50 dark:bg-zinc-900/50">
                            <span className="font-semibold text-zinc-700 dark:text-zinc-200">
                                ⏱️ Execution Cadence
                            </span>
                            <p className="text-zinc-600 dark:text-zinc-400 leading-relaxed">
                                Entered at Monday market open and liquidated at Friday close with 5
                                bps slippage, isolating weekly cross-sectional sector dispersion.
                            </p>
                        </div>
                    </div>
                )}
            </Card>
        );
    }

    if (ownerId.startsWith('sys-daily-spy-')) {
        return (
            <Card
                variant="glass"
                padding="md"
                className="border border-amber-500/20 bg-amber-950/10"
            >
                <button
                    type="button"
                    className="w-full flex items-center justify-between text-left select-none cursor-pointer"
                    onClick={() => setIsExpanded(!isExpanded)}
                >
                    <div className="flex items-center gap-2.5">
                        <span className="text-xl">⚡</span>
                        <div>
                            <h3 className="text-base font-bold text-zinc-900 dark:text-white flex items-center gap-2">
                                Daily S&P 500 Intraday Trader
                                <Badge variant="glass" size="xs" colorScheme="warning">
                                    Intraday 100% Equity
                                </Badge>
                            </h3>
                            <p className="text-xs text-zinc-500 dark:text-zinc-400">
                                Systematic day trading on SPY executing at 9:30 AM ET open with
                                profit target limit orders and 3:30 PM time exits.
                            </p>
                        </div>
                    </div>
                    <span className="text-xs text-zinc-400 hover:text-zinc-200 transition-colors px-2 py-1 rounded">
                        {isExpanded ? 'Collapse ▲' : 'Details ▼'}
                    </span>
                </button>
            </Card>
        );
    }

    return null;
}
