import {
    Badge,
    SubHeading,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@llm-market-bench/ui-design-system';
import { type KeyboardEvent, useState } from 'react';
import { signTone } from '~/lib/sign-tone';
import type { CompletedTradeRecord } from '../types';

export interface ClosedTradesSectionProps {
    title?: string;
    trades: CompletedTradeRecord[];
    limit?: number;
    emptyMessage?: string;
    trailingAction?: React.ReactNode;
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

function tradeKey(trade: CompletedTradeRecord, index: number): string {
    return `${trade.ticker}-${trade.entry_time}-${trade.exit_time}-${index}`;
}

/**
 * Closed trades ledger with in-flow `.voxel-trough` catalyst & confidence inspection
 * (zero floating tooltips, full keyboard accessibility).
 */
export function ClosedTradesSection({
    title = 'Closed Trades',
    trades,
    limit,
    emptyMessage = 'No closed trades recorded yet.',
    trailingAction,
}: ClosedTradesSectionProps) {
    const ordered = [...trades].reverse();
    const visible = typeof limit === 'number' ? ordered.slice(0, limit) : ordered;
    const [selectedKey, setSelectedKey] = useState<string | null>(null);

    const selectedTrade =
        visible.find((trade, idx) => tradeKey(trade, idx) === selectedKey) ?? null;

    const handleRowKeyDown = (event: KeyboardEvent<HTMLTableRowElement>, key: string) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            setSelectedKey((prev) => (prev === key ? null : key));
        }
    };

    return (
        <div className="flex flex-col gap-4 min-w-0">
            <SubHeading withDivider rightElement={trailingAction}>
                {title} ({trades.length})
            </SubHeading>

            {visible.length === 0 ? (
                <div className="voxel-trough bg-voxel-trough p-4">
                    <span className="text-xs font-normal text-voxel-muted">{emptyMessage}</span>
                </div>
            ) : (
                <>
                    <Table>
                        <TableHeader>
                            <TableRow isHoverable={false}>
                                <TableHead>Ticker</TableHead>
                                <TableHead>Exit Reason</TableHead>
                                <TableHead align="right">Entry</TableHead>
                                <TableHead align="right">Exit</TableHead>
                                <TableHead numeric>Net Return</TableHead>
                                <TableHead numeric>Net P&amp;L</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {visible.map((trade, idx) => {
                                const key = tradeKey(trade, idx);
                                const isSelected = selectedKey === key;
                                return (
                                    <TableRow
                                        key={key}
                                        tabIndex={0}
                                        role="button"
                                        aria-expanded={isSelected}
                                        aria-label={`Inspect ${trade.ticker} closed trade on ${trade.exit_time}`}
                                        onClick={() =>
                                            setSelectedKey((prev) => (prev === key ? null : key))
                                        }
                                        onKeyDown={(e) => handleRowKeyDown(e, key)}
                                        className="cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                                    >
                                        <TableCell>
                                            <Badge
                                                colorScheme={
                                                    trade.action === 'BUY' ? 'success' : 'neutral'
                                                }
                                                size="xs"
                                            >
                                                {trade.action} {trade.ticker}
                                            </Badge>
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant="soft" size="xs">
                                                {trade.exit_reason || 'EXIT'}
                                            </Badge>
                                        </TableCell>
                                        <TableCell align="right">
                                            ${trade.entry_price.toFixed(2)}
                                        </TableCell>
                                        <TableCell align="right">
                                            ${trade.exit_price.toFixed(2)}
                                        </TableCell>
                                        <TableCell numeric tone={signTone(trade.return_pct_net)}>
                                            {formatSignedPct(trade.return_pct_net)}
                                        </TableCell>
                                        <TableCell numeric tone={signTone(trade.pnl_net)}>
                                            {formatSignedDollar(trade.pnl_net)}
                                        </TableCell>
                                    </TableRow>
                                );
                            })}
                        </TableBody>
                    </Table>

                    <div
                        data-testid="closed-trade-inspector"
                        className="voxel-trough bg-voxel-trough p-3 flex flex-col gap-1.5 min-w-0"
                    >
                        {selectedTrade ? (
                            <>
                                <div className="flex flex-wrap items-baseline justify-between gap-2 min-w-0">
                                    <span className="text-sm font-bold text-voxel-ink whitespace-nowrap">
                                        {selectedTrade.ticker} ·{' '}
                                        {selectedTrade.exit_reason || 'EXIT'}
                                    </span>
                                    <span className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-xs font-normal font-mono text-voxel-muted min-w-0">
                                        <span className="whitespace-nowrap">
                                            {selectedTrade.entry_time}
                                        </span>
                                        <span className="whitespace-nowrap">
                                            → {selectedTrade.exit_time}
                                        </span>
                                    </span>
                                </div>
                                <p className="text-xs font-normal text-voxel-ink break-words">
                                    {selectedTrade.catalyst_headline?.trim() ||
                                        'No catalyst headline recorded for this trade.'}
                                </p>
                                <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-xs font-normal text-voxel-muted">
                                    <span className="whitespace-nowrap">
                                        Confidence:{' '}
                                        {typeof selectedTrade.confidence === 'number'
                                            ? `${Math.round(selectedTrade.confidence)}%`
                                            : '—'}
                                    </span>
                                    {typeof selectedTrade.shares === 'number' ? (
                                        <span className="whitespace-nowrap">
                                            Shares: {selectedTrade.shares}
                                        </span>
                                    ) : null}
                                </div>
                            </>
                        ) : (
                            <span className="text-xs font-normal text-voxel-muted">
                                Select any trade row above to inspect entry/exit timestamps,
                                confidence, and catalyst context.
                            </span>
                        )}
                    </div>
                </>
            )}
        </div>
    );
}
