import type { PromptExperiment } from '@llm-market-bench/database';
import { Badge, Button, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import { useState } from 'react';
import { formatEasternDateTimeWithYear } from '~/utils/date';

export interface BacktestTrade {
    id?: string;
    portfolio_id?: string;
    model_name?: string;
    ticker: string;
    signal: 'BUY' | 'SELL' | string;
    quantity: number;
    price: number;
    total_cost: number;
    executed_at: string;
    reasoning?: string;
    realized_pnl?: number | null;
    realized_pnl_pct?: number | null;
}

interface BacktestTradesAuditProps {
    experiment: PromptExperiment;
}

function BacktestTradeRow({
    trade,
    isExpanded,
    onToggleExpand,
}: {
    trade: BacktestTrade;
    isExpanded: boolean;
    onToggleExpand: () => void;
}) {
    const isBuy = trade.signal.toUpperCase() === 'BUY';

    return (
        <tr className="hover:bg-voxel-elevated/40 transition-colors">
            <td className="py-3 px-4 text-voxel-muted whitespace-nowrap text-xs font-normal">
                {trade.executed_at ? formatEasternDateTimeWithYear(trade.executed_at) : 'N/A'}
            </td>
            <td className="py-3 px-4 text-voxel-ink text-xs font-normal">
                {trade.model_name || 'Agent'}
            </td>
            <td className="py-3 px-4 text-sm font-bold text-accent">{trade.ticker}</td>
            <td className="py-3 px-4">
                <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-none text-xs font-normal ${
                        isBuy
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    }`}
                >
                    {trade.signal.toUpperCase()}
                </span>
            </td>
            <td className="py-3 px-4 text-right text-xs font-normal">
                {trade.quantity.toLocaleString('en-US')}
            </td>
            <td className="py-3 px-4 text-right text-voxel-muted text-xs font-normal">
                ${trade.price.toFixed(2)}
            </td>
            <td className="py-3 px-4 text-right text-sm font-bold text-voxel-ink">
                $
                {trade.total_cost.toLocaleString('en-US', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                })}
            </td>
            <td className="py-3 px-4 text-right text-xs font-normal">
                {trade.realized_pnl !== undefined && trade.realized_pnl !== null ? (
                    <span
                        className={trade.realized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}
                    >
                        {trade.realized_pnl >= 0 ? '+' : ''}${trade.realized_pnl.toFixed(2)}
                    </span>
                ) : (
                    <span className="text-voxel-muted">—</span>
                )}
            </td>
            <td className="py-3 px-4 text-center">
                {trade.reasoning ? (
                    <Button
                        type="button"
                        variant="outline"
                        colorScheme="accent"
                        size="sm"
                        onClick={onToggleExpand}
                        className="text-xs font-normal font-sans"
                    >
                        {isExpanded ? 'Hide' : 'View Thesis'}
                    </Button>
                ) : (
                    <span className="text-voxel-muted text-xs font-normal font-sans">—</span>
                )}
                {isExpanded && trade.reasoning && (
                    <div className="mt-2 p-3 text-left font-sans text-xs font-normal bg-voxel-canvas border border-voxel-bevel-hi rounded-none text-voxel-ink leading-relaxed">
                        <div className="text-sm font-bold text-accent mb-1">
                            Agent Decision Thesis:
                        </div>
                        {trade.reasoning}
                    </div>
                )}
            </td>
        </tr>
    );
}

export function BacktestTradesAudit({ experiment }: BacktestTradesAuditProps) {
    const metrics = (experiment.metrics || {}) as Record<string, unknown>;
    const trades = Array.isArray(metrics.trades) ? (metrics.trades as BacktestTrade[]) : [];

    const [selectedSignalFilter, setSelectedSignalFilter] = useState<'ALL' | 'BUY' | 'SELL'>('ALL');
    const [expandedTradeId, setExpandedTradeId] = useState<string | null>(null);

    const filteredTrades = trades.filter((t) => {
        if (selectedSignalFilter === 'ALL') return true;
        return t.signal.toUpperCase() === selectedSignalFilter;
    });

    return (
        <Card className="p-6 flex flex-col gap-6 bg-voxel-surface border-voxel-bevel-hi">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                        <SectionHeading>Backtest Executed Trades Audit</SectionHeading>
                        <Badge variant="soft">{trades.length} Total Trades</Badge>
                    </div>
                    <p className="text-xs font-normal text-voxel-muted">
                        Complete point-in-time trade ledger executed by model agents during this
                        12-week backtest run.
                    </p>
                </div>

                {trades.length > 0 && (
                    <div className="flex items-center gap-1.5 bg-voxel-trough p-1 rounded-none border border-voxel-bevel-hi self-start md:self-auto">
                        {(['ALL', 'BUY', 'SELL'] as const).map((filter) => (
                            <Button
                                key={filter}
                                type="button"
                                variant={selectedSignalFilter === filter ? 'solid' : 'outline'}
                                colorScheme={selectedSignalFilter === filter ? 'accent' : 'neutral'}
                                size="sm"
                                onClick={() => setSelectedSignalFilter(filter)}
                            >
                                {filter}
                            </Button>
                        ))}
                    </div>
                )}
            </div>

            {trades.length === 0 ? (
                <div className="p-8 text-center border border-dashed border-voxel-bevel-hi rounded-none flex flex-col gap-3 bg-voxel-trough">
                    <div className="text-sm font-bold">📜</div>
                    <div className="flex flex-col gap-1">
                        <h4 className="text-sm font-bold text-voxel-ink">
                            No Detailed Trade Ledger Recorded
                        </h4>
                        <p className="text-xs font-normal text-voxel-muted max-w-md mx-auto">
                            This historical backtest run was recorded prior to detailed trade
                            telemetry collection. Only aggregate equity metrics were preserved.
                        </p>
                    </div>
                </div>
            ) : filteredTrades.length === 0 ? (
                <div className="p-6 text-center text-xs font-normal text-voxel-muted border border-voxel-bevel-hi rounded-none bg-voxel-trough">
                    No {selectedSignalFilter} trades executed during this run.
                </div>
            ) : (
                <div className="overflow-x-auto border border-voxel-bevel-hi rounded-none bg-voxel-trough">
                    <table className="w-full text-left text-xs font-mono font-normal">
                        <thead className="bg-voxel-surface border-b border-voxel-bevel-hi text-voxel-muted text-sm font-bold uppercase tracking-wider font-sans">
                            <tr>
                                <th className="py-3 px-4">Executed At</th>
                                <th className="py-3 px-4">Agent Model</th>
                                <th className="py-3 px-4">Ticker</th>
                                <th className="py-3 px-4">Signal</th>
                                <th className="py-3 px-4 text-right">Quantity</th>
                                <th className="py-3 px-4 text-right">Exec Price</th>
                                <th className="py-3 px-4 text-right">Total Cost</th>
                                <th className="py-3 px-4 text-right">Realized PnL</th>
                                <th className="py-3 px-4 text-center">Reasoning</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-voxel-bevel-hi/50">
                            {filteredTrades.map((t, index) => {
                                const key = t.id || `${t.ticker}-${t.executed_at}-${index}`;
                                return (
                                    <BacktestTradeRow
                                        key={key}
                                        trade={t}
                                        isExpanded={expandedTradeId === key}
                                        onToggleExpand={() =>
                                            setExpandedTradeId((prev) =>
                                                prev === key ? null : key,
                                            )
                                        }
                                    />
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </Card>
    );
}
