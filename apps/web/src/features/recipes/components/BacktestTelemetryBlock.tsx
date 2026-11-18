import { Button, Card, MetricTile, SectionHeading } from '@llm-market-bench/ui-design-system';
import { useState } from 'react';
import type { BacktestResultData } from '../types';

interface BacktestTelemetryBlockProps {
    results: BacktestResultData | null;
    isRunning: boolean;
}

function signedPct(value: number): string {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function formatDollar(value: number): string {
    return `$${value.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    })}`;
}

function EquityProgression({
    startingCapital,
    equityCurve,
}: {
    startingCapital: number;
    equityCurve: { time: string; equity: number }[];
}) {
    const equities = equityCurve.map((pt) => pt.equity);
    const minEq = equities.length > 0 ? Math.min(startingCapital, ...equities) : startingCapital;
    const maxEq = equities.length > 0 ? Math.max(startingCapital, ...equities) : startingCapital;
    const eqRange = Math.max(1, maxEq - minEq);

    return (
        <div className="voxel-trough bg-voxel-trough p-4 flex flex-col gap-2 min-w-0">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="text-sm font-bold text-voxel-ink">Equity Progression</span>
                <span className="text-xs font-normal font-mono tabular-nums text-voxel-muted">
                    Baseline: ${startingCapital.toLocaleString()}
                </span>
            </div>
            {equityCurve.length === 0 ? (
                <span className="text-xs font-normal text-voxel-muted">
                    Daily equity checkpoints will stream in after Day 1 finishes.
                </span>
            ) : (
                <div className="flex flex-col gap-2">
                    {equityCurve.map((pt) => {
                        const fillPct = Math.max(
                            8,
                            Math.min(100, Math.round(((pt.equity - minEq) / eqRange) * 100)),
                        );
                        const isUp = pt.equity >= startingCapital;
                        return (
                            <div
                                key={pt.time}
                                className="flex flex-wrap items-center gap-4 min-w-0"
                            >
                                <span className="text-xs font-normal font-mono tabular-nums text-voxel-muted whitespace-nowrap">
                                    {pt.time}
                                </span>
                                <div className="flex-1 basis-40 min-w-0 h-3 bg-voxel-canvas border border-voxel-bevel-lo">
                                    <div
                                        className={`h-full ${isUp ? 'bg-success' : 'bg-danger'}`}
                                        style={{ width: `${fillPct}%` }}
                                    />
                                </div>
                                <span
                                    className={`text-xs font-normal font-mono tabular-nums whitespace-nowrap ${
                                        isUp ? 'text-success' : 'text-danger'
                                    }`}
                                >
                                    {formatDollar(pt.equity)}
                                </span>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}

function readTelemetrySummary(results: BacktestResultData | null, useNetPnL: boolean) {
    const startingCapital = results?.starting_capital ?? 10000;
    const endingCap = useNetPnL
        ? (results?.ending_capital_net ?? startingCapital)
        : (results?.ending_capital_midpoint ?? startingCapital);
    const returnPct = useNetPnL
        ? (results?.total_return_pct_net ?? 0)
        : (results?.total_return_pct_midpoint ?? 0);
    return {
        startingCapital,
        endingCap,
        returnPct,
        winRate: results?.win_rate_pct ?? 0,
        winningTrades: results?.winning_trades ?? 0,
        totalTrades: results?.total_trades ?? 0,
        profitFactor: results?.profit_factor ?? 0,
        maxDrawdown: results?.max_drawdown_pct ?? 0,
        llmCalls: results?.llm_calls_made ?? 0,
        totalDays: results?.total_days ?? results?.window_dates?.length ?? 10,
        equityCurve: results?.equity_curve ?? [],
    };
}

export function BacktestTelemetryBlock({ results, isRunning }: BacktestTelemetryBlockProps) {
    const [useNetPnL, setUseNetPnL] = useState(true);
    const summary = readTelemetrySummary(results, useNetPnL);

    return (
        <Card padding="md" className="flex flex-col gap-4 min-w-0">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-voxel-bevel-hi pb-3">
                <SectionHeading>Developing Telemetry</SectionHeading>
                <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-normal text-voxel-muted">P&amp;L Model:</span>
                    <Button
                        size="sm"
                        variant={!useNetPnL ? 'solid' : 'outline'}
                        onClick={() => setUseNetPnL(false)}
                    >
                        Midpoint (Zero-Cost)
                    </Button>
                    <Button
                        size="sm"
                        variant={useNetPnL ? 'solid' : 'outline'}
                        onClick={() => setUseNetPnL(true)}
                    >
                        Spread &amp; Slippage Net
                    </Button>
                </div>
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,11rem),1fr))] gap-4">
                <MetricTile
                    label="Ending Capital"
                    value={
                        <span className="font-mono tabular-nums">
                            {formatDollar(summary.endingCap)}
                        </span>
                    }
                />
                <MetricTile
                    label="Total Return"
                    value={
                        <span
                            className={`font-mono tabular-nums ${
                                summary.returnPct >= 0 ? 'text-success' : 'text-danger'
                            }`}
                        >
                            {signedPct(summary.returnPct)}
                        </span>
                    }
                />
                <MetricTile
                    label="Win Rate"
                    value={`${summary.winRate}% (${summary.winningTrades}/${summary.totalTrades})`}
                />
                <MetricTile label="Profit Factor" value={summary.profitFactor} />
                <MetricTile
                    label="Max Drawdown"
                    value={
                        <span className="font-mono tabular-nums text-danger">
                            -{summary.maxDrawdown}%
                        </span>
                    }
                />
                <MetricTile
                    label="LLM Calls"
                    value={
                        isRunning
                            ? `${summary.llmCalls} / ${summary.totalDays}`
                            : `${summary.llmCalls}`
                    }
                />
            </div>

            <EquityProgression
                startingCapital={summary.startingCapital}
                equityCurve={summary.equityCurve}
            />
        </Card>
    );
}
