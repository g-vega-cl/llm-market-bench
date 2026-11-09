import type { PromptExperiment } from '@llm-market-bench/database';
import { Badge, Card } from '@llm-market-bench/ui-design-system';
import { useState } from 'react';
import { meanConvictionPoints, normalizeConvictionPoints } from '~/shared/conviction';
import type { DailyPrediction } from '../api/fetch-daily-predictions';

export interface DailyScoreBreakdownProps {
    experiment: PromptExperiment;
    predictions?: DailyPrediction[];
}

export interface DailyRatchetMetrics {
    score: number;
    closeAccuracyPct: number;
    intradayHitPct: number;
    magnitudeCapturePct: number;
    meanBrier: number;
    convictionNorm: number;
    convictionMeanCp: number;
    hasConviction: boolean;
    predictionsEvaluated: number;
    tradedCount: number;
    holdCount: number;
    participationFactor: number;
    correctCount: number;
    intradayHitCount: number;
    closeAccPoints: number;
    intradayHitPoints: number;
    magnitudeCapturePoints: number;
    accuracyBlockPoints: number;
    convictionContribution: number;
}

function getPeakReturn(
    predictedDir: string,
    openP: number,
    highP?: number | null,
    lowP?: number | null,
    closeReturn = 0,
): number {
    if (predictedDir === 'UP' && highP) {
        return Math.max(0.0, ((highP - openP) / openP) * 100.0);
    }
    if (predictedDir === 'DOWN' && lowP) {
        return Math.max(0.0, ((openP - lowP) / openP) * 100.0);
    }
    return closeReturn;
}

function isEligibleForCapture(p: DailyPrediction): boolean {
    const isCorrect = p.is_correct === true;
    return isCorrect && (p.intraday_hit === true || p.intraday_hit == null);
}

export function calculateMagnitudeCapture(p: DailyPrediction): number {
    if (!isEligibleForCapture(p)) return 0.0;

    const openP = p.open_price;
    if (!openP || openP <= 0) return 100.0;

    const expPct = Math.abs(Number(p.expected_return_pct) || 0.0);
    const closeP = p.close_price;
    const closeReturn = closeP ? Math.abs((closeP - openP) / openP) * 100.0 : 0.0;
    const predictedDir = (p.predicted_direction || 'UP').toUpperCase();
    const peakReturn = getPeakReturn(predictedDir, openP, p.high_price, p.low_price, closeReturn);

    const actualMove = Math.max(peakReturn, closeReturn);
    if (actualMove <= 0) return expPct === 0 ? 100.0 : 0.0;
    return Math.min(1.0, expPct / actualMove) * 100.0;
}

export function calculateHoldSessionCredit(p: DailyPrediction): number {
    const openP = p.open_price;
    const closeP = p.close_price;
    if (!openP || !closeP || openP <= 0) return 45.0;
    const actualMove = Math.abs((closeP - openP) / openP) * 100.0;
    if (actualMove < 0.25) return 52.0;
    if (actualMove > 0.75) return 35.0;
    return 45.0;
}

const ACCURACY_WEIGHT = 0.9;
const CONVICTION_WEIGHT = 0.1;

function buildMetrics(
    closeAccuracyPct: number,
    intradayHitPct: number,
    magnitudeCapturePct: number,
    meanBrier: number,
    predictionsEvaluated: number,
    correctCount: number,
    intradayHitCount: number,
    convictionNorm: number,
    convictionMeanCp: number,
    hasConviction: boolean,
    overrideScore?: number | null,
    tradedCount?: number,
    holdCount?: number,
    participationFactor?: number,
    accuracyBlockOverride?: number | null,
): DailyRatchetMetrics {
    const actualTraded = tradedCount ?? predictionsEvaluated;
    const actualHold = holdCount ?? 0;
    const actualPart = participationFactor ?? 1.0;
    const closeAccPoints = (closeAccuracyPct / 100.0) * 55.0;
    const intradayHitPoints = (intradayHitPct / 100.0) * 35.0;
    const magnitudeCapturePoints = (magnitudeCapturePct / 100.0) * 10.0;
    const accuracyBlockPoints =
        accuracyBlockOverride ?? closeAccPoints + intradayHitPoints + magnitudeCapturePoints;
    const convictionContribution = convictionNorm * CONVICTION_WEIGHT;
    const baseScore = accuracyBlockPoints * ACCURACY_WEIGHT + convictionContribution;
    const score = overrideScore ?? baseScore * actualPart;

    return {
        score,
        closeAccuracyPct,
        intradayHitPct,
        magnitudeCapturePct,
        meanBrier,
        convictionNorm,
        convictionMeanCp,
        hasConviction,
        predictionsEvaluated,
        tradedCount: actualTraded,
        holdCount: actualHold,
        participationFactor: actualPart,
        correctCount,
        intradayHitCount,
        closeAccPoints,
        intradayHitPoints,
        magnitudeCapturePoints,
        accuracyBlockPoints,
        convictionContribution,
    };
}

function isPredictionInExperiment(p: DailyPrediction, experiment: PromptExperiment): boolean {
    if (p.status !== 'evaluated') return false;
    if (p.prompt_variant_tag) {
        return p.prompt_variant_tag === experiment.variant_tag;
    }

    if (
        experiment.track_id &&
        experiment.track_id !== 'track_default' &&
        p.model_name &&
        !p.model_name.includes(experiment.track_id) &&
        !experiment.track_id.includes(p.model_name)
    ) {
        return false;
    }

    if (experiment.week_start && experiment.week_end) {
        const target = p.target_date || p.prediction_date;
        if (target && (target < experiment.week_start || target > experiment.week_end)) {
            return false;
        }
    }
    return true;
}

function computeMetricsFromSample(
    sample: DailyPrediction[],
    rawScore?: unknown,
): DailyRatchetMetrics {
    const holdSample = sample.filter((p) => (p.predicted_direction as string) === 'HOLD');
    const tradedSample = sample.filter((p) => (p.predicted_direction as string) !== 'HOLD');
    const correctCount = tradedSample.filter((p) => p.is_correct === true).length;
    const closeAccuracyPct =
        tradedSample.length > 0 ? (correctCount / tradedSample.length) * 100.0 : 50.0;

    const intradayHitCount = tradedSample.filter(
        (p) => p.intraday_hit === true || (p.intraday_hit == null && p.is_correct === true),
    ).length;
    const intradayHitPct =
        tradedSample.length > 0 ? (intradayHitCount / tradedSample.length) * 100.0 : 50.0;

    const captures = tradedSample.map(calculateMagnitudeCapture);
    const magnitudeCapturePct =
        captures.length > 0 ? captures.reduce((a, b) => a + b, 0) / captures.length : 0.0;

    const brierList = sample
        .map((p) => (typeof p.brier_score === 'number' ? p.brier_score : null))
        .filter((b): b is number => b !== null);
    const meanBrier =
        brierList.length > 0 ? brierList.reduce((a, b) => a + b, 0) / brierList.length : 0.25;

    // Fallback path for variants evaluated before the engine started persisting
    // conviction_norm on the experiment metrics. The mean log-score is aggregated
    // from the per-prediction values the engine already stored.
    const meanCp = meanConvictionPoints(sample);
    const convictionNorm = meanCp === null ? 50.0 : normalizeConvictionPoints(meanCp);

    const totalEvaluated = sample.length;
    const tradedCount = tradedSample.length;
    const holdCount = holdSample.length;

    let accuracyBlockOverride: number | null = null;
    if (holdCount > 0 && totalEvaluated > 0) {
        const tradedBlock =
            closeAccuracyPct * 0.55 + intradayHitPct * 0.35 + magnitudeCapturePct * 0.1;
        const holdCredits = holdSample.map(calculateHoldSessionCredit);
        const holdAvg = holdCredits.reduce((a, b) => a + b, 0) / holdCount;
        accuracyBlockOverride = (tradedCount * tradedBlock + holdCount * holdAvg) / totalEvaluated;
    }

    const tradeRate = totalEvaluated > 0 ? tradedCount / totalEvaluated : 1.0;
    const participationFactor = tradeRate < 0.75 ? Math.min(1.0, tradeRate / 0.75) : 1.0;

    return buildMetrics(
        closeAccuracyPct,
        intradayHitPct,
        magnitudeCapturePct,
        meanBrier,
        sample.length,
        correctCount,
        intradayHitCount,
        convictionNorm,
        meanCp ?? 0.0,
        meanCp !== null,
        typeof rawScore === 'number' ? Number(rawScore) : null,
        tradedCount,
        holdCount,
        participationFactor,
        accuracyBlockOverride,
    );
}

function extractEnrichedMetrics(rawMetrics?: Record<string, unknown>): DailyRatchetMetrics | null {
    if (
        !rawMetrics ||
        typeof rawMetrics.score !== 'number' ||
        typeof rawMetrics.close_accuracy_pct !== 'number' ||
        typeof rawMetrics.intraday_hit_pct !== 'number'
    ) {
        return null;
    }

    // Metrics written before conviction scoring existed fall back to neutral 50.
    const convictionNorm =
        typeof rawMetrics.conviction_norm === 'number' ? Number(rawMetrics.conviction_norm) : 50.0;
    const convictionMeanCp =
        typeof rawMetrics.conviction_mean_cp === 'number'
            ? Number(rawMetrics.conviction_mean_cp)
            : 0.0;
    const tradedCount =
        typeof rawMetrics.traded_count === 'number'
            ? Number(rawMetrics.traded_count)
            : Number(rawMetrics.predictions_evaluated || 0);
    const holdCount = typeof rawMetrics.hold_count === 'number' ? Number(rawMetrics.hold_count) : 0;
    const participationFactor =
        typeof rawMetrics.participation_factor === 'number'
            ? Number(rawMetrics.participation_factor)
            : 1.0;

    return buildMetrics(
        Number(rawMetrics.close_accuracy_pct),
        Number(rawMetrics.intraday_hit_pct),
        Number(rawMetrics.magnitude_capture_pct || 0),
        typeof rawMetrics.mean_brier === 'number' ? Number(rawMetrics.mean_brier) : 0.25,
        Number(rawMetrics.predictions_evaluated || 0),
        Number(rawMetrics.correct_count || 0),
        Number(rawMetrics.intraday_hit_count || 0),
        convictionNorm,
        convictionMeanCp,
        typeof rawMetrics.conviction_norm === 'number',
        Number(rawMetrics.score),
        tradedCount,
        holdCount,
        participationFactor,
    );
}

export function resolveRatchetMetrics(
    experiment: PromptExperiment,
    predictions?: DailyPrediction[],
): DailyRatchetMetrics | null {
    const rawMetrics = experiment.metrics as Record<string, unknown> | undefined;
    const enriched = extractEnrichedMetrics(rawMetrics);
    if (enriched) return enriched;

    if (predictions && predictions.length > 0) {
        const matching = predictions.filter((p) => isPredictionInExperiment(p, experiment));
        if (matching.length > 0) {
            return computeMetricsFromSample(matching, rawMetrics?.score);
        }
    }

    return null;
}

function ConvictionPillar({ metrics }: { metrics: DailyRatchetMetrics }) {
    const isAboveNeutral = metrics.convictionNorm >= 50;
    const toneClass = isAboveNeutral ? 'text-success' : 'text-danger';
    const detail = metrics.hasConviction
        ? `${metrics.convictionMeanCp >= 0 ? '+' : ''}${metrics.convictionMeanCp.toFixed(2)} mean CP · 50 = coin flip`
        : 'Neutral 50 (no scored confidence)';

    return (
        <div className="voxel-trough rounded-none p-3 flex flex-col justify-between gap-1 min-w-0">
            <div className="text-xs font-bold text-danger break-words">Conviction (10%)</div>
            <div className={`text-lg font-bold font-mono tabular-nums ${toneClass}`}>
                {metrics.convictionNorm.toFixed(1)}
            </div>
            <div className={`text-xs font-bold ${toneClass}`}>
                +{metrics.convictionContribution.toFixed(2)} pts
            </div>
            <div className="text-xs font-normal text-boxel-muted">{detail}</div>
        </div>
    );
}

function ActiveDailyExperimentPlaceholder({ variantTag }: { variantTag: string }) {
    return (
        <Card className="p-6 flex flex-col gap-3 rounded-none">
            <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-bold text-boxel-ink">
                    Live Variant Evaluation In Progress
                </span>
                <Badge colorScheme="success" variant="solid">
                    ACTIVE
                </Badge>
            </div>
            <p className="text-xs font-normal text-boxel-muted leading-relaxed">
                This mutated prompt variant (<code className="text-accent">{variantTag}</code>) is
                currently active and undergoing live daily evaluation. Score calculation and pillar
                breakdown will be computed automatically as trading sessions conclude and
                predictions are evaluated.
            </p>
        </Card>
    );
}

function FormulaSubstitutionBar({
    metrics,
    scoreColorClass,
}: {
    metrics: DailyRatchetMetrics;
    scoreColorClass: string;
}) {
    return (
        <div className="voxel-trough rounded-none p-3 text-xs font-mono text-boxel-ink leading-relaxed min-w-0 overflow-x-auto flex flex-col gap-1">
            <div className="text-xs font-bold text-boxel-muted uppercase tracking-wider">
                FORMULA SUBSTITUTION:
            </div>
            <div className="break-words overflow-wrap-anywhere">
                <span className="text-accent">(0.55 × {metrics.closeAccuracyPct.toFixed(1)}%)</span>
                {' + '}
                <span className="text-info">(0.35 × {metrics.intradayHitPct.toFixed(1)}%)</span>
                {' + '}
                <span className="text-boxel-ink">
                    (0.10 × {metrics.magnitudeCapturePct.toFixed(1)}%)
                </span>
                {' = '}
                <span className="text-boxel-ink">
                    {metrics.accuracyBlockPoints.toFixed(2)} accuracy
                </span>
                <br />
                {'0.90 × '}
                {metrics.accuracyBlockPoints.toFixed(2)}
                {' + 0.10 × '}
                <span className="text-accent">{metrics.convictionNorm.toFixed(1)}</span>
                {metrics.participationFactor < 1.0 ? (
                    <>
                        {' = '}
                        <span>
                            {(
                                metrics.accuracyBlockPoints * ACCURACY_WEIGHT +
                                metrics.convictionContribution
                            ).toFixed(2)}
                        </span>
                        {' × '}
                        <span className="text-amber-400">
                            {metrics.participationFactor.toFixed(2)} participation factor
                        </span>
                        {' = '}
                        <strong className={scoreColorClass}>{metrics.score.toFixed(2)}</strong>
                    </>
                ) : (
                    <>
                        {' = '}
                        <strong className={scoreColorClass}>
                            {(metrics.accuracyBlockPoints * ACCURACY_WEIGHT).toFixed(2)} +{' '}
                            {metrics.convictionContribution.toFixed(2)} = {metrics.score.toFixed(2)}
                        </strong>
                    </>
                )}
            </div>
        </div>
    );
}

function ScoringGuideCollapsible({
    showGuide,
    onToggle,
    meanBrier,
}: {
    showGuide: boolean;
    onToggle: () => void;
    meanBrier: number;
}) {
    return (
        <div className="border-t border-boxel-bevel-hi pt-3">
            <button
                type="button"
                onClick={onToggle}
                className="voxel-btn bg-boxel-surface text-boxel-ink hover:text-accent px-3 py-1 text-xs font-bold inline-flex items-center gap-1 cursor-pointer"
            >
                <span>{showGuide ? '▲ Hide' : '▼ View'} Scoring Formula & Weights Guide</span>
            </button>

            {showGuide && (
                <div className="voxel-trough rounded-none p-3 mt-3 flex flex-col gap-2 text-xs font-normal text-boxel-muted leading-relaxed">
                    <div className="text-xs font-bold text-boxel-ink uppercase tracking-wider">
                        How the Daily Ratchet Score is Computed:
                    </div>
                    <ul className="m-0 pl-4 flex flex-col gap-1">
                        <li>
                            <strong className="text-boxel-ink">
                                Close Directional Accuracy (55%):
                            </strong>{' '}
                            Evaluates whether the 4:00 PM ET close price matched the predicted
                            direction (`UP` if Close &ge; Open else `DOWN`).
                        </li>
                        <li>
                            <strong className="text-boxel-ink">
                                Intraday Target Hit Rate (35%):
                            </strong>{' '}
                            Evaluates whether SPY reached the expected return percentage
                            (`expected_return_pct`) at any point between Open and Close.
                        </li>
                        <li>
                            <strong className="text-boxel-ink">
                                Magnitude Capture Ratio (10%):
                            </strong>{' '}
                            Rewards predicting aggressive percentage targets on large breakout days
                            rather than overly timid targets on clear trends (min(1.0, |pred| /
                            actual) × 100).
                        </li>
                        <li>
                            <strong className="text-boxel-ink">Conviction (10%):</strong> Scores the
                            stated confidence against the outcome using the logarithmic rule,
                            recentred so a coin flip is worth zero: +100·ln(2p) when correct,
                            +100·ln(2−2p) when wrong.
                        </li>
                        <li>
                            <strong className="text-boxel-ink">HOLD Gating & Credits:</strong>{' '}
                            Confidence &lt; 56.0% automatically gates execution to `HOLD`. On choppy
                            sessions (|move| &lt; 0.25%), HOLD earns +52.0 pts credit. On normal
                            sessions (0.25% &ndash; 0.75%), HOLD earns +45.0 pts credit. On missed
                            trends (|move| &gt; 0.75%), HOLD earns +35.0 pts credit.
                        </li>
                        <li>
                            <strong className="text-boxel-ink">Participation Hurdle:</strong> Models
                            must maintain a &ge;75% trade rate (at most 1 HOLD per 4&ndash;5
                            sessions). If trade rate drops below 75%, the final score is scaled by
                            (trade_rate / 0.75).
                        </li>
                        <li>
                            <strong className="text-boxel-ink">Brier (diagnostic only):</strong>{' '}
                            Still stored per prediction ({meanBrier.toFixed(4)} here) for
                            calibration auditing.
                        </li>
                    </ul>
                </div>
            )}
        </div>
    );
}

export function DailyScoreBreakdown({ experiment, predictions }: DailyScoreBreakdownProps) {
    const [showGuide, setShowGuide] = useState(false);
    const metrics = resolveRatchetMetrics(experiment, predictions);

    if (!metrics) {
        if (experiment.status === 'active') {
            return <ActiveDailyExperimentPlaceholder variantTag={experiment.variant_tag} />;
        }
        return (
            <div className="voxel-trough rounded-none p-4 text-xs font-normal text-boxel-muted">
                <strong className="text-boxel-ink">Score Breakdown:</strong> No evaluated metrics
                available for this variant yet.
            </div>
        );
    }

    const isScorePositive = metrics.score > 0;
    const scoreColorClass = isScorePositive ? 'text-success' : 'text-danger';
    const isLowSample = metrics.predictionsEvaluated > 0 && metrics.predictionsEvaluated < 5;

    return (
        <Card className="p-5 flex flex-col gap-4 rounded-none min-w-0">
            {/* Header */}
            <div className="flex justify-between items-center flex-wrap gap-3 pb-3 border-b border-boxel-bevel-hi min-w-0">
                <div className="min-w-0 flex flex-col gap-0.5">
                    <div className="text-sm font-bold text-boxel-ink flex items-center gap-2 flex-wrap">
                        <span className="w-2 h-2 bg-accent shrink-0 inline-block" />
                        <span>Daily Ratchet Score Calculation & Breakdown</span>
                    </div>
                    <div className="text-xs font-normal text-boxel-muted break-words">
                        Evaluated across {metrics.predictionsEvaluated} prediction
                        {metrics.predictionsEvaluated === 1 ? '' : 's'}
                        {metrics.holdCount > 0
                            ? ` (${metrics.tradedCount} traded, ${metrics.holdCount} HOLD)`
                            : ''}
                        {experiment.week_start
                            ? ` (${experiment.week_start}${
                                  experiment.week_end ? ` → ${experiment.week_end}` : ''
                              })`
                            : ''}
                    </div>
                </div>

                <div className="text-right shrink-0 flex flex-col items-end">
                    <div className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                        Final Score
                    </div>
                    <div className={`text-lg font-bold font-mono tabular-nums ${scoreColorClass}`}>
                        {metrics.score.toFixed(2)}
                    </div>
                </div>
            </div>

            {/* Arithmetic Formula Bar */}
            <FormulaSubstitutionBar metrics={metrics} scoreColorClass={scoreColorClass} />

            {/* 4 Factor Pillar Cards */}
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,10rem),1fr))] gap-3 items-stretch min-w-0">
                {/* Close Accuracy */}
                <div className="voxel-trough rounded-none p-3 flex flex-col justify-between gap-1 min-w-0">
                    <div className="text-xs font-bold text-success break-words">
                        EOD Directional Acc (55%)
                    </div>
                    <div className="text-lg font-bold font-mono text-success tabular-nums">
                        {metrics.closeAccuracyPct.toFixed(1)}%
                    </div>
                    <div className="text-xs font-bold text-success">
                        +{metrics.closeAccPoints.toFixed(2)} pts
                    </div>
                    <div className="text-xs font-normal text-boxel-muted">
                        {metrics.holdCount > 0
                            ? `${metrics.correctCount} / ${metrics.tradedCount} correct (${metrics.holdCount} HOLD)`
                            : `${metrics.correctCount} / ${metrics.predictionsEvaluated} correct`}
                    </div>
                </div>

                {/* Intraday Hit */}
                <div className="voxel-trough rounded-none p-3 flex flex-col justify-between gap-1 min-w-0">
                    <div className="text-xs font-bold text-info break-words">
                        Intraday Target Hit (35%)
                    </div>
                    <div className="text-lg font-bold font-mono text-info tabular-nums">
                        {metrics.intradayHitPct.toFixed(1)}%
                    </div>
                    <div className="text-xs font-bold text-info">
                        +{metrics.intradayHitPoints.toFixed(2)} pts
                    </div>
                    <div className="text-xs font-normal text-boxel-muted">
                        {metrics.holdCount > 0
                            ? `${metrics.intradayHitCount} / ${metrics.tradedCount} targets hit`
                            : `${metrics.intradayHitCount} / ${metrics.predictionsEvaluated} targets hit`}
                    </div>
                </div>

                {/* Magnitude Capture */}
                <div className="voxel-trough rounded-none p-3 flex flex-col justify-between gap-1 min-w-0">
                    <div className="text-xs font-bold text-accent break-words">
                        Magnitude Capture (10%)
                    </div>
                    <div className="text-lg font-bold font-mono text-accent tabular-nums">
                        {metrics.magnitudeCapturePct.toFixed(1)}%
                    </div>
                    <div className="text-xs font-bold text-accent">
                        +{metrics.magnitudeCapturePoints.toFixed(2)} pts
                    </div>
                    <div className="text-xs font-normal text-boxel-muted">
                        Breakout capture ratio
                    </div>
                </div>

                {/* Conviction */}
                <ConvictionPillar metrics={metrics} />
            </div>

            {/* Participation Factor Hurdle Penalty Notice */}
            {metrics.participationFactor < 1.0 && (
                <div className="voxel-trough rounded-none p-3 text-xs font-normal text-amber-400 flex items-start gap-2 border-l-2 border-l-amber-400">
                    <span className="w-2 h-2 bg-amber-400 mt-1 shrink-0 inline-block" />
                    <div>
                        <strong className="text-boxel-ink">Participation Hurdle Penalty:</strong>{' '}
                        Track traded only {metrics.tradedCount} of {metrics.predictionsEvaluated}{' '}
                        sessions (
                        {((metrics.tradedCount / metrics.predictionsEvaluated) * 100).toFixed(0)}%,
                        target &ge;75%). Score scaled by {metrics.participationFactor.toFixed(2)}x.
                    </div>
                </div>
            )}

            {/* Low Sample Size Notice */}
            {isLowSample && (
                <div className="voxel-trough rounded-none p-3 text-xs font-normal text-accent flex items-start gap-2 border-l-2 border-l-accent">
                    <span className="w-2 h-2 bg-accent mt-1 shrink-0 inline-block" />
                    <div>
                        <strong className="text-boxel-ink">
                            Low Sample Window Notice (N = {metrics.predictionsEvaluated}):
                        </strong>{' '}
                        Weekly autoresearch evaluates 7-day windows (all available trading sessions
                        in the week). A single high-confidence miss costs far more conviction points
                        than the equivalent correct call earns, so short windows swing more than
                        multi-week backtest baselines.
                    </div>
                </div>
            )}

            {/* Collapsible Guide Toggle */}
            <ScoringGuideCollapsible
                showGuide={showGuide}
                onToggle={() => setShowGuide((prev) => !prev)}
                meanBrier={metrics.meanBrier}
            />
        </Card>
    );
}
