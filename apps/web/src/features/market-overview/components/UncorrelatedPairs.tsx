import {
    Badge,
    Button,
    Card,
    SectionHeading,
    Table,
    TableBody,
    TableCell,
    type TableCellTone,
    TableHead,
    TableHeader,
    TableRow,
} from '@llm-market-bench/ui-design-system';
import * as React from 'react';
import type { CorrelationData } from '../api/fetch-market-overview';
import { etfDescriptions } from '../utils/etf-descriptions';

interface UncorrelatedPairsProps {
    correlationData: CorrelationData[];
    onSelectPair?: (tickerA: string, tickerB: string) => void;
    timeframe?: '7d' | '30d' | '60d' | '90d';
}

export function UncorrelatedPairs({
    correlationData,
    onSelectPair,
    timeframe = '90d',
}: UncorrelatedPairsProps) {
    const [maxCorrelation, setMaxCorrelation] = React.useState(0.3);
    const [minReturn, setMinReturn] = React.useState(0);
    const [method, setMethod] = React.useState<'pearson' | 'spearman'>('pearson');
    const [sortBy, setSortBy] = React.useState<'correlation' | 'return'>('correlation');

    const displayWindowName =
        timeframe === '7d'
            ? '7-day'
            : timeframe === '30d'
              ? '30-day'
              : timeframe === '60d'
                ? '60-day'
                : '90-day';

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

    const getCorrelationTone = (corr: number | null): TableCellTone | undefined =>
        corr !== null && Math.abs(corr) < 0.3 ? undefined : 'muted';

    const getReturnTone = (ret: number | null): TableCellTone | undefined => {
        if (ret === null) return 'muted';
        return ret > 0 ? 'positive' : 'negative';
    };

    return (
        <section className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
                <SectionHeading>Uncorrelated Pairs with Positive Momentum</SectionHeading>
            </div>

            <Card
                variant="default"
                padding="none"
                className="overflow-hidden rounded-none shadow-sm"
            >
                <div className="p-6 border-b border-voxel-bevel-hi">
                    <div className="flex flex-wrap items-center gap-6">
                        <div className="flex items-center gap-3">
                            <label
                                htmlFor="max-corr-slider"
                                className="text-sm font-bold uppercase tracking-wider text-voxel-muted"
                            >
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
                            <span className="text-sm font-bold font-mono w-12">
                                {maxCorrelation.toFixed(2)}
                            </span>
                        </div>

                        <div className="flex items-center gap-3">
                            <label
                                htmlFor="min-return-slider"
                                className="text-sm font-bold uppercase tracking-wider text-voxel-muted"
                            >
                                Min {timeframe.toUpperCase()} Return:
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
                            <span className="text-sm font-bold font-mono w-12">{minReturn}%</span>
                        </div>

                        <div className="flex items-center gap-2">
                            <span className="text-sm font-bold uppercase tracking-wider text-voxel-muted">
                                Method:
                            </span>
                            <Button
                                size="sm"
                                variant={method === 'pearson' ? 'solid' : 'outline'}
                                colorScheme={method === 'pearson' ? 'accent' : 'neutral'}
                                onClick={() => setMethod('pearson')}
                            >
                                Pearson
                            </Button>
                            <Button
                                size="sm"
                                variant={method === 'spearman' ? 'solid' : 'outline'}
                                colorScheme={method === 'spearman' ? 'accent' : 'neutral'}
                                onClick={() => setMethod('spearman')}
                            >
                                Spearman
                            </Button>
                        </div>

                        <div className="flex items-center gap-2">
                            <span className="text-sm font-bold uppercase tracking-wider text-voxel-muted">
                                Sort by:
                            </span>
                            <Button
                                size="sm"
                                variant={sortBy === 'correlation' ? 'solid' : 'outline'}
                                colorScheme={sortBy === 'correlation' ? 'accent' : 'neutral'}
                                onClick={() => setSortBy('correlation')}
                            >
                                Lowest Correlation
                            </Button>
                            <Button
                                size="sm"
                                variant={sortBy === 'return' ? 'solid' : 'outline'}
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
                        <p className="text-sm font-bold text-voxel-muted">
                            No pairs match the current filters.
                        </p>
                        <p className="text-xs font-normal text-voxel-muted mt-2">
                            Try increasing the max correlation threshold.
                        </p>
                    </div>
                ) : (
                    <Table containerClassName="border-none shadow-none rounded-none">
                        <TableHeader>
                            <TableRow isHoverable={false}>
                                <TableHead>Pair</TableHead>
                                <TableHead align="center">Pearson</TableHead>
                                <TableHead align="center">Spearman</TableHead>
                                <TableHead align="right">{timeframe} Return A</TableHead>
                                <TableHead align="right">{timeframe} Return B</TableHead>
                                <TableHead align="right">Avg Return</TableHead>
                                <TableHead align="center">Action</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody className="divide-zinc-200 divide-zinc-800">
                            {filteredPairs.slice(0, 50).map((pair, idx) => (
                                <TableRow
                                    key={`${pair.ticker_a}-${pair.ticker_b}`}
                                    className={idx === 0 ? 'bg-blue-950/20' : ''}
                                >
                                    <TableCell className="whitespace-nowrap">
                                        <div className="flex flex-col gap-1">
                                            <div className="flex items-center gap-2">
                                                <span className="font-mono font-bold text-voxel-ink">
                                                    {pair.ticker_a}
                                                </span>
                                                <span className="text-voxel-muted">/</span>
                                                <span className="font-mono font-bold text-voxel-ink">
                                                    {pair.ticker_b}
                                                </span>
                                                {idx === 0 && (
                                                    <Badge
                                                        colorScheme="accent"
                                                        size="sm"
                                                        variant="soft"
                                                    >
                                                        BEST
                                                    </Badge>
                                                )}
                                            </div>
                                            <div className="flex items-center gap-2 text-xs font-normal text-voxel-muted max-w-[200px] sm:max-w-[300px] truncate">
                                                <span className="truncate">
                                                    {etfDescriptions[pair.ticker_a] ||
                                                        pair.ticker_a}
                                                </span>
                                                <span>•</span>
                                                <span className="truncate">
                                                    {etfDescriptions[pair.ticker_b] ||
                                                        pair.ticker_b}
                                                </span>
                                            </div>
                                        </div>
                                    </TableCell>
                                    <TableCell
                                        align="center"
                                        tone={getCorrelationTone(pair.pearson_corr)}
                                        className="font-mono"
                                    >
                                        {pair.pearson_corr?.toFixed(4) ?? 'N/A'}
                                    </TableCell>
                                    <TableCell
                                        align="center"
                                        tone={getCorrelationTone(pair.spearman_corr)}
                                        className="font-mono"
                                    >
                                        {pair.spearman_corr?.toFixed(4) ?? 'N/A'}
                                    </TableCell>
                                    <TableCell
                                        align="right"
                                        tone={getReturnTone(pair.returns_a_90d)}
                                    >
                                        {pair.returns_a_90d?.toFixed(2) ?? 'N/A'}%
                                    </TableCell>
                                    <TableCell
                                        align="right"
                                        tone={getReturnTone(pair.returns_b_90d)}
                                    >
                                        {pair.returns_b_90d?.toFixed(2) ?? 'N/A'}%
                                    </TableCell>
                                    <TableCell align="right" tone={getReturnTone(pair.avgReturn)}>
                                        {pair.avgReturn.toFixed(2)}%
                                    </TableCell>
                                    <TableCell align="center">
                                        {onSelectPair && (
                                            <Button
                                                size="sm"
                                                variant="solid"
                                                colorScheme="accent"
                                                onClick={() =>
                                                    onSelectPair(pair.ticker_a, pair.ticker_b)
                                                }
                                                className="cursor-pointer"
                                            >
                                                📈 History
                                            </Button>
                                        )}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                )}

                {filteredPairs.length > 50 && (
                    <div className="p-4 border-t border-voxel-bevel-hi text-center text-xs font-normal text-voxel-muted">
                        Showing top 50 of {filteredPairs.length} pairs
                    </div>
                )}
            </Card>

            <div className="p-4 bg-voxel-trough border border-voxel-bevel-hi rounded-none flex flex-col gap-2">
                <h3 className="text-sm font-bold text-voxel-ink">💡 Strategy Note</h3>
                <p className="text-xs font-normal text-voxel-muted">
                    The most uncorrelated pair with positive returns is highlighted in blue. This
                    combination of assets would have provided diversification benefits during the{' '}
                    {displayWindowName} window while still generating positive returns. The XLK/XLE
                    strategy (Technology + Energy) is a classic example of this approach.
                </p>
            </div>
        </section>
    );
}
