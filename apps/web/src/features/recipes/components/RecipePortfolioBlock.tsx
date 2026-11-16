import {
    Badge,
    Card,
    MetricTile,
    SectionHeading,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@llm-market-bench/ui-design-system';
import type { OpenPositionRecord } from '../types';

interface RecipePortfolioBlockProps {
    title: string;
    cash: number;
    totalEquity: number;
    openPositions: OpenPositionRecord[];
    maxOpenTrades?: number;
}

function formatDollar(value: number): string {
    return `$${value.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    })}`;
}

function formatSignedDollar(value: number): string {
    const abs = Math.abs(value).toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
    return `${value >= 0 ? '+' : '-'}$${abs}`;
}

function formatSignedPct(value: number): string {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

export function RecipePortfolioBlock({
    title,
    cash,
    totalEquity,
    openPositions,
    maxOpenTrades = 4,
}: RecipePortfolioBlockProps) {
    const investedValue = openPositions.reduce(
        (sum, pos) =>
            sum +
            Number(pos.market_value ?? pos.shares * (pos.current_price ?? pos.entry_price ?? 0)),
        0,
    );

    return (
        <Card padding="md" className="flex flex-col gap-4 min-w-0">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-boxel-bevel-hi pb-3">
                <SectionHeading gradient="electric">{title}</SectionHeading>
                <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline" size="xs">
                        {openPositions.length} / {maxOpenTrades} Slots Open
                    </Badge>
                    <Badge variant="soft" colorScheme="neutral" size="xs">
                        Cash {formatDollar(cash)}
                    </Badge>
                </div>
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,11rem),1fr))] gap-4">
                <MetricTile
                    label="Cash Available"
                    value={<span className="font-mono tabular-nums">{formatDollar(cash)}</span>}
                />
                <MetricTile
                    label="Open Market Value"
                    value={
                        <span className="font-mono tabular-nums">
                            {formatDollar(investedValue)}
                        </span>
                    }
                />
                <MetricTile
                    label="Total Equity"
                    value={
                        <span className="font-mono tabular-nums">{formatDollar(totalEquity)}</span>
                    }
                />
                <MetricTile
                    label="Open Positions"
                    value={
                        <span className="font-mono tabular-nums">
                            {openPositions.length} / {maxOpenTrades}
                        </span>
                    }
                />
            </div>

            {openPositions.length === 0 ? (
                <div className="voxel-trough bg-boxel-trough p-4">
                    <span className="text-xs font-normal text-boxel-muted">
                        No open positions — 100% cash ({formatDollar(cash)}).
                    </span>
                </div>
            ) : (
                <Table>
                    <TableHeader>
                        <TableRow isHoverable={false}>
                            <TableHead>Ticker</TableHead>
                            <TableHead align="right">Entry Session</TableHead>
                            <TableHead numeric>Shares</TableHead>
                            <TableHead numeric>Entry</TableHead>
                            <TableHead numeric>Current</TableHead>
                            <TableHead numeric>Market Value</TableHead>
                            <TableHead numeric>Unrealized Return</TableHead>
                            <TableHead numeric>Unrealized P&amp;L</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {openPositions.map((pos) => {
                            const curPx = pos.current_price ?? pos.entry_price;
                            const mktVal = pos.market_value ?? pos.shares * curPx;
                            const costBasis = pos.cost_basis ?? pos.shares * pos.entry_price;
                            const unrPnl = pos.unrealized_pnl_net ?? mktVal - costBasis;
                            const unrPct =
                                pos.unrealized_return_pct ??
                                (costBasis > 0 ? (unrPnl / costBasis) * 100 : 0);
                            return (
                                <TableRow key={`${pos.ticker}-${pos.entry_time}`}>
                                    <TableCell>
                                        <div className="flex flex-wrap items-center gap-2">
                                            <Badge colorScheme="success" size="xs">
                                                {pos.ticker}
                                            </Badge>
                                        </div>
                                    </TableCell>
                                    <TableCell align="right">{pos.entry_time}</TableCell>
                                    <TableCell numeric>{pos.shares.toFixed(4)}</TableCell>
                                    <TableCell numeric>${pos.entry_price.toFixed(2)}</TableCell>
                                    <TableCell numeric>${curPx.toFixed(2)}</TableCell>
                                    <TableCell numeric>{formatDollar(mktVal)}</TableCell>
                                    <TableCell numeric>
                                        <span
                                            className={unrPct >= 0 ? 'text-success' : 'text-danger'}
                                        >
                                            {formatSignedPct(unrPct)}
                                        </span>
                                    </TableCell>
                                    <TableCell numeric>
                                        <span
                                            className={unrPnl >= 0 ? 'text-success' : 'text-danger'}
                                        >
                                            {formatSignedDollar(unrPnl)}
                                        </span>
                                    </TableCell>
                                </TableRow>
                            );
                        })}
                    </TableBody>
                </Table>
            )}
        </Card>
    );
}
