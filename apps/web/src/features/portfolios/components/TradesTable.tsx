import type { TradeWithReasoning } from '@llm-market-bench/database';
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

export type Trade = TradeWithReasoning;

interface TradesTableProps {
    trades: Trade[];
}

export function TradesTable({ trades }: TradesTableProps) {
    const [expandedId, setExpandedId] = useState<string | null>(null);

    return (
        <Table className="min-w-[700px]">
            <TableHeader>
                <TableRow isHoverable={false}>
                    <TableHead>Date</TableHead>
                    <TableHead>Ticker</TableHead>
                    <TableHead>Signal</TableHead>
                    <TableHead>Alpaca</TableHead>
                    <TableHead align="right">Qty</TableHead>
                    <TableHead align="right">Price</TableHead>
                    <TableHead align="right">Total</TableHead>
                    <TableHead align="right">PnL</TableHead>
                </TableRow>
            </TableHeader>
            <TableBody>
                {trades?.map((trade) => (
                    <React.Fragment key={trade.id}>
                        <TableRow
                            className="cursor-pointer group"
                            onClick={() => setExpandedId(expandedId === trade.id ? null : trade.id)}
                        >
                            <TableCell className="text-zinc-500 dark:text-zinc-400 text-sm">
                                {trade.executed_at
                                    ? new Date(trade.executed_at).toLocaleDateString('en-US', {
                                          timeZone: 'America/New_York',
                                      })
                                    : '-'}
                            </TableCell>
                            <TableCell className="font-bold text-zinc-900 dark:text-zinc-100">
                                <div className="flex items-center gap-2">
                                    <span
                                        className={`transition-transform duration-200 ${expandedId === trade.id ? 'rotate-90' : ''}`}
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
                                    {trade.ticker}
                                </div>
                            </TableCell>
                            <TableCell>
                                <Badge
                                    variant="soft"
                                    colorScheme={
                                        trade.signal.toUpperCase() === 'BUY' ? 'success' : 'danger'
                                    }
                                    radius="md"
                                    size="sm"
                                >
                                    {trade.signal}
                                </Badge>
                            </TableCell>
                            <TableCell>
                                {trade.alpaca_status ? (
                                    <a
                                        href="https://paper.alpaca.markets/orders"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-block transition-opacity hover:opacity-80"
                                        title={
                                            trade.alpaca_order_id
                                                ? `Order ID: ${trade.alpaca_order_id}`
                                                : undefined
                                        }
                                        onClick={(e) => e.stopPropagation()}
                                    >
                                        <Badge
                                            variant="soft"
                                            colorScheme={
                                                trade.alpaca_status === 'FILLED'
                                                    ? 'success'
                                                    : trade.alpaca_status === 'PENDING' ||
                                                        trade.alpaca_status === 'SUBMITTED'
                                                      ? 'warning'
                                                      : 'danger'
                                            }
                                            radius="md"
                                            size="sm"
                                        >
                                            {trade.alpaca_status}
                                        </Badge>
                                    </a>
                                ) : (
                                    <span className="text-zinc-300 dark:text-zinc-700">—</span>
                                )}
                            </TableCell>
                            <TableCell align="right" className="text-zinc-700 dark:text-zinc-300">
                                {trade.quantity}
                            </TableCell>
                            <TableCell align="right" className="text-zinc-700 dark:text-zinc-300">
                                $
                                {Number(trade.price).toLocaleString(undefined, {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2,
                                })}
                            </TableCell>
                            <TableCell
                                align="right"
                                className="text-zinc-900 dark:text-zinc-100 font-medium"
                            >
                                $
                                {Number(trade.total_cost).toLocaleString(undefined, {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2,
                                })}
                            </TableCell>
                            <TableCell align="right">
                                {trade.realized_pnl !== null && trade.realized_pnl !== undefined ? (
                                    <div className="flex flex-col items-end">
                                        <span
                                            className={`font-bold ${trade.realized_pnl >= 0 ? 'text-emerald-600 dark:text-emerald-500' : 'text-rose-600 dark:text-rose-500'}`}
                                        >
                                            {trade.realized_pnl >= 0 ? '+' : ''}$
                                            {Math.abs(trade.realized_pnl).toLocaleString(
                                                undefined,
                                                {
                                                    minimumFractionDigits: 2,
                                                    maximumFractionDigits: 2,
                                                },
                                            )}
                                        </span>
                                        <Badge
                                            size="xs"
                                            variant="soft"
                                            colorScheme={
                                                trade.realized_pnl >= 0 ? 'success' : 'danger'
                                            }
                                            radius="md"
                                        >
                                            {trade.realized_pnl >= 0 ? '+' : ''}
                                            {trade.realized_pnl_pct?.toFixed(2)}%
                                        </Badge>
                                    </div>
                                ) : (
                                    <span className="text-zinc-300 dark:text-zinc-700">—</span>
                                )}
                            </TableCell>
                        </TableRow>
                        {expandedId === trade.id && (
                            <TableRow
                                isHoverable={false}
                                className="bg-zinc-50/30 dark:bg-zinc-950/30"
                            >
                                <TableCell colSpan={8} className="px-4 sm:px-12 py-4 sm:py-6">
                                    <div className="flex flex-col gap-4">
                                        <h4 className="flex items-center gap-2 text-sm font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-tight">
                                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                                            Thinking Process
                                        </h4>
                                        <div className="bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 sm:p-6 shadow-sm">
                                            <p className="text-zinc-600 dark:text-zinc-400 leading-relaxed whitespace-pre-wrap text-sm sm:text-base">
                                                {trade.reasoning}
                                            </p>
                                        </div>
                                    </div>
                                </TableCell>
                            </TableRow>
                        )}
                    </React.Fragment>
                ))}
                {(!trades || trades.length === 0) && (
                    <TableRow isHoverable={false}>
                        <TableCell colSpan={8} className="py-12 text-center text-zinc-500">
                            No recent trades found for this agent.
                        </TableCell>
                    </TableRow>
                )}
            </TableBody>
        </Table>
    );
}
