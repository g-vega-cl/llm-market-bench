import type { PromptExperiment } from '@llm-market-bench/database';
import { Card, MetricTile, SectionHeading } from '@llm-market-bench/ui-design-system';
import { useState } from 'react';
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
    predictionsEvaluated: number;
    basePercentilePoints: number;
    alphaBonusPoints: number;
    brierPenaltyPoints: number;
}

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

    const computedScore =
        typeof rawScore === 'number'
            ? Number(rawScore)
            : avgBasePercentile + avgAlphaBonus - meanBrier * 50.0;

    return {
        score: computedScore,
        basePercentile: avgBasePercentile,
        alphaBonus: avgAlphaBonus,
        meanBrier,
        predictionsEvaluated: evaluatedCount,
        basePercentilePoints: avgBasePercentile,
        alphaBonusPoints: avgAlphaBonus,
        brierPenaltyPoints: meanBrier * 50.0,
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
        typeof rawMetrics.alpha_bonus === 'number' &&
        typeof rawMetrics.mean_brier === 'number'
    ) {
        const score = Number(rawMetrics.score);
        const basePercentile = Number(rawMetrics.base_percentile);
        const alphaBonus = Number(rawMetrics.alpha_bonus);
        const meanBrier = Number(rawMetrics.mean_brier);
        const evaluated = Number(rawMetrics.predictions_evaluated || 0);

        return {
            score,
            basePercentile,
            alphaBonus,
            meanBrier,
            predictionsEvaluated: evaluated,
            basePercentilePoints: basePercentile,
            alphaBonusPoints: alphaBonus,
            brierPenaltyPoints: meanBrier * 50.0,
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
        predictionsEvaluated: 0,
        basePercentilePoints: 50.0,
        alphaBonusPoints: 0.0,
        brierPenaltyPoints: 12.5,
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
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
                <div className="space-y-1">
                    <div className="flex items-center gap-3">
                        <SectionHeading className="text-slate-100 font-black">
                            Sector Ratchet Score & Math Audit
                        </SectionHeading>
                        <span className="font-mono text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded">
                            {experiment.variant_tag.toLowerCase().startsWith('v')
                                ? experiment.variant_tag
                                : `v${experiment.variant_tag}`}
                        </span>
                    </div>
                    <p className="text-xs text-slate-400">
                        Multi-pillar evaluation balancing relative percentile rank, S&P alpha
                        capture, and Brier confidence calibration.
                    </p>
                </div>

                <div className="flex items-center gap-4">
                    {deltaVsBaseline !== null && (
                        <div className="flex flex-col items-end">
                            <span className="text-[10px] uppercase font-bold text-slate-500">
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

                    <div className="flex flex-col items-end pl-4 border-l border-slate-800">
                        <span className="text-[10px] uppercase font-bold text-slate-500">
                            Ratchet Score
                        </span>
                        <span
                            className={`font-mono text-3xl font-black ${
                                metrics.score >= 0 ? 'text-emerald-400' : 'text-rose-400'
                            }`}
                        >
                            {metrics.score.toFixed(2)}
                        </span>
                    </div>
                </div>
            </div>

            {/* Formula Substitution Bar */}
            <div className="p-4 bg-slate-950/80 rounded-xl border border-slate-800 font-mono text-xs space-y-2 text-slate-300">
                <div className="text-[10px] uppercase font-sans font-bold text-slate-500 tracking-wider">
                    Formula Substitution
                </div>
                <div className="flex flex-wrap items-center gap-2 text-sm leading-relaxed">
                    <span className="text-slate-400">Score =</span>
                    <span className="text-emerald-400">
                        {metrics.basePercentile.toFixed(1)}%ile (Base)
                    </span>
                    <span className="text-slate-500">+</span>
                    <span className="text-teal-400">
                        {metrics.alphaBonus >= 0 ? '+' : ''}
                        {metrics.alphaBonus.toFixed(2)}% (Alpha)
                    </span>
                    <span className="text-slate-500">-</span>
                    <span className="text-rose-400">
                        ({metrics.meanBrier.toFixed(3)} × 50.0) (Brier)
                    </span>
                    <span className="text-slate-400">=</span>
                    <span
                        className={`font-black ${metrics.score >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}
                    >
                        {metrics.score.toFixed(2)} pts
                    </span>
                </div>
            </div>

            {/* 3 Metric Pillar Tiles */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                    icon="🛡️"
                    label="Brier Calibration Penalty"
                    value={
                        <span className="font-mono text-rose-400">
                            -{metrics.brierPenaltyPoints.toFixed(2)} pts
                        </span>
                    }
                    className="bg-slate-950/60 border-slate-800"
                />
            </div>

            {/* Sample Warning if low N */}
            {metrics.predictionsEvaluated > 0 && metrics.predictionsEvaluated < 5 && (
                <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-300 text-xs flex items-center gap-2">
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
                    className="text-xs text-slate-400 hover:text-slate-200 font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                    <span>{showGuide ? '▼' : '▶'}</span>
                    <span>How Sector Ratchet Scoring Works</span>
                </button>

                {showGuide && (
                    <div className="mt-3 p-4 bg-slate-950/60 border border-slate-800 rounded-xl text-xs text-slate-400 space-y-2 leading-relaxed font-sans animate-fade-in">
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
                            <strong>3. Brier Calibration Penalty:</strong> Strictly penalizes
                            uncalibrated confidence. Overconfidence in wrong directional predictions
                            heavily docks the ratchet score (Mean Brier × 50.0).
                        </p>
                    </div>
                )}
            </div>
        </Card>
    );
}
