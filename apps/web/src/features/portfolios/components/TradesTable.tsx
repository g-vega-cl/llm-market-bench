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
import { ExecutionTraceView } from '~/features/today/components/ExecutionTraceView';
import {
    formatEasternDateTimeWithYear,
    formatEasternExactTime,
    formatEasternShortDateWithYear,
} from '~/utils/date';

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
                    <TableHead>Executed At</TableHead>
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
                            <TableCell tone="muted" className="whitespace-nowrap">
                                {trade.executed_at ? (
                                    <div className="flex flex-col">
                                        <span className="font-bold text-voxel-ink">
                                            {formatEasternShortDateWithYear(trade.executed_at)}
                                        </span>
                                        <span className="text-xs text-voxel-muted font-mono">
                                            {formatEasternExactTime(trade.executed_at)}
                                        </span>
                                    </div>
                                ) : (
                                    '-'
                                )}
                            </TableCell>
                            <TableCell>
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
                                    size="sm"
                                >
                                    {trade.signal}
                                </Badge>
                            </TableCell>
                            <TableCell>
                                <div className="flex flex-col items-start gap-1">
                                    {trade.alpaca_status ? (
                                        trade.alpaca_status === 'BACKFILLED' ? (
                                            <span
                                                className="inline-block"
                                                onClick={(e) => e.stopPropagation()}
                                            >
                                                <Badge
                                                    variant="soft"
                                                    colorScheme="accent"
                                                    size="sm"
                                                    title="Reconstructed post-market via historical session bars"
                                                >
                                                    BACKFILLED
                                                </Badge>
                                            </span>
                                        ) : (
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
                                                    size="sm"
                                                >
                                                    {trade.alpaca_status}
                                                </Badge>
                                            </a>
                                        )
                                    ) : (
                                        <span className="text-voxel-muted">—</span>
                                    )}
                                    {trade.audit_flag ? (
                                        <Badge
                                            variant="soft"
                                            colorScheme="warning"
                                            size="xs"
                                            title={trade.audit_note ?? undefined}
                                        >
                                            {trade.audit_flag === 'NON_TRADING_DAY'
                                                ? 'HOLIDAY'
                                                : 'BAD_PRICE'}
                                        </Badge>
                                    ) : null}
                                </div>
                            </TableCell>
                            <TableCell align="right">{trade.quantity}</TableCell>
                            <TableCell align="right">
                                $
                                {Number(trade.price).toLocaleString('en-US', {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2,
                                })}
                            </TableCell>
                            <TableCell align="right">
                                $
                                {Number(trade.total_cost).toLocaleString('en-US', {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2,
                                })}
                            </TableCell>
                            <TableCell align="right">
                                {trade.realized_pnl !== null && trade.realized_pnl !== undefined ? (
                                    <div className="flex flex-col items-end">
                                        <span
                                            className={`font-bold ${trade.realized_pnl >= 0 ? 'text-success' : 'text-danger'}`}
                                        >
                                            {trade.realized_pnl >= 0 ? '+' : '-'}$
                                            {Math.abs(trade.realized_pnl).toLocaleString('en-US', {
                                                minimumFractionDigits: 2,
                                                maximumFractionDigits: 2,
                                            })}
                                        </span>
                                        <Badge
                                            size="xs"
                                            variant="soft"
                                            colorScheme={
                                                trade.realized_pnl >= 0 ? 'success' : 'danger'
                                            }
                                        >
                                            {trade.realized_pnl >= 0 ? '+' : ''}
                                            {trade.realized_pnl_pct?.toFixed(2)}%
                                        </Badge>
                                    </div>
                                ) : (
                                    <span className="text-voxel-muted">—</span>
                                )}
                            </TableCell>
                        </TableRow>
                        {expandedId === trade.id && (
                            <TableRow isHoverable={false} className="bg-voxel-trough">
                                <TableCell colSpan={8} className="py-4">
                                    <div className="flex flex-col gap-4">
                                        <div className="flex flex-wrap items-center gap-4 text-xs border-b border-zinc-800 pb-3">
                                            {trade.executed_at && (
                                                <div className="flex items-center gap-1.5">
                                                    <span className="text-zinc-400 font-normal">
                                                        Executed:
                                                    </span>
                                                    <Badge
                                                        variant="soft"
                                                        colorScheme="neutral"
                                                        size="sm"
                                                        className="font-mono"
                                                    >
                                                        {formatEasternDateTimeWithYear(
                                                            trade.executed_at,
                                                        )}{' '}
                                                        ({formatEasternExactTime(trade.executed_at)}
                                                        )
                                                    </Badge>
                                                </div>
                                            )}
                                            {trade.alpaca_filled_at && (
                                                <div className="flex items-center gap-1.5">
                                                    <span className="text-zinc-400 font-normal">
                                                        Alpaca Filled:
                                                    </span>
                                                    <Badge
                                                        variant="soft"
                                                        colorScheme="success"
                                                        size="sm"
                                                        className="font-mono"
                                                    >
                                                        {formatEasternDateTimeWithYear(
                                                            trade.alpaca_filled_at,
                                                        )}{' '}
                                                        (
                                                        {formatEasternExactTime(
                                                            trade.alpaca_filled_at,
                                                        )}
                                                        )
                                                    </Badge>
                                                </div>
                                            )}
                                            {trade.alpaca_order_id && (
                                                <div className="flex items-center gap-1.5">
                                                    <span className="text-zinc-400 font-normal">
                                                        Order ID:
                                                    </span>
                                                    <Badge
                                                        variant="soft"
                                                        colorScheme="neutral"
                                                        size="sm"
                                                        className="font-mono"
                                                    >
                                                        {trade.alpaca_order_id}
                                                    </Badge>
                                                </div>
                                            )}
                                        </div>
                                        <h4 className="flex items-center gap-2 text-sm font-bold text-voxel-ink uppercase tracking-tight">
                                            <span className="w-1.5 h-1.5 rounded-none bg-blue-500 animate-pulse" />
                                            Thinking Process
                                        </h4>
                                        <div className="bg-voxel-surface border border-voxel-bevel-hi rounded-none p-4 sm:p-6 shadow-sm">
                                            <p className="text-voxel-muted leading-relaxed whitespace-pre-wrap text-xs font-normal">
                                                {trade.reasoning}
                                            </p>
                                        </div>
                                        <ExecutionTraceView
                                            trace={trade.metadata?.execution_trace}
                                        />
                                    </div>
                                </TableCell>
                            </TableRow>
                        )}
                    </React.Fragment>
                ))}
                {(!trades || trades.length === 0) && (
                    <TableRow isHoverable={false}>
                        <TableCell colSpan={8} align="center" tone="muted" className="py-12">
                            No recent trades found for this agent.
                        </TableCell>
                    </TableRow>
                )}
            </TableBody>
        </Table>
    );
}
