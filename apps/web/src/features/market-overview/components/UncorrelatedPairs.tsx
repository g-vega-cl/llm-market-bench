import { Button, Card } from '@llm-market-bench/ui-design-system';
import * as React from 'react';
import type { CorrelationData } from '../api/fetch-market-overview';

interface UncorrelatedPairsProps {
    correlationData: CorrelationData[];
}

export function UncorrelatedPairs({ correlationData }: UncorrelatedPairsProps) {
    const [maxCorrelation, setMaxCorrelation] = React.useState(0.3);
    const [minReturn, setMinReturn] = React.useState(0);
    const [method, setMethod] = React.useState<'pearson' | 'spearman'>('pearson');
    const [sortBy, setSortBy] = React.useState<'correlation' | 'return'>('correlation');

    const filteredPairs = React.useMemo(() => {
        return correlationData
            .filter((c) => {
                const corr = method === 'pearson' ? c.pearson_corr : c.spearman_corr;
                if (corr === null) return false;
                if (Math.abs(corr) > maxCorrelation) return false;
                if (c.returns_a_90d === null || c.returns_b_90d === null) return false;
                if (c.returns_a_90d < minReturn || c.returns_b_90d < minReturn) return false;
                return true;
            })
            .map((c) => ({
                ...c,
                absCorrelation: Math.abs(
                    method === 'pearson' ? (c.pearson_corr ?? 1) : (c.spearman_corr ?? 1),
                ),
                avgReturn: ((c.returns_a_90d ?? 0) + (c.returns_b_90d ?? 0)) / 2,
            }))
            .sort((a, b) => {
                if (sortBy === 'correlation') {
                    return a.absCorrelation - b.absCorrelation;
                } else {
                    return b.avgReturn - a.avgReturn;
                }
            });
    }, [correlationData, maxCorrelation, minReturn, method, sortBy]);

    const getCorrelationColor = (corr: number | null): string => {
        if (corr === null) return 'text-zinc-400';
        if (Math.abs(corr) < 0.1) return 'text-blue-500 font-bold';
        if (Math.abs(corr) < 0.3) return 'text-blue-400';
        return 'text-zinc-600 dark:text-zinc-400';
    };

    const getReturnColor = (ret: number | null): string => {
        if (ret === null) return 'text-zinc-400';
        if (ret > 0) return 'text-neon-green-500';
        return 'text-alert-red-400';
    };

    return (
        <section>
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-zinc-800 dark:text-zinc-100 tracking-tight">
                    Uncorrelated Pairs with Positive Momentum
                </h2>
            </div>

            <Card variant="default" padding="none" className="overflow-hidden">
                <div className="p-6 border-b border-zinc-200 dark:border-zinc-800">
                    <div className="flex flex-wrap items-center gap-6">
                        <div className="flex items-center gap-3">
                            <label htmlFor="max-corr-slider" className="text-sm text-zinc-500">
                                Max Correlation:
                            </label>
                            <input
                                id="max-corr-slider"
                                type="range"
                                min="0"
                                max="0.8"
                                step="0.05"
                                value={maxCorrelation}
                                onChange={(e) => setMaxCorrelation(parseFloat(e.target.value))}
                                className="w-32"
                            />
                            <span className="text-sm font-mono font-semibold w-12">
                                {maxCorrelation.toFixed(2)}
                            </span>
                        </div>

                        <div className="flex items-center gap-3">
                            <label htmlFor="min-return-slider" className="text-sm text-zinc-500">
                                Min 90d Return:
                            </label>
                            <input
                                id="min-return-slider"
                                type="range"
                                min="-10"
                                max="20"
                                step="1"
                                value={minReturn}
                                onChange={(e) => setMinReturn(parseFloat(e.target.value))}
                                className="w-32"
                            />
                            <span className="text-sm font-mono font-semibold w-12">
                                {minReturn}%
                            </span>
                        </div>

                        <div className="flex items-center gap-2">
                            <span className="text-sm text-zinc-500">Method:</span>
                            <Button
                                rounded="full"
                                size="sm"
                                variant={method === 'pearson' ? 'solid' : 'soft'}
                                colorScheme={method === 'pearson' ? 'accent' : 'neutral'}
                                onClick={() => setMethod('pearson')}
                            >
                                Pearson
                            </Button>
                            <Button
                                rounded="full"
                                size="sm"
                                variant={method === 'spearman' ? 'solid' : 'soft'}
                                colorScheme={method === 'spearman' ? 'accent' : 'neutral'}
                                onClick={() => setMethod('spearman')}
                            >
                                Spearman
                            </Button>
                        </div>

                        <div className="flex items-center gap-2">
                            <span className="text-sm text-zinc-500">Sort by:</span>
                            <Button
                                rounded="full"
                                size="sm"
                                variant={sortBy === 'correlation' ? 'solid' : 'soft'}
                                colorScheme={sortBy === 'correlation' ? 'accent' : 'neutral'}
                                onClick={() => setSortBy('correlation')}
                            >
                                Lowest Correlation
                            </Button>
                            <Button
                                rounded="full"
                                size="sm"
                                variant={sortBy === 'return' ? 'solid' : 'soft'}
                                colorScheme={sortBy === 'return' ? 'accent' : 'neutral'}
                                onClick={() => setSortBy('return')}
                            >
                                Highest Return
                            </Button>
                        </div>
                    </div>
                </div>

                {filteredPairs.length === 0 ? (
                    <div className="p-12 text-center">
                        <p className="text-zinc-500">No pairs match the current filters.</p>
                        <p className="text-sm text-zinc-400 mt-2">
                            Try increasing the max correlation threshold.
                        </p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead className="bg-zinc-50 dark:bg-zinc-800/50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-bold text-zinc-500 uppercase tracking-wider">
                                        Pair
                                    </th>
                                    <th className="px-6 py-3 text-center text-xs font-bold text-zinc-500 uppercase tracking-wider">
                                        Pearson
                                    </th>
                                    <th className="px-6 py-3 text-center text-xs font-bold text-zinc-500 uppercase tracking-wider">
                                        Spearman
                                    </th>
                                    <th className="px-6 py-3 text-right text-xs font-bold text-zinc-500 uppercase tracking-wider">
                                        90d Return A
                                    </th>
                                    <th className="px-6 py-3 text-right text-xs font-bold text-zinc-500 uppercase tracking-wider">
                                        90d Return B
                                    </th>
                                    <th className="px-6 py-3 text-right text-xs font-bold text-zinc-500 uppercase tracking-wider">
                                        Avg Return
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
                                {filteredPairs.slice(0, 50).map((pair, idx) => (
                                    <tr
                                        key={`${pair.ticker_a}-${pair.ticker_b}`}
                                        className={`hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors ${idx === 0 ? 'bg-blue-50 dark:bg-blue-900/10' : ''}`}
                                    >
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center gap-2">
                                                <span className="font-mono font-bold text-zinc-800 dark:text-zinc-100">
                                                    {pair.ticker_a}
                                                </span>
                                                <span className="text-zinc-400">/</span>
                                                <span className="font-mono font-bold text-zinc-800 dark:text-zinc-100">
                                                    {pair.ticker_b}
                                                </span>
                                                {idx === 0 && (
                                                    <span className="px-2 py-0.5 bg-blue-500/20 text-blue-600 dark:text-blue-400 text-xs font-bold rounded-full">
                                                        BEST
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        <td
                                            className={`px-6 py-4 text-center font-mono font-semibold ${getCorrelationColor(pair.pearson_corr)}`}
                                        >
                                            {pair.pearson_corr?.toFixed(4) ?? 'N/A'}
                                        </td>
                                        <td
                                            className={`px-6 py-4 text-center font-mono font-semibold ${getCorrelationColor(pair.spearman_corr)}`}
                                        >
                                            {pair.spearman_corr?.toFixed(4) ?? 'N/A'}
                                        </td>
                                        <td
                                            className={`px-6 py-4 text-right font-mono font-semibold ${getReturnColor(pair.returns_a_90d)}`}
                                        >
                                            {pair.returns_a_90d?.toFixed(2) ?? 'N/A'}%
                                        </td>
                                        <td
                                            className={`px-6 py-4 text-right font-mono font-semibold ${getReturnColor(pair.returns_b_90d)}`}
                                        >
                                            {pair.returns_b_90d?.toFixed(2) ?? 'N/A'}%
                                        </td>
                                        <td
                                            className={`px-6 py-4 text-right font-mono font-semibold ${getReturnColor(pair.avgReturn)}`}
                                        >
                                            {pair.avgReturn.toFixed(2)}%
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {filteredPairs.length > 50 && (
                    <div className="p-4 border-t border-zinc-200 dark:border-zinc-800 text-center text-sm text-zinc-500">
                        Showing top 50 of {filteredPairs.length} pairs
                    </div>
                )}
            </Card>

            <div className="mt-6 p-4 bg-zinc-100 dark:bg-zinc-800/50 rounded-xl">
                <h3 className="text-sm font-bold text-zinc-700 dark:text-zinc-300 mb-2">
                    💡 Strategy Note
                </h3>
                <p className="text-sm text-zinc-600 dark:text-zinc-400">
                    The most uncorrelated pair with positive returns is highlighted in blue. This
                    combination of assets would have provided diversification benefits during the
                    90-day window while still generating positive returns. The XLK/XLE strategy
                    (Technology + Energy) is a classic example of this approach.
                </p>
            </div>
        </section>
    );
}
