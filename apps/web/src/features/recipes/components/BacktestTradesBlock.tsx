import {
    Badge,
    Card,
    SectionHeading,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@llm-market-bench/ui-design-system';
import type { BacktestResultData } from '../types';

interface BacktestTradesBlockProps {
    results: BacktestResultData | null;
}

function signedPct(value: number): string {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function formatSignedDollar(value: number): string {
    const abs = Math.abs(value).toFixed(2);
    return `${value >= 0 ? '+' : '-'}$${abs}`;
}

function badgeColorForAction(action: string): 'success' | 'warning' | 'danger' {
    if (action === 'BUY') return 'success';
    if (action === 'EXIT') return 'warning';
    return 'danger';
}

function TradeRow({ trade }: { trade: BacktestResultData['trades'][number] }) {
    return (
        <TableRow>
            <TableCell>
                <Badge colorScheme={badgeColorForAction(trade.action)} size="xs">
                    {trade.action} {trade.ticker}
                </Badge>
            </TableCell>
            <TableCell align="right">{trade.entry_time}</TableCell>
            <TableCell align="right">{trade.exit_time}</TableCell>
            <TableCell numeric>${trade.entry_price.toFixed(2)}</TableCell>
            <TableCell numeric>${trade.exit_price.toFixed(2)}</TableCell>
            <TableCell>
                <Badge variant="outline" size="xs">
                    {trade.exit_reason || 'EXIT'}
                </Badge>
            </TableCell>
            <TableCell numeric>
                <span className={trade.return_pct_net >= 0 ? 'text-success' : 'text-danger'}>
                    {signedPct(trade.return_pct_net)}
                </span>
            </TableCell>
            <TableCell numeric>
                <span className={trade.pnl_net >= 0 ? 'text-success' : 'text-danger'}>
                    {formatSignedDollar(trade.pnl_net)}
                </span>
            </TableCell>
        </TableRow>
    );
}

export function BacktestTradesBlock({ results }: BacktestTradesBlockProps) {
    const trades = results?.trades ?? [];
    const skipped = results?.skipped_trades ?? [];

    return (
        <Card padding="md" className="flex flex-col gap-4 min-w-0">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-boxel-bevel-hi pb-3">
                <SectionHeading gradient="catalyst">
                    Executed Trades ({trades.length})
                </SectionHeading>
                <span className="text-xs font-normal text-boxel-muted">
                    {skipped.length} skipped signals
                </span>
            </div>

            {trades.length === 0 ? (
                <div className="voxel-trough bg-boxel-trough p-4">
                    <span className="text-xs font-normal text-boxel-muted">
                        No trades executed yet — closed positions appear here once exited or settled
                        at end of window.
                    </span>
                </div>
            ) : (
                <Table>
                    <TableHeader>
                        <TableRow isHoverable={false}>
                            <TableHead>Action</TableHead>
                            <TableHead align="right">Entry Session</TableHead>
                            <TableHead align="right">Exit Session</TableHead>
                            <TableHead numeric>Entry</TableHead>
                            <TableHead numeric>Exit</TableHead>
                            <TableHead>Exit Reason</TableHead>
                            <TableHead numeric>Net Return</TableHead>
                            <TableHead numeric>Net P&amp;L</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {(() => {
                            const seenTrades = new Map<string, number>();
                            return trades.map((t) => {
                                const baseKey = `${t.entry_time}-${t.ticker}-${t.action}-${t.exit_time}-${t.entry_price}`;
                                const count = (seenTrades.get(baseKey) ?? 0) + 1;
                                seenTrades.set(baseKey, count);
                                return <TradeRow key={`${baseKey}#${count}`} trade={t} />;
                            });
                        })()}
                    </TableBody>
                </Table>
            )}

            {skipped.length > 0 && (
                <div className="flex flex-col gap-2 min-w-0">
                    <span className="text-sm font-bold text-boxel-ink">
                        Counterfactual Skipped Signals (
                        {skipped.length > 20 ? `Showing 20 of ${skipped.length}` : skipped.length})
                    </span>
                    <Table>
                        <TableHeader>
                            <TableRow isHoverable={false}>
                                <TableHead>Category</TableHead>
                                <TableHead>Reason</TableHead>
                                <TableHead align="right">Time</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {(() => {
                                const seenSkips = new Map<string, number>();
                                return skipped.slice(0, 20).map((s) => {
                                    const baseKey = `${s.time}-${s.skip_type}-${s.reason}`;
                                    const count = (seenSkips.get(baseKey) ?? 0) + 1;
                                    seenSkips.set(baseKey, count);
                                    return (
                                        <TableRow key={`${baseKey}#${count}`} isInactive>
                                            <TableCell>
                                                <Badge variant="outline" size="xs">
                                                    {s.skip_type}
                                                </Badge>
                                            </TableCell>
                                            <TableCell>
                                                <span className="break-words">{s.reason}</span>
                                            </TableCell>
                                            <TableCell align="right">
                                                {s.time.replace('T', ' ').slice(0, 16)}
                                            </TableCell>
                                        </TableRow>
                                    );
                                });
                            })()}
                        </TableBody>
                    </Table>
                </div>
            )}
        </Card>
    );
}
