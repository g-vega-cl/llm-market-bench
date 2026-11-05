import type { PromptExperiment } from '@llm-market-bench/database';
import { Card, MetricTile, SectionHeading } from '@llm-market-bench/ui-design-system';
import { useState } from 'react';
import { meanConvictionPoints, normalizeConvictionPoints } from '~/shared/conviction';
import type { SectorPrediction } from '../api/fetch-predictions';

export interface SectorScoreBreakdownProps {
    experiment: PromptExperiment;
    predictions?: SectorPrediction[];
    baselineScore?: number | null;
}

export interface SectorRatchetMetrics {
    score: number;
    basePercentile: number;
    alphaBonus: number;
    meanBrier: number;
    convictionNorm: number;
    convictionMeanCp: number;
    hasConviction: boolean;
    predictionsEvaluated: number;
    basePercentilePoints: number;
    alphaBonusPoints: number;
    accuracyBlockPoints: number;
    convictionContribution: number;
}

const ACCURACY_WEIGHT = 0.9;
const CONVICTION_WEIGHT = 0.1;

function calculatePredictionBaseScore(p: SectorPrediction): number | null {
    const sScore = p.sector_percentile_score;
    const wScore = p.worst_sector_percentile_score;
    const pScore = p.pair_percentile_score;

    const components = [sScore, wScore, pScore].filter(
        (s): s is number => s !== null && s !== undefined,
    );
    if (components.length === 0) return null;
    return components.reduce((a, b) => a + b, 0) / components.length;
}

function calculatePredictionAlpha(p: SectorPrediction): number {
    let spDiff = p.sector_sp_diff;
    if (spDiff === null || spDiff === undefined) {
        const secRet = p.predicted_sector_return;
        const spyRet = p.benchmark_spy_return;
        if (secRet != null && spyRet != null) {
            spDiff = secRet - spyRet;
        }
    }
    return spDiff != null ? Math.max(0.0, spDiff) : 0.0;
}

export function computeSectorMetricsFromSample(
    sample: SectorPrediction[],
    rawScore?: unknown,
): SectorRatchetMetrics {
    const predScores: number[] = [];
    const basePercentiles: number[] = [];
    const alphaBonuses: number[] = [];
    const brierScores: number[] = [];

    for (const p of sample) {
        const baseScore = calculatePredictionBaseScore(p);
        if (baseScore === null) continue;

        const alphaBonus = calculatePredictionAlpha(p);
        basePercentiles.push(baseScore);
        alphaBonuses.push(alphaBonus);
        predScores.push(baseScore + alphaBonus);

        if (p.brier_score !== null && p.brier_score !== undefined) {
            brierScores.push(Number(p.brier_score));
        }
    }

    const evaluatedCount = predScores.length;
    const avgBasePercentile =
        basePercentiles.length > 0
            ? basePercentiles.reduce((a, b) => a + b, 0) / basePercentiles.length
            : 50.0;
    const avgAlphaBonus =
        alphaBonuses.length > 0
            ? alphaBonuses.reduce((a, b) => a + b, 0) / alphaBonuses.length
            : 0.0;
    const meanBrier =
        brierScores.length > 0 ? brierScores.reduce((a, b) => a + b, 0) / brierScores.length : 0.25;

    const meanCp = meanConvictionPoints(sample);
    const convictionNorm = meanCp === null ? 50.0 : normalizeConvictionPoints(meanCp);
    const accuracyBlockPoints = avgBasePercentile + avgAlphaBonus;

    const computedScore =
        typeof rawScore === 'number'
            ? Number(rawScore)
            : accuracyBlockPoints * ACCURACY_WEIGHT + convictionNorm * CONVICTION_WEIGHT;

    return {
        score: computedScore,
        basePercentile: avgBasePercentile,
        alphaBonus: avgAlphaBonus,
        meanBrier,
        convictionNorm,
        convictionMeanCp: meanCp ?? 0.0,
        hasConviction: meanCp !== null,
        predictionsEvaluated: evaluatedCount,
        basePercentilePoints: avgBasePercentile,
        alphaBonusPoints: avgAlphaBonus,
        accuracyBlockPoints,
        convictionContribution: convictionNorm * CONVICTION_WEIGHT,
    };
}

export function extractSectorMetrics(
    experiment: PromptExperiment,
    predictions?: SectorPrediction[],
): SectorRatchetMetrics {
    const rawMetrics = (experiment.metrics || {}) as Record<string, unknown>;

    if (
        typeof rawMetrics.score === 'number' &&
        typeof rawMetrics.base_percentile === 'number' &&
        typeof rawMetrics.alpha_bonus === 'number'
    ) {
        const score = Number(rawMetrics.score);
        const basePercentile = Number(rawMetrics.base_percentile);
        const alphaBonus = Number(rawMetrics.alpha_bonus);
        const meanBrier =
            typeof rawMetrics.mean_brier === 'number' ? Number(rawMetrics.mean_brier) : 0.25;
        const convictionNorm =
            typeof rawMetrics.conviction_norm === 'number'
                ? Number(rawMetrics.conviction_norm)
                : 50.0;
        const evaluated = Number(rawMetrics.predictions_evaluated || 0);
        const accuracyBlockPoints = basePercentile + alphaBonus;

        return {
            score,
            basePercentile,
            alphaBonus,
            meanBrier,
            convictionNorm,
            convictionMeanCp:
                typeof rawMetrics.conviction_mean_cp === 'number'
                    ? Number(rawMetrics.conviction_mean_cp)
                    : 0.0,
            hasConviction: typeof rawMetrics.conviction_norm === 'number',
            predictionsEvaluated: evaluated,
            basePercentilePoints: basePercentile,
            alphaBonusPoints: alphaBonus,
            accuracyBlockPoints,
            convictionContribution: convictionNorm * CONVICTION_WEIGHT,
        };
    }

    if (predictions && predictions.length > 0) {
        const matching = predictions.filter((p) => {
            if (p.prompt_tag && p.prompt_tag === experiment.variant_tag) return true;
            if (experiment.track_id && p.model_name.includes(experiment.track_id)) return true;
            return false;
        });

        if (matching.length > 0) {
            return computeSectorMetricsFromSample(matching, rawMetrics.score);
        }
    }

    const fallbackScore = typeof rawMetrics.score === 'number' ? Number(rawMetrics.score) : 0.0;
    return {
        score: fallbackScore,
        basePercentile: 50.0,
        alphaBonus: 0.0,
        meanBrier: 0.25,
        convictionNorm: 50.0,
        convictionMeanCp: 0.0,
        hasConviction: false,
        predictionsEvaluated: 0,
        basePercentilePoints: 50.0,
        alphaBonusPoints: 0.0,
        accuracyBlockPoints: 50.0,
        convictionContribution: 5.0,
    };
}

export function SectorScoreBreakdown({
    experiment,
    predictions = [],
    baselineScore,
}: SectorScoreBreakdownProps) {
    const [showGuide, setShowGuide] = useState(false);
    const metrics = extractSectorMetrics(experiment, predictions);

    const deltaVsBaseline =
        baselineScore !== null && baselineScore !== undefined
            ? metrics.score - baselineScore
            : null;

    return (
        <Card className="p-6 md:p-8 space-y-6 bg-slate-900/60 border-slate-800">
            {/* Header: Headline Score and Delta */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-boxel-bevel-hi pb-6">
                <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-3">
                        <SectionHeading>Sector Ratchet Score & Math Audit</SectionHeading>
                        <span className="font-mono text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded-none">
                            {experiment.variant_tag.toLowerCase().startsWith('v')
                                ? experiment.variant_tag
                                : `v${experiment.variant_tag}`}
                        </span>
                    </div>
                    <p className="text-xs font-normal text-boxel-muted">
                        Multi-pillar evaluation balancing relative percentile rank, S&P alpha
                        capture, and conviction-weighted confidence calibration.
                    </p>
                </div>

                <div className="flex items-center gap-4">
                    {deltaVsBaseline !== null && (
                        <div className="flex flex-col items-end">
                            <span className="text-sm uppercase font-bold text-boxel-muted">
                                vs Baseline
                            </span>
                            <span
                                className={`font-mono text-sm font-bold ${
                                    deltaVsBaseline >= 0 ? 'text-emerald-400' : 'text-rose-400'
                                }`}
                            >
                                {deltaVsBaseline >= 0 ? '+' : ''}
                                {deltaVsBaseline.toFixed(2)} pts
                            </span>
                        </div>
                    )}

                    <div className="flex flex-col items-end pl-4 border-l border-boxel-bevel-hi">
                        <span className="text-sm uppercase font-bold text-boxel-muted">
                            Ratchet Score
                        </span>
                        <span
                            className={`font-mono text-lg font-bold ${
                                metrics.score >= 0 ? 'text-emerald-400' : 'text-rose-400'
                            }`}
                        >
                            {metrics.score.toFixed(2)}
                        </span>
                    </div>
                </div>
            </div>

            {/* Formula Substitution Bar */}
            <div className="p-4 bg-boxel-trough rounded-none border border-boxel-bevel-hi font-mono text-xs font-normal flex flex-col gap-2 text-boxel-ink">
                <div className="text-sm uppercase font-sans font-bold text-boxel-muted tracking-wider">
                    Formula Substitution
                </div>
                <div className="flex flex-wrap items-center gap-2 text-sm font-bold leading-relaxed">
                    <span className="text-boxel-muted font-normal">Score = 0.90 ×</span>
                    <span className="text-emerald-400">
                        {metrics.basePercentile.toFixed(1)}%ile (Base)
                    </span>
                    <span className="text-boxel-muted font-normal">+</span>
                    <span className="text-teal-400">
                        {metrics.alphaBonus >= 0 ? '+' : ''}
                        {metrics.alphaBonus.toFixed(2)}% (Alpha)
                    </span>
                    <span className="text-boxel-muted font-normal">+ 0.10 ×</span>
                    <span className="text-accent">
                        {metrics.convictionNorm.toFixed(1)} (Conviction)
                    </span>
                    <span className="text-boxel-muted font-normal">=</span>
                    <span
                        className={`font-bold ${metrics.score >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}
                    >
                        {metrics.score.toFixed(2)} pts
                    </span>
                </div>
            </div>

            {/* 3 Metric Pillar Tiles */}
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,12rem),1fr))] gap-4 items-stretch">
                <MetricTile
                    icon="🎯"
                    label="Relative Percentile Rank"
                    value={
                        <span className="font-mono text-emerald-400">
                            {metrics.basePercentile.toFixed(1)}%
                        </span>
                    }
                    className="bg-slate-950/60 border-slate-800"
                />
                <MetricTile
                    icon="📈"
                    label="S&P Alpha Bonus"
                    value={
                        <span className="font-mono text-teal-400">
                            +{metrics.alphaBonus.toFixed(2)}%
                        </span>
                    }
                    className="bg-slate-950/60 border-slate-800"
                />
                <MetricTile
                    icon="⚖️"
                    label="Conviction Score"
                    value={
                        <span
                            className={`font-mono ${
                                metrics.convictionNorm >= 50 ? 'text-emerald-400' : 'text-rose-400'
                            }`}
                        >
                            {metrics.convictionNorm.toFixed(1)}
                        </span>
                    }
                    className="bg-slate-950/60 border-slate-800"
                />
                <MetricTile
                    icon="🛡️"
                    label="Brier (diagnostic)"
                    value={
                        <span className="font-mono text-boxel-muted">
                            {metrics.meanBrier.toFixed(4)}
                        </span>
                    }
                    className="bg-slate-950/60 border-slate-800"
                />
            </div>

            {/* Sample Warning if low N */}
            {metrics.predictionsEvaluated > 0 && metrics.predictionsEvaluated < 5 && (
                <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-none text-amber-300 text-xs font-normal shadow-sm flex items-center gap-2">
                    <span>⚠️</span>
                    <span>
                        Low sample window ({metrics.predictionsEvaluated} predictions evaluated).
                        Scores stabilize with $N \ge 5$.
                    </span>
                </div>
            )}

            {/* Collapsible Methodology Guide */}
            <div className="border-t border-slate-800/80 pt-4">
                <button
                    type="button"
                    onClick={() => setShowGuide(!showGuide)}
                    className="text-xs text-boxel-muted hover:text-boxel-ink font-bold flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                    <span>{showGuide ? '▼' : '▶'}</span>
                    <span>How Sector Ratchet Scoring Works</span>
                </button>

                {showGuide && (
                    <div className="mt-3 p-4 bg-boxel-canvas border border-boxel-bevel-hi rounded-none text-xs font-normal text-boxel-muted flex flex-col gap-2 leading-relaxed font-sans animate-fade-in">
                        <p>
                            <strong>1. Relative Percentile Score:</strong> Averages the percentile
                            performance of the predicted best sector, worst sector, and uncorrelated
                            pair relative to the 11 S&P sectors (0–100%).
                        </p>
                        <p>
                            <strong>2. S&P Alpha Bonus:</strong> Awards additive bonus points when
                            the picked best sector outperforms the benchmark SPY return over the
                            evaluation window (max(0, Sector - SPY)).
                        </p>
                        <p>
                            <strong>3. Conviction Score (10% weight):</strong> Scores stated
                            confidence against the outcome with the logarithmic rule, recentred so a
                            coin flip is worth zero. The best pick uses <code>confidence</code>, the
                            worst pick uses <code>worst_confidence</code>. A confident miss costs
                            more than a confident hit earns, and hedging buys nothing.
                        </p>
                        <p>
                            <strong>Brier (diagnostic only):</strong> Still stored per prediction
                            for calibration auditing ({metrics.meanBrier.toFixed(4)} here) but no
                            longer a scoring input.
                        </p>
                    </div>
                )}
            </div>
        </Card>
    );
}
