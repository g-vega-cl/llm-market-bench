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
        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,12rem),1fr))] gap-4 items-stretch mb-6">
            <Card padding="sm" className="h-full flex flex-col justify-between gap-1">
                <div className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                    Directional Accuracy
                </div>
                <div className="text-lg font-bold text-boxel-ink mt-0.5 tabular-nums font-mono">
                    {accuracyPct}%
                </div>
                <div className="text-xs font-normal text-boxel-muted mt-0.5">
                    {correctCount} / {totalEvaluated} correct
                </div>
            </Card>

            <Card padding="sm" className="h-full flex flex-col justify-between gap-1">
                <div className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                    Intraday Target Hit (30%)
                </div>
                <div className="text-lg font-bold text-boxel-ink mt-0.5 tabular-nums font-mono">
                    {intradayHitPct}%
                </div>
                <div className="text-xs font-normal text-boxel-muted mt-0.5">
                    Target reached intraday
                </div>
            </Card>

            <Card padding="sm" className="h-full flex flex-col justify-between gap-1">
                <div className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                    Brier Calibration Score
                </div>
                <div className="text-lg font-bold text-boxel-ink mt-0.5 tabular-nums font-mono">
                    {avgBrier}
                </div>
                <div className="text-xs font-normal text-boxel-muted mt-0.5">
                    Lower is better (0.0000 = perfect)
                </div>
            </Card>

            <Card padding="sm" className="h-full flex flex-col justify-between gap-1">
                <div className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                    Total Predictions
                </div>
                <div className="text-lg font-bold text-boxel-ink mt-0.5 tabular-nums font-mono">
                    {totalPredictions}
                </div>
                <div className="text-xs font-normal text-boxel-muted mt-0.5">
                    Logged predictions count
                </div>
            </Card>

            <Card padding="sm" className="h-full flex flex-col justify-between gap-1">
                <div className="flex justify-between items-center gap-1">
                    <span className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                        Active Prompt Variant
                    </span>
                    <Badge colorScheme="success" variant="solid" size="xs">
                        ACTIVE
                    </Badge>
                </div>
                <div className="text-sm font-bold text-accent mt-1 break-all">
                    {activePromptTag}
                </div>
                <div className="text-xs font-normal text-boxel-muted mt-0.5">
                    Mutates weekly (Sundays)
                </div>
            </Card>
        </div>
    );
}
