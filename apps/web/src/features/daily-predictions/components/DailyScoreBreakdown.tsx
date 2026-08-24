import type { PromptExperiment } from '@llm-market-bench/database';
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

    const finalScore =
        typeof rawScore === 'number'
            ? Number(rawScore)
            : 0.55 * closeAccuracyPct +
              0.35 * intradayHitPct +
              0.1 * magnitudeCapturePct -
              meanBrier * 50.0;

    return {
        score: finalScore,
        closeAccuracyPct,
        intradayHitPct,
        magnitudeCapturePct,
        meanBrier,
        predictionsEvaluated: sample.length,
        correctCount,
        intradayHitCount,
        closeAccPoints: 0.55 * closeAccuracyPct,
        intradayHitPoints: 0.35 * intradayHitPct,
        magnitudeCapturePoints: 0.1 * magnitudeCapturePct,
        brierPenaltyPoints: meanBrier * 50.0,
    };
}

function isPredictionInExperiment(p: DailyPrediction, experiment: PromptExperiment): boolean {
    if (p.status !== 'evaluated') return false;
    if (p.prompt_variant_tag && p.prompt_variant_tag === experiment.variant_tag) return true;

    if (
        experiment.track_id &&
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

    const score = Number(rawMetrics.score);
    const closeAccuracyPct = Number(rawMetrics.close_accuracy_pct);
    const intradayHitPct = Number(rawMetrics.intraday_hit_pct);
    const magnitudeCapturePct = Number(rawMetrics.magnitude_capture_pct || 0);
    const meanBrier = Number(rawMetrics.mean_brier);

    return {
        score,
        closeAccuracyPct,
        intradayHitPct,
        magnitudeCapturePct,
        meanBrier,
        predictionsEvaluated: Number(rawMetrics.predictions_evaluated || 0),
        correctCount: Number(rawMetrics.correct_count || 0),
        intradayHitCount: Number(rawMetrics.intraday_hit_count || 0),
        closeAccPoints: 0.55 * closeAccuracyPct,
        intradayHitPoints: 0.35 * intradayHitPct,
        magnitudeCapturePoints: 0.1 * magnitudeCapturePct,
        brierPenaltyPoints: meanBrier * 50.0,
    };
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
        const sample =
            matching.length > 0
                ? matching
                : predictions.filter((p) => p.status === 'evaluated').slice(0, 5);

        if (sample.length > 0) {
            return computeMetricsFromSample(sample, rawMetrics?.score);
        }
    }

    if (rawMetrics && typeof rawMetrics.score === 'number') {
        const score = Number(rawMetrics.score);
        const evalCount =
            typeof rawMetrics.predictions_evaluated === 'number'
                ? rawMetrics.predictions_evaluated
                : 0;
        return {
            score,
            closeAccuracyPct: 0,
            intradayHitPct: 0,
            magnitudeCapturePct: 0,
            meanBrier: 0,
            predictionsEvaluated: evalCount,
            correctCount: 0,
            intradayHitCount: 0,
            closeAccPoints: 0,
            intradayHitPoints: 0,
            magnitudeCapturePoints: 0,
            brierPenaltyPoints: 0,
        };
    }

    return null;
}

export function DailyScoreBreakdown({ experiment, predictions }: DailyScoreBreakdownProps) {
    const [showGuide, setShowGuide] = useState(false);
    const metrics = resolveRatchetMetrics(experiment, predictions);

    if (!metrics) {
        return (
            <div
                style={{
                    background: '#f8fafc',
                    borderRadius: '8px',
                    border: '1px solid #e2e8f0',
                    padding: '16px',
                    fontSize: '13px',
                    color: '#64748b',
                }}
            >
                <strong>Score Breakdown:</strong> No evaluated metrics available for this variant
                yet.
            </div>
        );
    }

    const isScorePositive = metrics.score > 0;
    const scoreColor = isScorePositive ? '#16a34a' : '#dc2626';
    const isLowSample = metrics.predictionsEvaluated > 0 && metrics.predictionsEvaluated < 5;

    return (
        <div
            style={{
                background: '#ffffff',
                borderRadius: '10px',
                border: '1px solid #e2e8f0',
                padding: '18px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
            }}
        >
            {/* Header */}
            <div
                style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '12px',
                    marginBottom: '14px',
                    borderBottom: '1px solid #f1f5f9',
                    paddingBottom: '12px',
                }}
            >
                <div>
                    <div
                        style={{
                            fontSize: '14px',
                            fontWeight: '700',
                            color: '#0f172a',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                        }}
                    >
                        <span>🧮</span>
                        <span>Daily Ratchet Score Calculation & Breakdown</span>
                    </div>
                    <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>
                        Evaluated across {metrics.predictionsEvaluated} prediction
                        {metrics.predictionsEvaluated === 1 ? '' : 's'}
                        {experiment.week_start
                            ? ` (${experiment.week_start}${
                                  experiment.week_end ? ` → ${experiment.week_end}` : ''
                              })`
                            : ''}
                    </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                    <div
                        style={{
                            fontSize: '11px',
                            color: '#64748b',
                            fontWeight: '600',
                            textTransform: 'uppercase',
                        }}
                    >
                        Final Score
                    </div>
                    <div
                        style={{
                            fontSize: '22px',
                            fontWeight: '800',
                            color: scoreColor,
                            fontFamily: 'monospace',
                        }}
                    >
                        {metrics.score.toFixed(2)}
                    </div>
                </div>
            </div>

            {/* Arithmetic Formula Bar */}
            <div
                style={{
                    background: '#f8fafc',
                    borderRadius: '8px',
                    border: '1px solid #e2e8f0',
                    padding: '12px 14px',
                    marginBottom: '16px',
                    fontSize: '12px',
                    fontFamily: 'monospace',
                    color: '#334155',
                    lineHeight: '1.6',
                }}
            >
                <div
                    style={{
                        fontWeight: '700',
                        color: '#475569',
                        marginBottom: '4px',
                        fontSize: '11px',
                    }}
                >
                    FORMULA SUBSTITUTION:
                </div>
                <div style={{ wordBreak: 'break-all' }}>
                    <span style={{ color: '#2563eb' }}>
                        (0.55 × {metrics.closeAccuracyPct.toFixed(1)}%)
                    </span>
                    {' + '}
                    <span style={{ color: '#0d9488' }}>
                        (0.35 × {metrics.intradayHitPct.toFixed(1)}%)
                    </span>
                    {' + '}
                    <span style={{ color: '#7c3aed' }}>
                        (0.10 × {metrics.magnitudeCapturePct.toFixed(1)}%)
                    </span>
                    {' − '}
                    <span style={{ color: '#dc2626' }}>
                        ({metrics.meanBrier.toFixed(3)} × 50.0)
                    </span>
                    {' = '}
                    <strong style={{ color: scoreColor }}>
                        {metrics.closeAccPoints.toFixed(2)} + {metrics.intradayHitPoints.toFixed(2)}{' '}
                        + {metrics.magnitudeCapturePoints.toFixed(2)} −{' '}
                        {metrics.brierPenaltyPoints.toFixed(2)} = {metrics.score.toFixed(2)}
                    </strong>
                </div>
            </div>

            {/* 4 Factor Pillar Cards */}
            <div
                style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                    gap: '12px',
                    marginBottom: '14px',
                }}
            >
                {/* Close Accuracy */}
                <div
                    style={{
                        padding: '12px',
                        background: '#f0fdf4',
                        borderRadius: '8px',
                        border: '1px solid #bbf7d0',
                    }}
                >
                    <div style={{ fontSize: '11px', color: '#166534', fontWeight: '700' }}>
                        EOD Directional Acc (55%)
                    </div>
                    <div
                        style={{
                            fontSize: '18px',
                            fontWeight: '800',
                            color: '#15803d',
                            marginTop: '4px',
                        }}
                    >
                        {metrics.closeAccuracyPct.toFixed(1)}%
                    </div>
                    <div
                        style={{
                            fontSize: '11px',
                            color: '#16a34a',
                            fontWeight: '600',
                            marginTop: '2px',
                        }}
                    >
                        +{metrics.closeAccPoints.toFixed(2)} pts
                    </div>
                    <div style={{ fontSize: '10px', color: '#4b5563', marginTop: '2px' }}>
                        {metrics.correctCount} / {metrics.predictionsEvaluated} correct
                    </div>
                </div>

                {/* Intraday Hit */}
                <div
                    style={{
                        padding: '12px',
                        background: '#f0fdfa',
                        borderRadius: '8px',
                        border: '1px solid #99f6e4',
                    }}
                >
                    <div style={{ fontSize: '11px', color: '#115e59', fontWeight: '700' }}>
                        Intraday Target Hit (35%)
                    </div>
                    <div
                        style={{
                            fontSize: '18px',
                            fontWeight: '800',
                            color: '#0f766e',
                            marginTop: '4px',
                        }}
                    >
                        {metrics.intradayHitPct.toFixed(1)}%
                    </div>
                    <div
                        style={{
                            fontSize: '11px',
                            color: '#0d9488',
                            fontWeight: '600',
                            marginTop: '2px',
                        }}
                    >
                        +{metrics.intradayHitPoints.toFixed(2)} pts
                    </div>
                    <div style={{ fontSize: '10px', color: '#4b5563', marginTop: '2px' }}>
                        {metrics.intradayHitCount} / {metrics.predictionsEvaluated} targets hit
                    </div>
                </div>

                {/* Magnitude Capture */}
                <div
                    style={{
                        padding: '12px',
                        background: '#faf5ff',
                        borderRadius: '8px',
                        border: '1px solid #e9d5ff',
                    }}
                >
                    <div style={{ fontSize: '11px', color: '#6b21a8', fontWeight: '700' }}>
                        Magnitude Capture (10%)
                    </div>
                    <div
                        style={{
                            fontSize: '18px',
                            fontWeight: '800',
                            color: '#7e22ce',
                            marginTop: '4px',
                        }}
                    >
                        {metrics.magnitudeCapturePct.toFixed(1)}%
                    </div>
                    <div
                        style={{
                            fontSize: '11px',
                            color: '#9333ea',
                            fontWeight: '600',
                            marginTop: '2px',
                        }}
                    >
                        +{metrics.magnitudeCapturePoints.toFixed(2)} pts
                    </div>
                    <div style={{ fontSize: '10px', color: '#4b5563', marginTop: '2px' }}>
                        Breakout capture ratio
                    </div>
                </div>

                {/* Brier Penalty */}
                <div
                    style={{
                        padding: '12px',
                        background: '#fef2f2',
                        borderRadius: '8px',
                        border: '1px solid #fecaca',
                    }}
                >
                    <div style={{ fontSize: '11px', color: '#991b1b', fontWeight: '700' }}>
                        Brier Penalty (50.0×)
                    </div>
                    <div
                        style={{
                            fontSize: '18px',
                            fontWeight: '800',
                            color: '#b91c1c',
                            marginTop: '4px',
                        }}
                    >
                        {metrics.meanBrier.toFixed(4)}
                    </div>
                    <div
                        style={{
                            fontSize: '11px',
                            color: '#dc2626',
                            fontWeight: '600',
                            marginTop: '2px',
                        }}
                    >
                        −{metrics.brierPenaltyPoints.toFixed(2)} pts
                    </div>
                    <div style={{ fontSize: '10px', color: '#4b5563', marginTop: '2px' }}>
                        Confidence calibration error
                    </div>
                </div>
            </div>

            {/* Low Sample Size Notice */}
            {isLowSample && (
                <div
                    style={{
                        background: '#fffbeb',
                        border: '1px solid #fde68a',
                        borderRadius: '8px',
                        padding: '10px 14px',
                        fontSize: '12px',
                        color: '#92400e',
                        marginBottom: '12px',
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '8px',
                    }}
                >
                    <span style={{ fontSize: '14px' }}>⚠️</span>
                    <div>
                        <strong>
                            Low Sample Window Notice (N = {metrics.predictionsEvaluated}):
                        </strong>{' '}
                        Twice-weekly autoresearch evaluates recent 3-4 day windows (2-3 trading
                        sessions). A single high-confidence miss heavily penalizes accuracy and
                        deducts up to 32 Brier penalty points, creating sharp short-term score
                        fluctuations compared to multi-week backtest baselines.
                    </div>
                </div>
            )}

            {/* Collapsible Guide Toggle */}
            <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '10px' }}>
                <button
                    type="button"
                    onClick={() => setShowGuide((prev) => !prev)}
                    style={{
                        background: 'transparent',
                        border: 'none',
                        color: '#2563eb',
                        fontSize: '12px',
                        fontWeight: '600',
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        padding: 0,
                    }}
                >
                    <span>{showGuide ? '▲ Hide' : '▼ View'} Scoring Formula & Weights Guide</span>
                </button>

                {showGuide && (
                    <div
                        style={{
                            marginTop: '10px',
                            padding: '12px',
                            background: '#f8fafc',
                            borderRadius: '8px',
                            fontSize: '12px',
                            color: '#475569',
                            lineHeight: '1.6',
                        }}
                    >
                        <p style={{ margin: '0 0 8px 0', fontWeight: '600', color: '#0f172a' }}>
                            How the Daily Ratchet Score is Computed:
                        </p>
                        <ul style={{ margin: 0, paddingLeft: '18px' }}>
                            <li>
                                <strong>Close Directional Accuracy (55%):</strong> Evaluates whether
                                the 4:00 PM ET close price matched the predicted direction (`UP` if
                                Close &ge; Open else `DOWN`).
                            </li>
                            <li>
                                <strong>Intraday Target Hit Rate (35%):</strong> Evaluates whether
                                SPY reached the expected return percentage (`expected_return_pct`)
                                at any point between Open and Close.
                            </li>
                            <li>
                                <strong>Magnitude Capture Ratio (10%):</strong> Rewards predicting
                                aggressive percentage targets on large breakout days rather than
                                overly timid targets on clear trends (min(1.0, |pred| / actual) ×
                                100).
                            </li>
                            <li>
                                <strong>Brier Calibration Penalty (50.0×):</strong> Penalizes
                                overconfident wrong calls (Brier = (p - y)²). A high-confidence
                                (80%) incorrect forecast produces a single-day Brier penalty of
                                -32.0 points.
                            </li>
                        </ul>
                    </div>
                )}
            </div>
        </div>
    );
}
