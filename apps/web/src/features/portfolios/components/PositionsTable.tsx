import type { PositionWithReasoning, TradeWithReasoning } from '@llm-market-bench/database';
import {
    Badge,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@llm-market-bench/ui-design-system';
import * as React from 'react';
import { useState } from 'react';
import { signTone } from '~/lib/sign-tone';
import { formatEasternDateTimeWithYear, formatEasternExactTime } from '~/utils/date';
import type { FrontierTheme } from '../api/fetch-portfolios';

export type Position = PositionWithReasoning;

function formatPnlUsd(value: number | null | undefined): string {
    if (value == null) return '—';
    const amount = Number(value);
    const digits = amount.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
    if (amount < 0) return `-$${digits.replace('-', '')}`;
    return `+$${digits}`;
}

function formatPnlPct(value: number | null | undefined): string {
    if (value == null) return '—';
    const pct = Number(value);
    return `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`;
}

interface PositionsTableProps {
    positions: Position[];
    themes?: FrontierTheme[];
    trades?: TradeWithReasoning[];
}

type SortKey = 'invested' | 'portfolio_pct' | 'pnl_usd' | 'pnl_pct';
type SortDirection = 'asc' | 'desc';

export function PositionsTable({ positions, themes, trades }: PositionsTableProps) {
    const [expandedTicker, setExpandedTicker] = useState<string | null>(null);
    const [sortKey, setSortKey] = useState<SortKey | null>(null);
    const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

    // Calculate total invested cash for the portfolio using gross notional exposure
    const totalInvestedCash = positions.reduce(
        (sum, pos) => sum + Math.abs((pos.quantity ?? 0) * (pos.average_cost_basis ?? 0)),
        0,
    );

    const hasAnyShorts = React.useMemo(() => {
        return positions?.some((p) => p.side === 'SHORT');
    }, [positions]);

    const tickerToTradeMap = React.useMemo(() => {
        const map = new Map<string, TradeWithReasoning>();
        if (trades) {
            for (const t of trades) {
                const sig = t.signal?.toUpperCase();
                if ((sig === 'BUY' || sig === 'SHORT') && !map.has(t.ticker.toUpperCase())) {
                    map.set(t.ticker.toUpperCase(), t);
                }
            }
        }
        return map;
    }, [trades]);

    const tickerToThemeMap = React.useMemo(() => {
        const map = new Map<string, string>();
        if (themes) {
            for (const theme of themes) {
                if (Array.isArray(theme.tickers)) {
                    for (const t of theme.tickers) {
                        map.set(String(t).toUpperCase(), theme.theme_name);
                    }
                }
            }
        }
        return map;
    }, [themes]);

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
                    aVal = Math.abs((a.quantity ?? 0) * (a.average_cost_basis ?? 0));
                    bVal = Math.abs((b.quantity ?? 0) * (b.average_cost_basis ?? 0));
                    break;
                case 'portfolio_pct':
                    aVal = totalInvestedCash
                        ? (Math.abs((a.quantity ?? 0) * (a.average_cost_basis ?? 0)) /
                              totalInvestedCash) *
                          100
                        : 0;
                    bVal = totalInvestedCash
                        ? (Math.abs((b.quantity ?? 0) * (b.average_cost_basis ?? 0)) /
                              totalInvestedCash) *
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
        <Table className="min-w-[800px]">
            <TableHeader>
                <TableRow isHoverable={false}>
                    <TableHead>Ticker</TableHead>
                    <TableHead align="right">Qty</TableHead>
                    <TableHead align="right">Avg Cost</TableHead>
                    <TableHead align="right">Price</TableHead>
                    <TableHead
                        align="right"
                        className="cursor-pointer hover:bg-voxel-elevated transition-colors select-none"
                        onClick={() => handleSort('invested')}
                        title="Click to sort by invested amount"
                    >
                        Invested {getSortIcon('invested')}
                    </TableHead>
                    <TableHead
                        align="right"
                        className="cursor-pointer hover:bg-voxel-elevated transition-colors select-none"
                        onClick={() => handleSort('portfolio_pct')}
                        title="Click to sort by portfolio percentage"
                    >
                        % {getSortIcon('portfolio_pct')}
                    </TableHead>
                    <TableHead
                        align="right"
                        className="cursor-pointer hover:bg-voxel-elevated transition-colors select-none"
                        onClick={() => handleSort('pnl_usd')}
                        title="Click to sort by profit/loss in USD"
                    >
                        P/L (USD) {getSortIcon('pnl_usd')}
                    </TableHead>
                    <TableHead
                        align="right"
                        className="cursor-pointer hover:bg-voxel-elevated transition-colors select-none"
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
                            <TableCell>
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
                                    {pos.side === 'SHORT' && (
                                        <Badge variant="soft" size="sm" colorScheme="danger">
                                            SHORT
                                        </Badge>
                                    )}
                                    {hasAnyShorts && pos.side === 'LONG' && (
                                        <Badge variant="soft" size="sm" colorScheme="success">
                                            LONG
                                        </Badge>
                                    )}
                                    {pos.ticker &&
                                        tickerToThemeMap.has(pos.ticker.toUpperCase()) && (
                                            <span className="text-xs font-normal px-2 py-0.5 rounded-none bg-zinc-800 text-zinc-300 border border-zinc-700/60 font-sans tracking-tight">
                                                {tickerToThemeMap.get(pos.ticker.toUpperCase())}
                                            </span>
                                        )}
                                </div>
                            </TableCell>
                            <TableCell align="right">{pos.quantity}</TableCell>
                            <TableCell align="right">
                                $
                                {Number(pos.average_cost_basis).toLocaleString('en-US', {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2,
                                })}
                            </TableCell>
                            <TableCell align="right">
                                $
                                {Number(pos.current_price || pos.average_cost_basis).toLocaleString(
                                    'en-US',
                                    {
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: 2,
                                    },
                                )}
                            </TableCell>
                            <TableCell align="right">
                                $
                                {Math.abs(
                                    (pos.quantity ?? 0) * (pos.average_cost_basis ?? 0),
                                ).toLocaleString('en-US', {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2,
                                })}
                            </TableCell>
                            <TableCell align="right">
                                {totalInvestedCash
                                    ? `${(
                                          (Math.abs(
                                              (pos.quantity ?? 0) * (pos.average_cost_basis ?? 0),
                                          ) /
                                              totalInvestedCash) *
                                              100
                                      ).toFixed(2)}%`
                                    : '0%'}
                            </TableCell>
                            <TableCell align="right" tone={signTone(pos.unrealized_pnl_usd)}>
                                {formatPnlUsd(pos.unrealized_pnl_usd)}
                            </TableCell>
                            <TableCell align="right" tone={signTone(pos.unrealized_pnl_pct)}>
                                {formatPnlPct(pos.unrealized_pnl_pct)}
                            </TableCell>
                        </TableRow>
                        {expandedTicker === pos.ticker && (
                            <TableRow
                                isHoverable={false}
                                className="bg-voxel-trough"
                                data-testid={`reasoning-row-${pos.ticker}`}
                            >
                                <TableCell colSpan={8} className="py-4">
                                    <div className="flex flex-col gap-4">
                                        {pos.ticker &&
                                            tickerToTradeMap.has(pos.ticker.toUpperCase()) && (
                                                <div className="flex flex-wrap items-center gap-2 text-xs border-b border-zinc-800 pb-3">
                                                    <span className="text-zinc-400 font-normal">
                                                        {tickerToTradeMap
                                                            .get(pos.ticker.toUpperCase())
                                                            ?.signal?.toUpperCase() === 'SHORT'
                                                            ? 'Sold Short:'
                                                            : 'Bought:'}
                                                    </span>
                                                    <Badge
                                                        variant="soft"
                                                        colorScheme="neutral"
                                                        size="sm"
                                                        className="font-mono"
                                                    >
                                                        {formatEasternDateTimeWithYear(
                                                            tickerToTradeMap.get(
                                                                pos.ticker.toUpperCase(),
                                                            )?.executed_at,
                                                        )}{' '}
                                                        (
                                                        {formatEasternExactTime(
                                                            tickerToTradeMap.get(
                                                                pos.ticker.toUpperCase(),
                                                            )?.executed_at,
                                                        )}
                                                        )
                                                    </Badge>
                                                </div>
                                            )}
                                        <h4 className="flex items-center gap-2 text-sm font-bold text-voxel-ink uppercase tracking-tight">
                                            <span className="w-1.5 h-1.5 rounded-none bg-blue-500 animate-pulse" />
                                            Thinking Process
                                        </h4>
                                        <div className="bg-voxel-surface border border-voxel-bevel-hi rounded-none p-4 sm:p-6 shadow-sm">
                                            <p className="text-voxel-muted leading-relaxed whitespace-pre-wrap text-xs font-normal">
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
                        <TableCell colSpan={8} align="center" tone="muted" className="py-12">
                            No active positions in this portfolio.
                        </TableCell>
                    </TableRow>
                )}
            </TableBody>
        </Table>
    );
}
