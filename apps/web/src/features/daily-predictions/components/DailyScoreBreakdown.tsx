import type { PromptExperiment } from '@llm-market-bench/database';
import { Badge, Card } from '@llm-market-bench/ui-design-system';
import { useState } from 'react';
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
    predictionsEvaluated: number;
    correctCount: number;
    intradayHitCount: number;
    closeAccPoints: number;
    intradayHitPoints: number;
    magnitudeCapturePoints: number;
    brierPenaltyPoints: number;
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

function buildMetrics(
    closeAccuracyPct: number,
    intradayHitPct: number,
    magnitudeCapturePct: number,
    meanBrier: number,
    predictionsEvaluated: number,
    correctCount: number,
    intradayHitCount: number,
    overrideScore?: number | null,
): DailyRatchetMetrics {
    const closeAccPoints = (closeAccuracyPct / 100.0) * 55.0;
    const intradayHitPoints = (intradayHitPct / 100.0) * 35.0;
    const magnitudeCapturePoints = (magnitudeCapturePct / 100.0) * 10.0;
    const brierPenaltyPoints = meanBrier * 50.0;
    const score =
        overrideScore ??
        closeAccPoints + intradayHitPoints + magnitudeCapturePoints - brierPenaltyPoints;

    return {
        score,
        closeAccuracyPct,
        intradayHitPct,
        magnitudeCapturePct,
        meanBrier,
        predictionsEvaluated,
        correctCount,
        intradayHitCount,
        closeAccPoints,
        intradayHitPoints,
        magnitudeCapturePoints,
        brierPenaltyPoints,
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
    const correctCount = sample.filter((p) => p.is_correct === true).length;
    const closeAccuracyPct = (correctCount / sample.length) * 100.0;

    const intradayHitCount = sample.filter(
        (p) => p.intraday_hit === true || (p.intraday_hit == null && p.is_correct === true),
    ).length;
    const intradayHitPct = (intradayHitCount / sample.length) * 100.0;

    const captures = sample.map(calculateMagnitudeCapture);
    const magnitudeCapturePct = captures.reduce((a, b) => a + b, 0) / captures.length;

    const brierList = sample
        .map((p) => (typeof p.brier_score === 'number' ? p.brier_score : null))
        .filter((b): b is number => b !== null);
    const meanBrier =
        brierList.length > 0 ? brierList.reduce((a, b) => a + b, 0) / brierList.length : 0.25;

    return buildMetrics(
        closeAccuracyPct,
        intradayHitPct,
        magnitudeCapturePct,
        meanBrier,
        sample.length,
        correctCount,
        intradayHitCount,
        typeof rawScore === 'number' ? Number(rawScore) : null,
    );
}

function extractEnrichedMetrics(rawMetrics?: Record<string, unknown>): DailyRatchetMetrics | null {
    if (
        !rawMetrics ||
        typeof rawMetrics.score !== 'number' ||
        typeof rawMetrics.close_accuracy_pct !== 'number' ||
        typeof rawMetrics.intraday_hit_pct !== 'number' ||
        typeof rawMetrics.mean_brier !== 'number'
    ) {
        return null;
    }

    return buildMetrics(
        Number(rawMetrics.close_accuracy_pct),
        Number(rawMetrics.intraday_hit_pct),
        Number(rawMetrics.magnitude_capture_pct || 0),
        Number(rawMetrics.mean_brier),
        Number(rawMetrics.predictions_evaluated || 0),
        Number(rawMetrics.correct_count || 0),
        Number(rawMetrics.intraday_hit_count || 0),
        Number(rawMetrics.score),
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
            <div className="voxel-trough rounded-none p-3 text-xs font-mono text-boxel-ink leading-relaxed min-w-0 overflow-x-auto flex flex-col gap-1">
                <div className="text-xs font-bold text-boxel-muted uppercase tracking-wider">
                    FORMULA SUBSTITUTION:
                </div>
                <div className="break-words overflow-wrap-anywhere">
                    <span className="text-accent">
                        (0.55 × {metrics.closeAccuracyPct.toFixed(1)}%)
                    </span>
                    {' + '}
                    <span className="text-info">(0.35 × {metrics.intradayHitPct.toFixed(1)}%)</span>
                    {' + '}
                    <span className="text-boxel-ink">
                        (0.10 × {metrics.magnitudeCapturePct.toFixed(1)}%)
                    </span>
                    {' − '}
                    <span className="text-danger">({metrics.meanBrier.toFixed(3)} × 50.0)</span>
                    {' = '}
                    <strong className={scoreColorClass}>
                        {metrics.closeAccPoints.toFixed(2)} + {metrics.intradayHitPoints.toFixed(2)}{' '}
                        + {metrics.magnitudeCapturePoints.toFixed(2)} −{' '}
                        {metrics.brierPenaltyPoints.toFixed(2)} = {metrics.score.toFixed(2)}
                    </strong>
                </div>
            </div>

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
                        {metrics.correctCount} / {metrics.predictionsEvaluated} correct
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
                        {metrics.intradayHitCount} / {metrics.predictionsEvaluated} targets hit
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

                {/* Brier Penalty */}
                <div className="voxel-trough rounded-none p-3 flex flex-col justify-between gap-1 min-w-0">
                    <div className="text-xs font-bold text-danger break-words">
                        Brier Penalty (50.0×)
                    </div>
                    <div className="text-lg font-bold font-mono text-danger tabular-nums">
                        {metrics.meanBrier.toFixed(4)}
                    </div>
                    <div className="text-xs font-bold text-danger">
                        −{metrics.brierPenaltyPoints.toFixed(2)} pts
                    </div>
                    <div className="text-xs font-normal text-boxel-muted">
                        Confidence calibration error
                    </div>
                </div>
            </div>

            {/* Low Sample Size Notice */}
            {isLowSample && (
                <div className="voxel-trough rounded-none p-3 text-xs font-normal text-accent flex items-start gap-2 border-l-2 border-l-accent">
                    <span className="w-2 h-2 bg-accent mt-1 shrink-0 inline-block" />
                    <div>
                        <strong className="text-boxel-ink">
                            Low Sample Window Notice (N = {metrics.predictionsEvaluated}):
                        </strong>{' '}
                        Weekly autoresearch evaluates 7-day windows (all available trading sessions
                        in the week). A single high-confidence miss heavily penalizes accuracy and
                        deducts up to 32 Brier penalty points, creating short-term score
                        fluctuations compared to multi-week backtest baselines.
                    </div>
                </div>
            )}

            {/* Collapsible Guide Toggle */}
            <div className="border-t border-boxel-bevel-hi pt-3">
                <button
                    type="button"
                    onClick={() => setShowGuide((prev) => !prev)}
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
                                Rewards predicting aggressive percentage targets on large breakout
                                days rather than overly timid targets on clear trends (min(1.0,
                                |pred| / actual) × 100).
                            </li>
                            <li>
                                <strong className="text-boxel-ink">
                                    Brier Calibration Penalty (50.0×):
                                </strong>{' '}
                                Penalizes overconfident wrong calls (Brier = (p - y)²). A
                                high-confidence (80%) incorrect forecast produces a single-day Brier
                                penalty of -32.0 points.
                            </li>
                        </ul>
                    </div>
                )}
            </div>
        </Card>
    );
}
