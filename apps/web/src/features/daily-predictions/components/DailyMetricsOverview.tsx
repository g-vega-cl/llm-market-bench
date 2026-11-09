import { Badge, Card } from '@llm-market-bench/ui-design-system';

export interface DailyMetricsOverviewProps {
    accuracyPct: string;
    intradayHitPct: string;
    correctCount: number;
    totalEvaluated: number;
    tradedEvaluated?: number;
    holdCount?: number;
    convictionScore: string;
    totalPredictions: number;
    activePromptTag: string;
}

export function DailyMetricsOverview({
    accuracyPct,
    intradayHitPct,
    correctCount,
    totalEvaluated,
    tradedEvaluated,
    holdCount,
    convictionScore,
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
                    {correctCount} / {tradedEvaluated ?? totalEvaluated} correct
                    {holdCount && holdCount > 0 ? ` (${holdCount} HOLD)` : ''}
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
                    Conviction Score
                </div>
                <div className="text-lg font-bold text-boxel-ink mt-0.5 tabular-nums font-mono">
                    {convictionScore}
                </div>
                <div className="text-xs font-normal text-boxel-muted mt-0.5">
                    Calibrated confidence · 50 = coin flip
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
