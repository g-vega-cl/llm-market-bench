import { Button, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import * as React from 'react';
import type { CorrelationData } from '../api/fetch-market-overview';
import { etfDescriptions } from '../utils/etf-descriptions';

interface HoveredCell {
    ticker_a: string;
    ticker_b: string;
    pearson_corr: number | null;
    spearman_corr: number | null;
    returns_a_90d: number | null;
    returns_b_90d: number | null;
}

interface CorrelationHeatmapProps {
    correlationData: CorrelationData[];
    tickers: string[];
}

export function CorrelationHeatmap({ correlationData, tickers }: CorrelationHeatmapProps) {
    const [hoveredCell, setHoveredCell] = React.useState<HoveredCell | null>(null);
    const [method, setMethod] = React.useState<'pearson' | 'spearman'>('pearson');

    // Build matrix
    const matrix = React.useMemo(() => {
        const corrMap: Record<string, Record<string, number>> = {};

        for (const ticker of tickers) {
            corrMap[ticker] = {};
            for (const otherTicker of tickers) {
                if (ticker === otherTicker) {
                    corrMap[ticker][otherTicker] = 1;
                } else {
                    // Look up the correlation
                    const entry = correlationData.find(
                        (c) =>
                            (c.ticker_a === ticker && c.ticker_b === otherTicker) ||
                            (c.ticker_a === otherTicker && c.ticker_b === ticker),
                    );
                    corrMap[ticker][otherTicker] = entry
                        ? ((method === 'pearson' ? entry.pearson_corr : entry.spearman_corr) ?? 0)
                        : 0;
                }
            }
        }

        return corrMap;
    }, [correlationData, tickers, method]);

    const getColor = (value: number): string => {
        // Red for high positive, blue for negative/uncorrelated
        if (value >= 0.7) return 'bg-rose-500';
        if (value >= 0.4) return 'bg-rose-400';
        if (value >= 0.2) return 'bg-rose-300';
        if (value >= 0) return 'bg-zinc-200';
        if (value >= -0.2) return 'bg-blue-100';
        if (value >= -0.4) return 'bg-blue-300';
        if (value >= -0.6) return 'bg-blue-500';
        return 'bg-blue-700';
    };

    const getTextColor = (value: number): string => {
        return value > 0.5 || value < -0.5 ? 'text-white' : 'text-zinc-800';
    };

    // For large matrices, we might want to show a simplified version
    const showSimplified = tickers.length > 20;

    return (
        <section>
            <div className="flex items-center justify-between mb-6">
                <SectionHeading gradient="ai">Correlation Matrix</SectionHeading>
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 text-sm">
                        <span className="text-zinc-500">Method:</span>
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
                </div>
            </div>

            <Card variant="default" padding="md" className="overflow-x-auto">
                {showSimplified ? (
                    <SimplifiedMatrix
                        matrix={matrix}
                        tickers={tickers}
                        getColor={getColor}
                        getTextColor={getTextColor}
                        onHover={setHoveredCell}
                    />
                ) : (
                    <FullMatrix
                        matrix={matrix}
                        tickers={tickers}
                        getColor={getColor}
                        getTextColor={getTextColor}
                        onHover={setHoveredCell}
                    />
                )}

                <div className="flex items-center justify-center gap-6 mt-6 pt-4 border-t border-zinc-200 dark:border-zinc-800">
                    <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded bg-blue-700" />
                        <span className="text-xs text-zinc-500">-1.0 (Inverse)</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded bg-zinc-200" />
                        <span className="text-xs text-zinc-500">0.0 (Uncorrelated)</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded bg-rose-500" />
                        <span className="text-xs text-zinc-500">+1.0 (Perfect)</span>
                    </div>
                </div>
            </Card>

            {hoveredCell && (
                <div className="mt-4 p-4 bg-zinc-100 dark:bg-zinc-800 rounded-lg border border-zinc-200 dark:border-zinc-700">
                    <div className="flex items-center gap-4 text-sm">
                        <div className="flex flex-col gap-0.5">
                            <span className="font-mono font-bold text-zinc-900 dark:text-zinc-100">
                                {hoveredCell.ticker_a}
                            </span>
                            <span className="text-[10px] text-zinc-500 dark:text-zinc-400 max-w-[120px] truncate">
                                {etfDescriptions[hoveredCell.ticker_a] || 'Unknown'}
                            </span>
                        </div>
                        <span className="text-zinc-400">/</span>
                        <div className="flex flex-col gap-0.5">
                            <span className="font-mono font-bold text-zinc-900 dark:text-zinc-100">
                                {hoveredCell.ticker_b}
                            </span>
                            <span className="text-[10px] text-zinc-500 dark:text-zinc-400 max-w-[120px] truncate">
                                {etfDescriptions[hoveredCell.ticker_b] || 'Unknown'}
                            </span>
                        </div>
                        <span className="text-zinc-300 ml-2">|</span>
                        <span>
                            Pearson:{' '}
                            <span className="font-semibold">
                                {hoveredCell.pearson_corr?.toFixed(4) ?? 'N/A'}
                            </span>
                        </span>
                        <span>
                            Spearman:{' '}
                            <span className="font-semibold">
                                {hoveredCell.spearman_corr?.toFixed(4) ?? 'N/A'}
                            </span>
                        </span>
                        <span>
                            90d A:{' '}
                            <span
                                className={`font-semibold ${(hoveredCell.returns_a_90d ?? 0) >= 0 ? 'text-neon-green-500' : 'text-alert-red-400'}`}
                            >
                                {hoveredCell.returns_a_90d?.toFixed(2) ?? 'N/A'}%
                            </span>
                        </span>
                        <span>
                            90d B:{' '}
                            <span
                                className={`font-semibold ${(hoveredCell.returns_b_90d ?? 0) >= 0 ? 'text-neon-green-500' : 'text-alert-red-400'}`}
                            >
                                {hoveredCell.returns_b_90d?.toFixed(2) ?? 'N/A'}%
                            </span>
                        </span>
                    </div>
                </div>
            )}
        </section>
    );
}

function FullMatrix({
    matrix,
    tickers,
    getColor,
    getTextColor,
    onHover,
}: {
    matrix: Record<string, Record<string, number>>;
    tickers: string[];
    getColor: (v: number) => string;
    getTextColor: (v: number) => string;
    onHover: (c: HoveredCell | null) => void;
}) {
    return (
        <div className="min-w-fit">
            <div className="flex">
                <div className="w-16 shrink-0" />
                {tickers.map((ticker) => (
                    <div key={ticker} className="w-10 shrink-0 text-center">
                        <div className="text-[10px] font-mono font-bold text-zinc-500 truncate">
                            {ticker}
                        </div>
                    </div>
                ))}
            </div>

            {tickers.map((rowTicker) => (
                <div key={rowTicker} className="flex items-center">
                    <div className="w-16 shrink-0 text-right pr-2">
                        <span className="text-[10px] font-mono font-bold text-zinc-500 truncate">
                            {rowTicker}
                        </span>
                    </div>
                    {tickers.map((colTicker) => {
                        const value = matrix[rowTicker]?.[colTicker] ?? 0;
                        return (
                            <div
                                key={colTicker}
                                className={`w-10 h-10 shrink-0 ${getColor(value)} flex items-center justify-center cursor-pointer hover:ring-2 hover:ring-electric-blue-500 transition-all`}
                                onMouseEnter={() =>
                                    onHover({
                                        ticker_a: rowTicker,
                                        ticker_b: colTicker,
                                        pearson_corr: null,
                                        spearman_corr: null,
                                        returns_a_90d: null,
                                        returns_b_90d: null,
                                    })
                                }
                                onMouseLeave={() => onHover(null)}
                            >
                                <span
                                    className={`text-[9px] font-mono font-semibold ${getTextColor(value)}`}
                                >
                                    {value.toFixed(2)}
                                </span>
                            </div>
                        );
                    })}
                </div>
            ))}
        </div>
    );
}

function SimplifiedMatrix({
    matrix,
    tickers,
    getColor,
    getTextColor,
    onHover,
}: {
    matrix: Record<string, Record<string, number>>;
    tickers: string[];
    getColor: (v: number) => string;
    getTextColor: (v: number) => string;
    onHover: (c: HoveredCell | null) => void;
}) {
    // Show only upper triangle for large matrices
    const indices = tickers.map((_, i) => i);

    return (
        <div className="min-w-fit">
            <div className="flex">
                <div className="w-16 shrink-0" />
                {tickers.map((ticker, _i) => (
                    <div key={ticker} className="w-8 shrink-0 text-center">
                        <div
                            className="text-[8px] font-mono font-bold text-zinc-500 truncate transform -rotate-45 origin-center"
                            style={{
                                height: '40px',
                                display: 'flex',
                                alignItems: 'flex-end',
                                justifyContent: 'center',
                            }}
                        >
                            {ticker}
                        </div>
                    </div>
                ))}
            </div>

            {indices.map((i) => {
                const rowTicker = tickers[i];
                return (
                    <div key={rowTicker} className="flex items-center">
                        <div className="w-16 shrink-0 text-right pr-2">
                            <span className="text-[10px] font-mono font-bold text-zinc-500 truncate">
                                {rowTicker}
                            </span>
                        </div>
                        {indices.map((j) => {
                            const colTicker = tickers[j];
                            const value = i <= j ? (matrix[rowTicker]?.[colTicker] ?? 0) : 0;
                            return (
                                <div
                                    key={colTicker}
                                    className={`w-8 h-8 shrink-0 flex items-center justify-center ${i <= j ? getColor(value) : 'bg-zinc-100 dark:bg-zinc-800'}`}
                                    onMouseEnter={() =>
                                        i < j &&
                                        onHover({
                                            ticker_a: rowTicker,
                                            ticker_b: colTicker,
                                            pearson_corr: null,
                                            spearman_corr: null,
                                            returns_a_90d: null,
                                            returns_b_90d: null,
                                        })
                                    }
                                    onMouseLeave={() => onHover(null)}
                                >
                                    {i <= j && (
                                        <span
                                            className={`text-[8px] font-mono font-semibold ${getTextColor(value)}`}
                                        >
                                            {value.toFixed(2)}
                                        </span>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                );
            })}
        </div>
    );
}
