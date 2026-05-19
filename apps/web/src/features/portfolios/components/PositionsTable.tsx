import type { PositionWithReasoning } from '@llm-market-bench/database';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@llm-market-bench/ui-design-system';
import * as React from 'react';
import { useState } from 'react';

export type Position = PositionWithReasoning;

interface PositionsTableProps {
    positions: Position[];
}

type SortKey = 'invested' | 'portfolio_pct' | 'pnl_usd' | 'pnl_pct';
type SortDirection = 'asc' | 'desc';

export function PositionsTable({ positions }: PositionsTableProps) {
    const [expandedTicker, setExpandedTicker] = useState<string | null>(null);
    const [sortKey, setSortKey] = useState<SortKey | null>(null);
    const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

    // Calculate total invested cash for the portfolio
    const totalInvestedCash = positions.reduce(
        (sum, pos) => sum + (pos.quantity ?? 0) * (pos.average_cost_basis ?? 0),
        0,
    );

    const handleSort = (key: SortKey) => {
        if (sortKey === key) {
            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
        } else {
            setSortKey(key);
            setSortDirection('desc');
        }
    };

    const getSortIcon = (key: SortKey) => {
        if (sortKey !== key) return '↕';
        return sortDirection === 'asc' ? '↑' : '↓';
    };

    const sortedPositions = React.useMemo(() => {
        if (!sortKey) return positions;

        const sorted = [...positions].sort((a, b) => {
            let aVal: number;
            let bVal: number;

            switch (sortKey) {
                case 'invested':
                    aVal = (a.quantity ?? 0) * (a.average_cost_basis ?? 0);
                    bVal = (b.quantity ?? 0) * (b.average_cost_basis ?? 0);
                    break;
                case 'portfolio_pct':
                    aVal = totalInvestedCash
                        ? (((a.quantity ?? 0) * (a.average_cost_basis ?? 0)) / totalInvestedCash) *
                          100
                        : 0;
                    bVal = totalInvestedCash
                        ? (((b.quantity ?? 0) * (b.average_cost_basis ?? 0)) / totalInvestedCash) *
                          100
                        : 0;
                    break;
                case 'pnl_usd':
                    aVal = a.unrealized_pnl_usd ?? 0;
                    bVal = b.unrealized_pnl_usd ?? 0;
                    break;
                case 'pnl_pct':
                    aVal = a.unrealized_pnl_pct ?? 0;
                    bVal = b.unrealized_pnl_pct ?? 0;
                    break;
                default:
                    return 0;
            }

            return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
        });

        return sorted;
    }, [positions, sortKey, sortDirection, totalInvestedCash]);

    return (
        <Table containerClassName="min-w-[800px]">
            <TableHeader>
                <TableRow isHoverable={false}>
                    <TableHead>Ticker</TableHead>
                    <TableHead align="right">Qty</TableHead>
                    <TableHead align="right">Avg Cost</TableHead>
                    <TableHead align="right">Price</TableHead>
                    <TableHead
                        align="right"
                        className="cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors select-none"
                        onClick={() => handleSort('invested')}
                        title="Click to sort by invested amount"
                    >
                        Invested {getSortIcon('invested')}
                    </TableHead>
                    <TableHead
                        align="right"
                        className="cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors select-none"
                        onClick={() => handleSort('portfolio_pct')}
                        title="Click to sort by portfolio percentage"
                    >
                        % {getSortIcon('portfolio_pct')}
                    </TableHead>
                    <TableHead
                        align="right"
                        className="cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors select-none"
                        onClick={() => handleSort('pnl_usd')}
                        title="Click to sort by profit/loss in USD"
                    >
                        P/L (USD) {getSortIcon('pnl_usd')}
                    </TableHead>
                    <TableHead
                        align="right"
                        className="cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors select-none"
                        onClick={() => handleSort('pnl_pct')}
                        title="Click to sort by profit/loss percentage"
                    >
                        P/L (%) {getSortIcon('pnl_pct')}
                    </TableHead>
                </TableRow>
            </TableHeader>
            <TableBody>
                {sortedPositions?.map((pos) => (
                    <React.Fragment key={pos.ticker}>
                        <TableRow
                            className="cursor-pointer group"
                            onClick={() =>
                                setExpandedTicker(expandedTicker === pos.ticker ? null : pos.ticker)
                            }
                            data-testid={`position-row-${pos.ticker}`}
                        >
                            <TableCell className="font-bold text-zinc-900 dark:text-zinc-100">
                                <div className="flex items-center gap-2">
                                    <span
                                        className={`transition-transform duration-200 ${expandedTicker === pos.ticker ? 'rotate-90' : ''}`}
                                    >
                                        <svg
                                            className="w-4 h-4 text-zinc-400"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            stroke="currentColor"
                                        >
                                            <title>SVG</title>
                                            <path
                                                strokeLinecap="round"
                                                strokeLinejoin="round"
                                                strokeWidth={2}
                                                d="M9 5l7 7-7 7"
                                            />
                                        </svg>
                                    </span>
                                    {pos.ticker}
                                </div>
                            </TableCell>
                            <TableCell align="right" className="text-zinc-700 dark:text-zinc-300">
                                {pos.quantity}
                            </TableCell>
                            <TableCell align="right" className="text-zinc-700 dark:text-zinc-300">
                                $
                                {Number(pos.average_cost_basis).toLocaleString(undefined, {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2,
                                })}
                            </TableCell>
                            <TableCell align="right" className="text-zinc-700 dark:text-zinc-300">
                                $
                                {Number(pos.current_price || pos.average_cost_basis).toLocaleString(
                                    undefined,
                                    {
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: 2,
                                    },
                                )}
                            </TableCell>
                            <TableCell align="right" className="text-zinc-700 dark:text-zinc-300">
                                $
                                {(
                                    (pos.quantity ?? 0) * (pos.average_cost_basis ?? 0)
                                ).toLocaleString(undefined, {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2,
                                })}
                            </TableCell>
                            <TableCell align="right" className="text-zinc-700 dark:text-zinc-300">
                                {totalInvestedCash
                                    ? `${(
                                          (((pos.quantity ?? 0) * (pos.average_cost_basis ?? 0)) /
                                              totalInvestedCash) *
                                              100
                                      ).toFixed(2)}%`
                                    : '0%'}
                            </TableCell>
                            <TableCell
                                align="right"
                                className={`font-medium ${Number(pos.unrealized_pnl_usd) >= 0 ? 'text-emerald-600 dark:text-emerald-500' : 'text-rose-600 dark:text-rose-500'}`}
                            >
                                {Number(pos.unrealized_pnl_usd) >= 0 ? '+' : ''}$
                                {Number(pos.unrealized_pnl_usd).toLocaleString(undefined, {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2,
                                })}
                            </TableCell>
                            <TableCell
                                align="right"
                                className={`font-medium ${Number(pos.unrealized_pnl_pct) >= 0 ? 'text-emerald-600 dark:text-emerald-500' : 'text-rose-600 dark:text-rose-500'}`}
                            >
                                {Number(pos.unrealized_pnl_pct) >= 0 ? '+' : ''}
                                {Number(pos.unrealized_pnl_pct).toFixed(2)}%
                            </TableCell>
                        </TableRow>
                        {expandedTicker === pos.ticker && (
                            <TableRow
                                isHoverable={false}
                                className="bg-zinc-50/30 dark:bg-zinc-950/30"
                                data-testid={`reasoning-row-${pos.ticker}`}
                            >
                                <TableCell colSpan={8} className="px-4 sm:px-12 py-4 sm:py-6">
                                    <div className="flex flex-col gap-4">
                                        <h4 className="flex items-center gap-2 text-sm font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-tight">
                                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                                            Thinking Process
                                        </h4>
                                        <div className="bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 sm:p-6 shadow-sm">
                                            <p className="text-zinc-600 dark:text-zinc-400 leading-relaxed whitespace-pre-wrap text-sm sm:text-base">
                                                {pos.reasoning}
                                            </p>
                                        </div>
                                    </div>
                                </TableCell>
                            </TableRow>
                        )}
                    </React.Fragment>
                ))}
                {(!positions || positions.length === 0) && (
                    <TableRow isHoverable={false}>
                        <TableCell colSpan={8} className="py-12 text-center text-zinc-500">
                            No active positions in this portfolio.
                        </TableCell>
                    </TableRow>
                )}
            </TableBody>
        </Table>
    );
}
