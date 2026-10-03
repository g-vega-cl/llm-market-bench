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
            <span className="px-3 py-1 text-xs font-bold rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/40 flex items-center gap-1">
                <span>🔮</span> Active Forecast (Pending)
            </span>
        );
    }

    const sectorScore = pred.sector_percentile_score ?? 0;
    if (sectorScore >= 75) {
        return (
            <span className="px-3 py-1 text-xs font-bold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                🎯 Top-Quartile Call ({sectorScore.toFixed(0)}th percentile)
            </span>
        );
    }

    if (sectorScore >= 50) {
        return (
            <span className="px-3 py-1 text-xs font-bold rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/40">
                🟢 Above Benchmark ({sectorScore.toFixed(0)}th percentile)
            </span>
        );
    }

    return (
        <span className="px-3 py-1 text-xs font-bold rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/40">
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
        <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-3 text-xs space-y-1">
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-1">
                <span className="text-slate-200 font-semibold flex items-center gap-1.5">
                    <span>🏆</span> Composite Predictor Score:{' '}
                    <strong className="text-emerald-400 font-mono text-sm">
                        {compositeScore} / 100
                    </strong>
                </span>
                <span className="text-slate-400 font-mono text-[11px]">
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
        <div className="space-y-2">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Score Constituents Breakdown
            </div>
            <div
                className={`grid grid-cols-1 ${
                    hasWorst ? 'md:grid-cols-3' : 'md:grid-cols-2'
                } gap-4`}
            >
                <div className="bg-slate-900/60 rounded-lg p-3 border border-slate-800 space-y-1">
                    <div className="flex justify-between items-center text-xs">
                        <span className="font-semibold text-slate-300">1️⃣ Best Sector Call</span>
                        <span className="text-slate-500 font-mono text-[10px]">
                            Best Sector Score
                        </span>
                    </div>
                    <div className="text-lg font-bold text-white flex items-center gap-2">
                        {pred.predicted_sector}
                        {!isPending && (
                            <span className="text-xs font-semibold text-emerald-400">
                                ({sectorScore.toFixed(1)} score)
                            </span>
                        )}
                    </div>
                    {!isPending && (
                        <div className="text-[11px] text-slate-400">
                            vs S&P Sector ETF Median (50th %ile)
                        </div>
                    )}
                </div>

                {hasWorst && (
                    <div className="bg-slate-900/60 rounded-lg p-3 border border-slate-800 space-y-1">
                        <div className="flex justify-between items-center text-xs">
                            <span className="font-semibold text-slate-300">
                                2️⃣ Worst Sector Call
                            </span>
                            <span className="text-slate-500 font-mono text-[10px]">
                                Worst Sector Score
                            </span>
                        </div>
                        <div className="text-lg font-bold text-rose-400 flex items-center gap-2">
                            {pred.predicted_worst_sector}
                            {!isPending && worstSectorScore != null && (
                                <span className="text-xs font-semibold text-rose-300">
                                    ({worstSectorScore.toFixed(1)} score)
                                </span>
                            )}
                        </div>
                        {!isPending && (
                            <div className="text-[11px] text-slate-400">
                                Bottom sector performance rank
                            </div>
                        )}
                    </div>
                )}

                <div className="bg-slate-900/60 rounded-lg p-3 border border-slate-800 space-y-1">
                    <div className="flex justify-between items-center text-xs">
                        <span className="font-semibold text-slate-300">
                            {hasWorst ? '3️⃣ Uncorrelated Pair' : '2️⃣ Uncorrelated Pair'}
                        </span>
                        <span className="text-slate-500 font-mono text-[10px]">Pair Score</span>
                    </div>
                    <div className="text-lg font-bold text-white flex items-center gap-2">
                        {pred.predicted_pair.join(' + ')}
                        {!isPending && (
                            <span className="text-xs font-semibold text-emerald-400">
                                ({pairScore.toFixed(1)} score)
                            </span>
                        )}
                    </div>
                    {!isPending && (
                        <div className="text-[11px] text-slate-400">
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
        <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-4 space-y-3">
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-1 border-b border-slate-800 pb-2">
                <span className="text-xs font-bold text-white flex items-center gap-1.5">
                    <span>🎯</span> Prediction vs S&P 500 Benchmark ({pred.timeframe} Window)
                </span>
                <span className="text-xs font-mono text-slate-300">
                    S&P 500 (SPY): {formatReturn(spyReturn)}
                </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800/80 space-y-1">
                    <div className="text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
                        Sector Call: {pred.predicted_sector}
                    </div>
                    <div className="flex justify-between items-baseline">
                        <span className="text-sm font-bold text-white">
                            Return: {formatReturn(sectorReturn)}
                        </span>
                        <span
                            className={`font-semibold font-mono text-xs ${
                                sectorAlpha >= 0 ? 'text-emerald-400' : 'text-rose-400'
                            }`}
                        >
                            {formatReturn(sectorAlpha)} vs S&P 500
                        </span>
                    </div>
                </div>

                <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800/80 space-y-1">
                    <div className="text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
                        Pair Call: {pred.predicted_pair.join(' + ')}
                    </div>
                    <div className="flex justify-between items-baseline">
                        <span className="text-sm font-bold text-white">
                            Return: {formatReturn(pairReturn)}
                        </span>
                        <span
                            className={`font-semibold font-mono text-xs ${
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
        <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-3 text-xs space-y-2">
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-1 text-slate-300 font-semibold text-[11px] border-b border-slate-800 pb-1.5">
                <span className="flex items-center gap-1">
                    <span>🔍</span> Data Audit & Price Verification
                </span>
                <span className="text-slate-400 font-mono text-[10px]">
                    Window: {auditData.start_date} ➔ {auditData.end_date}
                </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                {spy && (
                    <div className="flex justify-between items-center bg-slate-950/60 px-2.5 py-1.5 rounded border border-slate-850 font-mono">
                        <span className="text-slate-400 font-sans">S&P 500 (SPY):</span>
                        <span className="text-slate-200">
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
            className={`border rounded-xl p-5 space-y-4 transition-colors ${
                isPending
                    ? 'bg-slate-800/60 border-blue-500/40 shadow-sm'
                    : 'bg-slate-800/40 border-slate-700/80 hover:border-slate-600'
            }`}
        >
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3">
                <div className="flex items-center gap-3 flex-wrap">
                    <span
                        className={`px-2.5 py-1 text-xs font-bold rounded-md ${getModelBadgeStyle(
                            pred.model_name,
                        )}`}
                    >
                        {pred.model_name}
                    </span>
                    <span className="text-slate-400 text-sm font-medium">
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

            <div>
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    AI Rationale
                </div>
                <p className="text-xs text-slate-300 bg-slate-900/50 p-3 rounded-lg leading-relaxed border border-slate-850">
                    {pred.reasoning}
                </p>
            </div>
        </div>
    );
}
