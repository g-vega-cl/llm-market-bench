import type {
    EvaluationAuditData,
    EvaluationAuditItem,
    SectorPrediction,
} from '../api/fetch-predictions';

export function formatStableDate(dateStr: string): string {
    if (!dateStr) return 'N/A';
    const parts = dateStr.split('T')[0].split('-');
    if (parts.length === 3) {
        const year = parts[0];
        const monthStr = parts[1];
        const dayStr = parts[2];
        const months = [
            'Jan',
            'Feb',
            'Mar',
            'Apr',
            'May',
            'Jun',
            'Jul',
            'Aug',
            'Sep',
            'Oct',
            'Nov',
            'Dec',
        ];
        const monthIndex = parseInt(monthStr, 10) - 1;
        if (monthIndex >= 0 && monthIndex < 12) {
            const day = parseInt(dayStr, 10);
            return `${months[monthIndex]} ${day}, ${year}`;
        }
    }
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        timeZone: 'America/New_York',
        month: 'short',
        day: 'numeric',
        year: 'numeric',
    });
}

export function PredictionOutcomeBadge({ pred }: { pred: SectorPrediction }) {
    if (pred.status === 'pending') {
        return (
            <span className="px-3 py-1 text-xs font-bold rounded-none bg-blue-500/20 text-blue-400 border border-blue-500/40 shadow-sm flex items-center gap-1">
                <span>🔮</span> Active Forecast (Pending)
            </span>
        );
    }

    const sectorScore = pred.sector_percentile_score ?? 0;
    if (sectorScore >= 75) {
        return (
            <span className="px-3 py-1 text-xs font-bold rounded-none bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 shadow-sm">
                🎯 Top-Quartile Call ({sectorScore.toFixed(0)}th percentile)
            </span>
        );
    }

    if (sectorScore >= 50) {
        return (
            <span className="px-3 py-1 text-xs font-bold rounded-none bg-blue-500/20 text-blue-400 border border-blue-500/40 shadow-sm">
                🟢 Above Benchmark ({sectorScore.toFixed(0)}th percentile)
            </span>
        );
    }

    return (
        <span className="px-3 py-1 text-xs font-bold rounded-none bg-rose-500/20 text-rose-400 border border-rose-500/40 shadow-sm">
            🔴 Below Benchmark ({sectorScore.toFixed(0)}th percentile)
        </span>
    );
}

export function getModelBadgeStyle(modelName: string): string {
    const lower = modelName.toLowerCase();
    if (lower.includes('deepseek')) return 'bg-blue-500/20 text-blue-400 border border-blue-500/30';
    if (lower.includes('minimax'))
        return 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
    if (lower.includes('gemini'))
        return 'bg-amber-500/20 text-amber-400 border border-amber-500/30';
    if (lower.includes('gpt') || lower.includes('openai'))
        return 'bg-purple-500/20 text-purple-400 border border-purple-500/30';
    return 'bg-slate-500/20 text-slate-400 border border-slate-500/30';
}

export function computeCompositeScore(pred: SectorPrediction) {
    const components = [
        pred.sector_percentile_score,
        pred.worst_sector_percentile_score,
        pred.pair_percentile_score,
    ].filter((s): s is number => s != null);
    const baseScore =
        components.length > 0 ? components.reduce((a, b) => a + b, 0) / components.length : 0;

    const spDiff =
        pred.sector_sp_diff ??
        (pred.predicted_sector_return != null && pred.benchmark_spy_return != null
            ? pred.predicted_sector_return - pred.benchmark_spy_return
            : 0);
    const alphaBonus = Math.max(0, spDiff);
    const compositeScore = (baseScore + alphaBonus).toFixed(1);

    return { components, alphaBonus, compositeScore };
}

export function CompositeScoreBanner({ pred }: { pred: SectorPrediction }) {
    const { components, alphaBonus, compositeScore } = computeCompositeScore(pred);

    return (
        <div className="bg-boxel-canvas border border-boxel-bevel-hi rounded-none p-3 text-xs flex flex-col gap-1">
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-1">
                <span className="text-boxel-ink text-sm font-bold flex items-center gap-1.5">
                    <span>🏆</span> Composite Predictor Score:{' '}
                    <strong className="text-emerald-400 font-mono text-sm">
                        {compositeScore} / 100
                    </strong>
                </span>
                <span className="text-boxel-muted font-mono text-xs font-normal">
                    Formula: ({components.map((c) => c.toFixed(1)).join(' + ')}) ÷{' '}
                    {components.length}
                    {alphaBonus > 0 ? ` + ${alphaBonus.toFixed(1)} S&P Alpha` : ''}
                </span>
            </div>
        </div>
    );
}

export function ScoreConstituentsGrid({
    pred,
    isPending,
}: {
    pred: SectorPrediction;
    isPending: boolean;
}) {
    const hasWorst = Boolean(
        pred.predicted_worst_sector && pred.predicted_worst_sector !== 'UNKNOWN',
    );
    const sectorScore = pred.sector_percentile_score ?? 0;
    const worstSectorScore = pred.worst_sector_percentile_score;
    const pairScore = pred.pair_percentile_score ?? 0;

    return (
        <div className="flex flex-col gap-2">
            <div className="text-sm font-bold text-boxel-muted uppercase tracking-wider">
                Score Constituents Breakdown
            </div>
            <div
                className={`grid grid-cols-[repeat(auto-fit,minmax(min(100%,14rem),1fr))] gap-4 items-stretch`}
            >
                <div className="bg-boxel-trough rounded-none p-3 border border-boxel-bevel-hi flex flex-col justify-between gap-1 h-full">
                    <div className="flex justify-between items-center text-xs">
                        <span className="text-sm font-bold text-boxel-ink">1️⃣ Best Sector Call</span>
                        <span className="text-boxel-muted font-mono text-xs font-normal">
                            Best Sector Score
                        </span>
                    </div>
                    <div className="text-lg font-bold text-boxel-ink flex items-center gap-2">
                        {pred.predicted_sector}
                        {!isPending && (
                            <span className="text-xs font-normal text-emerald-400">
                                ({sectorScore.toFixed(1)} score)
                            </span>
                        )}
                    </div>
                    {!isPending && (
                        <div className="text-xs font-normal text-boxel-muted">
                            vs S&P Sector ETF Median (50th %ile)
                        </div>
                    )}
                </div>

                {hasWorst && (
                    <div className="bg-boxel-trough rounded-none p-3 border border-boxel-bevel-hi flex flex-col justify-between gap-1 h-full">
                        <div className="flex justify-between items-center text-xs">
                            <span className="text-sm font-bold text-boxel-ink">
                                2️⃣ Worst Sector Call
                            </span>
                            <span className="text-boxel-muted font-mono text-xs font-normal">
                                Worst Sector Score
                            </span>
                        </div>
                        <div className="text-lg font-bold text-rose-400 flex items-center gap-2">
                            {pred.predicted_worst_sector}
                            {!isPending && worstSectorScore != null && (
                                <span className="text-xs font-normal text-rose-300">
                                    ({worstSectorScore.toFixed(1)} score)
                                </span>
                            )}
                        </div>
                        {!isPending && (
                            <div className="text-xs font-normal text-boxel-muted">
                                Bottom sector performance rank
                            </div>
                        )}
                    </div>
                )}

                <div className="bg-boxel-trough rounded-none p-3 border border-boxel-bevel-hi flex flex-col justify-between gap-1 h-full">
                    <div className="flex justify-between items-center text-xs">
                        <span className="text-sm font-bold text-boxel-ink">
                            {hasWorst ? '3️⃣ Uncorrelated Pair' : '2️⃣ Uncorrelated Pair'}
                        </span>
                        <span className="text-boxel-muted font-mono text-xs font-normal">
                            Pair Score
                        </span>
                    </div>
                    <div className="text-lg font-bold text-boxel-ink flex items-center gap-2">
                        {pred.predicted_pair.join(' + ')}
                        {!isPending && (
                            <span className="text-xs font-normal text-emerald-400">
                                ({pairScore.toFixed(1)} score)
                            </span>
                        )}
                    </div>
                    {!isPending && (
                        <div className="text-xs font-normal text-boxel-muted">
                            Multi-asset uncorrelation basket rank
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export function BenchmarkComparisonBlock({ pred }: { pred: SectorPrediction }) {
    const spyReturn = pred.benchmark_spy_return ?? 0;
    const sectorReturn = pred.predicted_sector_return ?? 0;
    const pairReturn = pred.predicted_pair_return ?? 0;

    const sectorAlpha = sectorReturn - spyReturn;
    const pairAlpha = pairReturn - spyReturn;

    const formatReturn = (val: number) => (val >= 0 ? `+${val.toFixed(1)}%` : `${val.toFixed(1)}%`);

    return (
        <div className="bg-boxel-trough border border-boxel-bevel-hi rounded-none p-4 flex flex-col gap-3">
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-1 border-b border-boxel-bevel-hi pb-2">
                <span className="text-sm font-bold text-boxel-ink flex items-center gap-1.5">
                    <span>🎯</span> Prediction vs S&P 500 Benchmark ({pred.timeframe} Window)
                </span>
                <span className="text-xs font-normal font-mono text-boxel-muted">
                    S&P 500 (SPY): {formatReturn(spyReturn)}
                </span>
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,14rem),1fr))] gap-4 text-xs font-normal items-stretch">
                <div className="bg-boxel-canvas p-3 rounded-none border border-boxel-bevel-hi flex flex-col justify-between gap-1 h-full">
                    <div className="text-boxel-muted text-sm font-bold uppercase tracking-wider">
                        Sector Call: {pred.predicted_sector}
                    </div>
                    <div className="flex justify-between items-baseline">
                        <span className="text-sm font-bold text-boxel-ink">
                            Return: {formatReturn(sectorReturn)}
                        </span>
                        <span
                            className={`font-mono text-xs font-normal ${
                                sectorAlpha >= 0 ? 'text-emerald-400' : 'text-rose-400'
                            }`}
                        >
                            {formatReturn(sectorAlpha)} vs S&P 500
                        </span>
                    </div>
                </div>

                <div className="bg-boxel-canvas p-3 rounded-none border border-boxel-bevel-hi flex flex-col justify-between gap-1 h-full">
                    <div className="text-boxel-muted text-sm font-bold uppercase tracking-wider">
                        Pair Call: {pred.predicted_pair.join(' + ')}
                    </div>
                    <div className="flex justify-between items-baseline">
                        <span className="text-sm font-bold text-boxel-ink">
                            Return: {formatReturn(pairReturn)}
                        </span>
                        <span
                            className={`font-mono text-xs font-normal ${
                                pairAlpha >= 0 ? 'text-emerald-400' : 'text-rose-400'
                            }`}
                        >
                            {formatReturn(pairAlpha)} vs S&P 500
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}

export function DataAuditBlock({ auditData }: { auditData: EvaluationAuditData }) {
    const spy = auditData.spy;
    const sector = auditData.sector;
    const pairs = auditData.pair || [];

    const formatPrice = (p: number) => `$${p.toFixed(2)}`;
    const formatRet = (val: number) => (val >= 0 ? `+${val.toFixed(1)}%` : `${val.toFixed(1)}%`);

    return (
        <div className="bg-boxel-trough border border-boxel-bevel-hi rounded-none p-3 text-xs font-normal flex flex-col gap-2">
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-1 text-boxel-ink text-sm font-bold border-b border-boxel-bevel-hi pb-1.5">
                <span className="flex items-center gap-1">
                    <span>🔍</span> Data Audit & Price Verification
                </span>
                <span className="text-boxel-muted font-mono text-xs font-normal">
                    Window: {auditData.start_date} ➔ {auditData.end_date}
                </span>
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,14rem),1fr))] gap-2 text-xs font-normal items-stretch">
                {spy && (
                    <div className="flex justify-between items-center bg-boxel-canvas px-2.5 py-1.5 rounded-none border border-boxel-bevel-hi font-mono">
                        <span className="text-boxel-muted font-sans">S&P 500 (SPY):</span>
                        <span className="text-boxel-ink">
                            {formatPrice(spy.start_price)} ➔ {formatPrice(spy.end_price)}{' '}
                            <span
                                className={
                                    spy.return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
                                }
                            >
                                ({formatRet(spy.return_pct)})
                            </span>
                        </span>
                    </div>
                )}

                {sector && (
                    <div className="flex justify-between items-center bg-slate-950/60 px-2.5 py-1.5 rounded border border-slate-850 font-mono">
                        <span className="text-slate-400 font-sans">
                            Best Sector ({sector.ticker}):
                        </span>
                        <span className="text-slate-200">
                            {formatPrice(sector.start_price)} ➔ {formatPrice(sector.end_price)}{' '}
                            <span
                                className={
                                    sector.return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
                                }
                            >
                                ({formatRet(sector.return_pct)})
                            </span>
                        </span>
                    </div>
                )}

                {auditData.worst_sector && (
                    <div className="flex justify-between items-center bg-slate-950/60 px-2.5 py-1.5 rounded border border-slate-850 font-mono">
                        <span className="text-rose-400 font-sans">
                            Worst Sector ({auditData.worst_sector.ticker}):
                        </span>
                        <span className="text-slate-200">
                            {formatPrice(auditData.worst_sector.start_price)} ➔{' '}
                            {formatPrice(auditData.worst_sector.end_price)}{' '}
                            <span
                                className={
                                    auditData.worst_sector.return_pct <= 0
                                        ? 'text-emerald-400'
                                        : 'text-rose-400'
                                }
                            >
                                ({formatRet(auditData.worst_sector.return_pct)})
                            </span>
                        </span>
                    </div>
                )}

                {pairs.map((item: EvaluationAuditItem) => (
                    <div
                        key={item.ticker}
                        className="flex justify-between items-center bg-slate-950/60 px-2.5 py-1.5 rounded border border-slate-850 font-mono"
                    >
                        <span className="text-slate-400 font-sans">
                            Pair Asset ({item.ticker}):
                        </span>
                        <span className="text-slate-200">
                            {formatPrice(item.start_price)} ➔ {formatPrice(item.end_price)}{' '}
                            <span
                                className={
                                    item.return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
                                }
                            >
                                ({formatRet(item.return_pct)})
                            </span>
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}

export interface PredictionFeedCardProps {
    pred: SectorPrediction;
}

export function PredictionFeedCard({ pred }: PredictionFeedCardProps) {
    const isPending = pred.status === 'pending';
    const hasBenchmarkData =
        pred.benchmark_spy_return != null && pred.predicted_sector_return != null;

    return (
        <div
            className={`border border-boxel-bevel-hi rounded-none p-5 flex flex-col gap-4 bg-boxel-surface transition-colors shadow-sm`}
        >
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3">
                <div className="flex items-center gap-3 flex-wrap">
                    <span
                        className={`px-2.5 py-1 text-sm font-bold rounded-none ${getModelBadgeStyle(
                            pred.model_name,
                        )}`}
                    >
                        {pred.model_name}
                    </span>
                    <span className="text-boxel-muted text-xs font-normal">
                        Target: {formatStableDate(pred.target_date)} ({pred.timeframe})
                    </span>
                </div>

                <div>
                    <PredictionOutcomeBadge pred={pred} />
                </div>
            </div>

            {/* S&P 500 Benchmark Window Return Comparison Block */}
            {!isPending && hasBenchmarkData && <BenchmarkComparisonBlock pred={pred} />}

            {/* Data Audit & Price Verification Block */}
            {!isPending && pred.evaluation_audit_data && (
                <DataAuditBlock auditData={pred.evaluation_audit_data} />
            )}

            {/* Evaluated Composite Score Formula Banner */}
            {!isPending && <CompositeScoreBanner pred={pred} />}

            {/* Score Constituents Breakdown */}
            <ScoreConstituentsGrid pred={pred} isPending={isPending} />

            <div className="flex flex-col gap-1">
                <div className="text-sm font-bold text-boxel-muted uppercase tracking-wider">
                    AI Rationale
                </div>
                <p className="text-xs font-normal text-boxel-ink bg-boxel-trough p-3 rounded-none leading-relaxed border border-boxel-bevel-hi">
                    {pred.reasoning}
                </p>
            </div>
        </div>
    );
}
