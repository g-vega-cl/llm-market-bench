import { Badge } from '@llm-market-bench/ui-design-system';
import { useState } from 'react';
import type { BacktestResultData } from '../types';

interface RecipeBacktestResultsProps {
    results: BacktestResultData | null;
    isLoading?: boolean;
}

export function RecipeBacktestResults({ results, isLoading = false }: RecipeBacktestResultsProps) {
    const [useNetPnL, setUseNetPnL] = useState(true);

    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center border border-border bg-boxel-canvas p-8 rounded-none">
                <span className="font-display text-lg font-bold text-foreground">
                    Executing Timeline Simulation...
                </span>
                <span className="text-xs font-normal text-muted-foreground">
                    Stepping through intraday candles & news catalysts
                </span>
            </div>
        );
    }

    if (!results) {
        return (
            <div className="flex flex-col items-center justify-center border border-dashed border-border bg-boxel-canvas p-8 rounded-none">
                <span className="text-sm font-bold text-muted-foreground">
                    No Backtest Results Yet
                </span>
                <span className="text-xs font-normal text-muted-foreground">
                    Configure your blocks above and click "Run Simulation" to evaluate strategy
                    performance.
                </span>
            </div>
        );
    }

    const returnPct = useNetPnL ? results.total_return_pct_net : results.total_return_pct_midpoint;
    const endingCap = useNetPnL ? results.ending_capital_net : results.ending_capital_midpoint;

    return (
        <div className="flex flex-col gap-4 border border-border bg-boxel-surface p-4 rounded-none voxel-card">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
                <div className="flex items-center gap-2">
                    <span className="font-display text-lg font-bold text-foreground">
                        Simulation Telemetry
                    </span>
                    <Badge colorScheme={returnPct >= 0 ? 'success' : 'danger'} size="sm">
                        {returnPct >= 0 ? '+' : ''}
                        {returnPct.toFixed(2)}%
                    </Badge>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-xs font-normal text-muted-foreground">P&L Model:</span>
                    <button
                        type="button"
                        onClick={() => setUseNetPnL(false)}
                        className={`px-2 py-1 text-xs font-bold rounded-none ${
                            !useNetPnL
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-boxel-canvas text-muted-foreground'
                        }`}
                    >
                        Midpoint (Zero-Cost)
                    </button>
                    <button
                        type="button"
                        onClick={() => setUseNetPnL(true)}
                        className={`px-2 py-1 text-xs font-bold rounded-none ${
                            useNetPnL
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-boxel-canvas text-muted-foreground'
                        }`}
                    >
                        Spread & Slippage Adjusted
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,8rem),1fr))] gap-3">
                <div className="flex flex-col gap-1 border border-border bg-boxel-canvas p-3 rounded-none">
                    <span className="text-xs font-normal text-muted-foreground">
                        Ending Capital
                    </span>
                    <span className="font-mono text-sm font-bold tabular-nums text-foreground">
                        ${endingCap.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                </div>
                <div className="flex flex-col gap-1 border border-border bg-boxel-canvas p-3 rounded-none">
                    <span className="text-xs font-normal text-muted-foreground">Win Rate</span>
                    <span className="font-mono text-sm font-bold tabular-nums text-foreground">
                        {results.win_rate_pct}% ({results.winning_trades}/{results.total_trades})
                    </span>
                </div>
                <div className="flex flex-col gap-1 border border-border bg-boxel-canvas p-3 rounded-none">
                    <span className="text-xs font-normal text-muted-foreground">Profit Factor</span>
                    <span className="font-mono text-sm font-bold tabular-nums text-foreground">
                        {results.profit_factor}
                    </span>
                </div>
                <div className="flex flex-col gap-1 border border-border bg-boxel-canvas p-3 rounded-none">
                    <span className="text-xs font-normal text-muted-foreground">Max Drawdown</span>
                    <span className="font-mono text-sm font-bold tabular-nums text-red-400">
                        -{results.max_drawdown_pct}%
                    </span>
                </div>
                <div className="flex flex-col gap-1 border border-border bg-boxel-canvas p-3 rounded-none">
                    <span className="text-xs font-normal text-muted-foreground">
                        Completed Trades
                    </span>
                    <span className="font-mono text-sm font-bold tabular-nums text-foreground">
                        {results.total_trades}
                    </span>
                </div>
                <div className="flex flex-col gap-1 border border-border bg-boxel-canvas p-3 rounded-none">
                    <span className="text-xs font-normal text-muted-foreground">
                        LLM Invocations
                    </span>
                    <span className="font-mono text-sm font-bold tabular-nums text-foreground">
                        {results.llm_calls_made}
                    </span>
                </div>
            </div>

            {/* Weeks Breakdown */}
            {results.weeks_breakdown.length > 0 && (
                <div className="flex flex-col gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                        ISO Week Performance Breakdown
                    </span>
                    <div className="overflow-x-auto border border-border rounded-none">
                        <table className="w-full text-left text-xs font-normal">
                            <thead className="border-b border-border bg-boxel-canvas text-muted-foreground">
                                <tr>
                                    <th className="p-2 font-bold">Week</th>
                                    <th className="p-2 font-bold text-right">Trades</th>
                                    <th className="p-2 font-bold text-right">Midpoint P&L</th>
                                    <th className="p-2 font-bold text-right">Net P&L</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border">
                                {results.weeks_breakdown.map((w) => {
                                    const tradesCount =
                                        typeof w.trades_count === 'number'
                                            ? w.trades_count
                                            : (w.trades ?? 0);
                                    const midPnl =
                                        typeof w.week_pnl_midpoint === 'number'
                                            ? w.week_pnl_midpoint
                                            : (w.pnl_midpoint ?? 0);
                                    const netPnl =
                                        typeof w.week_pnl_net === 'number'
                                            ? w.week_pnl_net
                                            : (w.pnl_net ?? 0);
                                    return (
                                        <tr key={w.week} className="hover:bg-boxel-canvas">
                                            <td className="p-2 font-mono font-bold text-foreground">
                                                {w.week}
                                            </td>
                                            <td className="p-2 font-mono text-right tabular-nums text-foreground">
                                                {tradesCount}
                                            </td>
                                            <td className="p-2 font-mono text-right tabular-nums text-foreground">
                                                ${midPnl.toFixed(2)}
                                            </td>
                                            <td
                                                className={`p-2 font-mono text-right tabular-nums font-bold ${
                                                    netPnl >= 0 ? 'text-success' : 'text-danger'
                                                }`}
                                            >
                                                ${netPnl.toFixed(2)}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Counterfactual Skipped Trades */}
            {results.skipped_trades.length > 0 && (
                <div className="flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                        <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                            Counterfactual Skipped Signals ({results.skipped_trades.length})
                        </span>
                        <span className="text-xs font-normal text-muted-foreground">
                            Signals blocked by technical filters or LLM classification
                        </span>
                    </div>
                    <div className="max-h-48 overflow-y-auto border border-border rounded-none">
                        <table className="w-full text-left text-xs font-normal">
                            <thead className="border-b border-border bg-boxel-canvas text-muted-foreground">
                                <tr>
                                    <th className="p-2 font-bold">Time</th>
                                    <th className="p-2 font-bold">Block Category</th>
                                    <th className="p-2 font-bold">Reason & Catalyst</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border">
                                {results.skipped_trades.slice(0, 15).map((s) => (
                                    <tr
                                        key={`${s.time}-${s.skip_type}-${s.reason.slice(0, 15)}`}
                                        className="hover:bg-boxel-canvas"
                                    >
                                        <td className="p-2 font-mono text-muted-foreground whitespace-nowrap">
                                            {s.time.replace('T', ' ').slice(0, 16)}
                                        </td>
                                        <td className="p-2">
                                            <Badge variant="outline" size="sm">
                                                {s.skip_type}
                                            </Badge>
                                        </td>
                                        <td className="p-2 text-muted-foreground">
                                            <div className="flex flex-col">
                                                <span className="font-bold text-foreground">
                                                    {s.reason}
                                                </span>
                                                {s.headline && (
                                                    <span className="italic">
                                                        Catalyst: {s.headline}
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Executed Trades */}
            {results.trades.length > 0 && (
                <div className="flex flex-col gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                        Executed Trades ({results.trades.length})
                    </span>
                    <div className="max-h-60 overflow-y-auto border border-border rounded-none">
                        <table className="w-full text-left text-xs font-normal">
                            <thead className="border-b border-border bg-boxel-canvas text-muted-foreground">
                                <tr>
                                    <th className="p-2 font-bold">Action</th>
                                    <th className="p-2 font-bold text-right">Entry</th>
                                    <th className="p-2 font-bold text-right">Exit</th>
                                    <th className="p-2 font-bold">Exit Reason</th>
                                    <th className="p-2 font-bold text-right">Net Return</th>
                                    <th className="p-2 font-bold text-right">Net P&L</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border">
                                {results.trades.map((t) => (
                                    <tr
                                        key={`${t.entry_time}-${t.ticker}-${t.exit_time}-${t.entry_price}`}
                                        className="hover:bg-boxel-canvas"
                                    >
                                        <td className="p-2">
                                            <Badge
                                                colorScheme={
                                                    t.action === 'BUY' ? 'success' : 'danger'
                                                }
                                                size="sm"
                                            >
                                                {t.action} {t.ticker}
                                            </Badge>
                                        </td>
                                        <td className="p-2 font-mono text-right tabular-nums text-foreground">
                                            ${t.entry_price.toFixed(2)}
                                        </td>
                                        <td className="p-2 font-mono text-right tabular-nums text-foreground">
                                            ${t.exit_price.toFixed(2)}
                                        </td>
                                        <td className="p-2 font-mono text-muted-foreground">
                                            {t.exit_reason}
                                        </td>
                                        <td
                                            className={`p-2 font-mono text-right tabular-nums font-bold ${
                                                t.return_pct_net >= 0
                                                    ? 'text-success'
                                                    : 'text-danger'
                                            }`}
                                        >
                                            {t.return_pct_net >= 0 ? '+' : ''}
                                            {t.return_pct_net.toFixed(2)}%
                                        </td>
                                        <td
                                            className={`p-2 font-mono text-right tabular-nums font-bold ${
                                                t.pnl_net >= 0 ? 'text-success' : 'text-danger'
                                            }`}
                                        >
                                            ${t.pnl_net.toFixed(2)}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}
