import { Badge } from '@llm-market-bench/ui-design-system';
import { useState } from 'react';
import type {
    BacktestResultData,
    CompletedTradeRecord,
    SkippedTradeRecord,
    WeekBreakdown,
} from '../types';

interface RecipeBacktestResultsProps {
    results: BacktestResultData | null;
    isLoading?: boolean;
}

const TABLE_HEAD_CLASS = 'border-b border-border bg-boxel-canvas text-muted-foreground';
const SECTION_LABEL_CLASS = 'text-xs font-bold uppercase tracking-wider text-muted-foreground';

function signedPct(value: number): string {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function pnlColor(value: number): string {
    return value >= 0 ? 'text-success' : 'text-danger';
}

function normalizeWeek(w: WeekBreakdown) {
    return {
        week: w.week,
        trades: typeof w.trades_count === 'number' ? w.trades_count : (w.trades ?? 0),
        midPnl:
            typeof w.week_pnl_midpoint === 'number' ? w.week_pnl_midpoint : (w.pnl_midpoint ?? 0),
        netPnl: typeof w.week_pnl_net === 'number' ? w.week_pnl_net : (w.pnl_net ?? 0),
    };
}

function StatePanel({
    title,
    detail,
    titleClass,
    borderClass,
}: {
    title: string;
    detail: string;
    titleClass: string;
    borderClass: string;
}) {
    return (
        <div
            className={`flex flex-col items-center justify-center ${borderClass} bg-boxel-canvas p-8 rounded-none`}
        >
            <span className={titleClass}>{title}</span>
            <span className="text-xs font-normal text-muted-foreground">{detail}</span>
        </div>
    );
}

function StatCard({
    label,
    value,
    valueClass = 'text-foreground',
}: {
    label: string;
    value: string | number | undefined;
    valueClass?: string;
}) {
    return (
        <div className="flex flex-col gap-1 border border-border bg-boxel-canvas p-3 rounded-none">
            <span className="text-xs font-normal text-muted-foreground">{label}</span>
            <span className={`font-mono text-sm font-bold tabular-nums ${valueClass}`}>
                {value}
            </span>
        </div>
    );
}

function PnlModeButton({
    active,
    label,
    onClick,
}: {
    active: boolean;
    label: string;
    onClick: () => void;
}) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={`px-2 py-1 text-xs font-bold rounded-none ${
                active
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-boxel-canvas text-muted-foreground'
            }`}
        >
            {label}
        </button>
    );
}

function WeeksTable({ weeks }: { weeks: WeekBreakdown[] }) {
    return (
        <div className="flex flex-col gap-2">
            <span className={SECTION_LABEL_CLASS}>ISO Week Performance Breakdown</span>
            <div className="overflow-x-auto border border-border rounded-none">
                <table className="w-full text-left text-xs font-normal">
                    <thead className={TABLE_HEAD_CLASS}>
                        <tr>
                            <th className="p-2 font-bold">Week</th>
                            <th className="p-2 font-bold text-right">Trades</th>
                            <th className="p-2 font-bold text-right">Midpoint P&L</th>
                            <th className="p-2 font-bold text-right">Net P&L</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                        {weeks.map(normalizeWeek).map((w) => (
                            <tr key={w.week} className="hover:bg-boxel-canvas">
                                <td className="p-2 font-mono font-bold text-foreground">
                                    {w.week}
                                </td>
                                <td className="p-2 font-mono text-right tabular-nums text-foreground">
                                    {w.trades}
                                </td>
                                <td className="p-2 font-mono text-right tabular-nums text-foreground">
                                    ${w.midPnl.toFixed(2)}
                                </td>
                                <td
                                    className={`p-2 font-mono text-right tabular-nums font-bold ${pnlColor(w.netPnl)}`}
                                >
                                    ${w.netPnl.toFixed(2)}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function SkippedSignalsTable({ skipped }: { skipped: SkippedTradeRecord[] }) {
    return (
        <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
                <span className={SECTION_LABEL_CLASS}>
                    Counterfactual Skipped Signals ({skipped.length})
                </span>
                <span className="text-xs font-normal text-muted-foreground">
                    Signals blocked by technical filters or LLM classification
                </span>
            </div>
            <div className="max-h-48 overflow-y-auto border border-border rounded-none">
                <table className="w-full text-left text-xs font-normal">
                    <thead className={TABLE_HEAD_CLASS}>
                        <tr>
                            <th className="p-2 font-bold">Time</th>
                            <th className="p-2 font-bold">Block Category</th>
                            <th className="p-2 font-bold">Reason & Catalyst</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                        {skipped.slice(0, 15).map((s) => (
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
                                            <span className="italic">Catalyst: {s.headline}</span>
                                        )}
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function ExecutedTradesTable({ trades }: { trades: CompletedTradeRecord[] }) {
    return (
        <div className="flex flex-col gap-2">
            <span className={SECTION_LABEL_CLASS}>Executed Trades ({trades.length})</span>
            <div className="max-h-60 overflow-y-auto border border-border rounded-none">
                <table className="w-full text-left text-xs font-normal">
                    <thead className={TABLE_HEAD_CLASS}>
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
                        {trades.map((t) => (
                            <tr
                                key={`${t.entry_time}-${t.ticker}-${t.exit_time}-${t.entry_price}`}
                                className="hover:bg-boxel-canvas"
                            >
                                <td className="p-2">
                                    <Badge
                                        colorScheme={t.action === 'BUY' ? 'success' : 'danger'}
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
                                    className={`p-2 font-mono text-right tabular-nums font-bold ${pnlColor(t.return_pct_net)}`}
                                >
                                    {signedPct(t.return_pct_net)}
                                </td>
                                <td
                                    className={`p-2 font-mono text-right tabular-nums font-bold ${pnlColor(t.pnl_net)}`}
                                >
                                    ${t.pnl_net.toFixed(2)}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export function RecipeBacktestResults({ results, isLoading = false }: RecipeBacktestResultsProps) {
    const [useNetPnL, setUseNetPnL] = useState(true);

    if (isLoading) {
        return (
            <StatePanel
                title="Executing Timeline Simulation..."
                detail="Stepping through intraday candles & news catalysts"
                titleClass="font-display text-lg font-bold text-foreground"
                borderClass="border border-border"
            />
        );
    }

    if (!results) {
        return (
            <StatePanel
                title="No Backtest Results Yet"
                detail={
                    'Configure your blocks above and click "Run Simulation" to evaluate strategy performance.'
                }
                titleClass="text-sm font-bold text-muted-foreground"
                borderClass="border border-dashed border-border"
            />
        );
    }

    const returnPct = useNetPnL ? results.total_return_pct_net : results.total_return_pct_midpoint;
    const endingCap = useNetPnL ? results.ending_capital_net : results.ending_capital_midpoint;
    const weeks = results.weeks_breakdown ?? [];
    const skipped = results.skipped_trades ?? [];

    return (
        <div className="flex flex-col gap-4 border border-border bg-boxel-surface p-4 rounded-none voxel-card">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
                <div className="flex items-center gap-2">
                    <span className="font-display text-lg font-bold text-foreground">
                        Simulation Telemetry
                    </span>
                    <Badge colorScheme={returnPct >= 0 ? 'success' : 'danger'} size="sm">
                        {signedPct(returnPct)}
                    </Badge>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-xs font-normal text-muted-foreground">P&L Model:</span>
                    <PnlModeButton
                        active={!useNetPnL}
                        label="Midpoint (Zero-Cost)"
                        onClick={() => setUseNetPnL(false)}
                    />
                    <PnlModeButton
                        active={useNetPnL}
                        label="Spread & Slippage Adjusted"
                        onClick={() => setUseNetPnL(true)}
                    />
                </div>
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,8rem),1fr))] gap-3">
                <StatCard
                    label="Ending Capital"
                    value={`$${(endingCap ?? 10000).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
                />
                <StatCard
                    label="Win Rate"
                    value={`${results.win_rate_pct}% (${results.winning_trades}/${results.total_trades})`}
                />
                <StatCard label="Profit Factor" value={results.profit_factor} />
                <StatCard
                    label="Max Drawdown"
                    value={`-${results.max_drawdown_pct}%`}
                    valueClass="text-red-400"
                />
                <StatCard label="Completed Trades" value={results.total_trades} />
                <StatCard label="LLM Invocations" value={results.llm_calls_made} />
            </div>

            {weeks.length > 0 && <WeeksTable weeks={weeks} />}
            {skipped.length > 0 && <SkippedSignalsTable skipped={skipped} />}
            {results.trades.length > 0 && <ExecutedTradesTable trades={results.trades} />}
        </div>
    );
}
