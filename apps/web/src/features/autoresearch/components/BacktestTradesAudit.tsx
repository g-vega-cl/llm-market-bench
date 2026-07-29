import type { PromptExperiment } from '@llm-market-bench/database';
import { Badge, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import { useState } from 'react';

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
        <tr className="hover:bg-zinc-50/80 dark:hover:bg-zinc-900/40 transition-colors">
            <td className="py-3.5 px-4 text-zinc-500 whitespace-nowrap">
                {trade.executed_at ? new Date(trade.executed_at).toLocaleString() : 'N/A'}
            </td>
            <td className="py-3.5 px-4 text-zinc-800 dark:text-zinc-200 font-semibold">
                {trade.model_name || 'Agent'}
            </td>
            <td className="py-3.5 px-4 font-bold text-indigo-600 dark:text-indigo-400">
                {trade.ticker}
            </td>
            <td className="py-3.5 px-4">
                <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold ${
                        isBuy
                            ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
                            : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20'
                    }`}
                >
                    {trade.signal.toUpperCase()}
                </span>
            </td>
            <td className="py-3.5 px-4 text-right font-medium">
                {trade.quantity.toLocaleString()}
            </td>
            <td className="py-3.5 px-4 text-right text-zinc-700 dark:text-zinc-300">
                ${trade.price.toFixed(2)}
            </td>
            <td className="py-3.5 px-4 text-right font-semibold text-zinc-900 dark:text-zinc-100">
                $
                {trade.total_cost.toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                })}
            </td>
            <td className="py-3.5 px-4 text-right">
                {trade.realized_pnl !== undefined && trade.realized_pnl !== null ? (
                    <span
                        className={`font-semibold ${
                            trade.realized_pnl >= 0
                                ? 'text-emerald-600 dark:text-emerald-400'
                                : 'text-rose-600 dark:text-rose-400'
                        }`}
                    >
                        {trade.realized_pnl >= 0 ? '+' : ''}${trade.realized_pnl.toFixed(2)}
                    </span>
                ) : (
                    <span className="text-zinc-400">—</span>
                )}
            </td>
            <td className="py-3.5 px-4 text-center">
                {trade.reasoning ? (
                    <button
                        type="button"
                        onClick={onToggleExpand}
                        className="text-xs font-sans text-indigo-500 hover:text-indigo-600 underline"
                    >
                        {isExpanded ? 'Hide' : 'View Thesis'}
                    </button>
                ) : (
                    <span className="text-zinc-400 text-xs font-sans">—</span>
                )}
                {isExpanded && trade.reasoning && (
                    <div className="mt-2 p-3 text-left font-sans text-xs bg-indigo-50/50 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-800/40 rounded-xl text-zinc-800 dark:text-zinc-200 leading-relaxed">
                        <div className="font-semibold text-indigo-600 dark:text-indigo-400 mb-1">
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
        <Card className="p-8 space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1">
                    <div className="flex items-center gap-2">
                        <SectionHeading>Backtest Executed Trades Audit</SectionHeading>
                        <Badge variant="outline">{trades.length} Total Trades</Badge>
                    </div>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400">
                        Complete point-in-time trade ledger executed by model agents during this
                        12-week backtest run.
                    </p>
                </div>

                {trades.length > 0 && (
                    <div className="flex items-center gap-1.5 bg-zinc-100 dark:bg-zinc-900 p-1 rounded-xl border border-zinc-200 dark:border-zinc-800 self-start md:self-auto">
                        {(['ALL', 'BUY', 'SELL'] as const).map((filter) => (
                            <button
                                key={filter}
                                type="button"
                                onClick={() => setSelectedSignalFilter(filter)}
                                className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all ${
                                    selectedSignalFilter === filter
                                        ? 'bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 shadow-sm'
                                        : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
                                }`}
                            >
                                {filter}
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {trades.length === 0 ? (
                <div className="p-8 text-center border-2 border-dashed border-zinc-200 dark:border-zinc-800 rounded-2xl space-y-3 bg-zinc-50/50 dark:bg-zinc-900/30">
                    <div className="text-3xl">📜</div>
                    <div className="space-y-1">
                        <h4 className="text-sm font-bold text-zinc-700 dark:text-zinc-300">
                            No Detailed Trade Ledger Recorded
                        </h4>
                        <p className="text-xs text-zinc-500 max-w-md mx-auto">
                            This historical backtest run was recorded prior to detailed trade
                            telemetry collection. Only aggregate equity metrics were preserved.
                        </p>
                    </div>
                </div>
            ) : filteredTrades.length === 0 ? (
                <div className="p-6 text-center text-xs text-zinc-500 border border-zinc-200 dark:border-zinc-800 rounded-xl">
                    No {selectedSignalFilter} trades executed during this run.
                </div>
            ) : (
                <div className="overflow-x-auto border border-zinc-200 dark:border-zinc-800 rounded-2xl">
                    <table className="w-full text-left text-xs">
                        <thead className="bg-zinc-100/70 dark:bg-zinc-900/80 border-b border-zinc-200 dark:border-zinc-800 text-zinc-500 dark:text-zinc-400 font-semibold uppercase tracking-wider">
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
                        <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800/60 font-mono">
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
