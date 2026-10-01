import { Badge, Card } from '@llm-market-bench/ui-design-system';

export interface DailyMetricsOverviewProps {
    accuracyPct: string;
    intradayHitPct: string;
    correctCount: number;
    totalEvaluated: number;
    avgBrier: string;
    totalPredictions: number;
    activePromptTag: string;
}

export function DailyMetricsOverview({
    accuracyPct,
    intradayHitPct,
    correctCount,
    totalEvaluated,
    avgBrier,
    totalPredictions,
    activePromptTag,
}: DailyMetricsOverviewProps) {
    return (
        <div
            style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 12rem), 1fr))',
                gap: '16px',
                marginBottom: '24px',
            }}
        >
            <Card className="p-5 flex flex-col justify-between">
                <div className="text-xs font-semibold text-zinc-500 dark:text-zinc-400">
                    Directional Accuracy
                </div>
                <div className="text-2xl font-bold text-zinc-900 dark:text-white mt-1 tabular-nums">
                    {accuracyPct}%
                </div>
                <div className="text-xs text-zinc-400 dark:text-zinc-500 mt-1">
                    {correctCount} / {totalEvaluated} correct
                </div>
            </Card>

            <Card className="p-5 flex flex-col justify-between">
                <div className="text-xs font-semibold text-zinc-500 dark:text-zinc-400">
                    Intraday Target Hit (30%)
                </div>
                <div className="text-2xl font-bold text-zinc-900 dark:text-white mt-1 tabular-nums">
                    {intradayHitPct}%
                </div>
                <div className="text-xs text-zinc-400 dark:text-zinc-500 mt-1">
                    Target reached intraday
                </div>
            </Card>

            <Card className="p-5 flex flex-col justify-between">
                <div className="text-xs font-semibold text-zinc-500 dark:text-zinc-400">
                    Brier Calibration Score
                </div>
                <div className="text-2xl font-bold text-zinc-900 dark:text-white mt-1 tabular-nums">
                    {avgBrier}
                </div>
                <div className="text-xs text-zinc-400 dark:text-zinc-500 mt-1">
                    Lower is better (0.0000 = perfect)
                </div>
            </Card>

            <Card className="p-5 flex flex-col justify-between">
                <div className="text-xs font-semibold text-zinc-500 dark:text-zinc-400">
                    Total Predictions
                </div>
                <div className="text-2xl font-bold text-zinc-900 dark:text-white mt-1 tabular-nums">
                    {totalPredictions}
                </div>
                <div className="text-xs text-zinc-400 dark:text-zinc-500 mt-1">
                    Logged predictions count
                </div>
            </Card>

            <Card className="p-5 flex flex-col justify-between">
                <div className="flex justify-between items-center">
                    <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400">
                        Active Prompt Variant
                    </span>
                    <Badge colorScheme="success" variant="soft" size="xs">
                        🟢 ACTIVE
                    </Badge>
                </div>
                <div className="text-lg font-bold text-blue-600 dark:text-blue-400 mt-2 break-all">
                    {activePromptTag}
                </div>
                <div className="text-xs text-zinc-400 dark:text-zinc-500 mt-1">
                    Mutates weekly (Sundays)
                </div>
            </Card>
        </div>
    );
}
