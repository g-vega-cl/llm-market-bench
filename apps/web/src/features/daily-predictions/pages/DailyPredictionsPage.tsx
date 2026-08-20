import type { PromptExperiment } from '@llm-market-bench/database';
import { Link } from '@tanstack/react-router';
import { useState } from 'react';
import type { DailyPrediction } from '../api/fetch-daily-predictions';

interface Props {
    initialPredictions: DailyPrediction[];
    experiments: PromptExperiment[];
    refreshFn?: () => Promise<{ predictions: DailyPrediction[]; experiments: PromptExperiment[] }>;
}

interface DailyMetricsOverviewProps {
    accuracyPct: string;
    intradayHitPct: string;
    correctCount: number;
    totalEvaluated: number;
    avgBrier: string;
    totalPredictions: number;
    activePromptTag: string;
}

function DailyMetricsOverview({
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
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '16px',
                marginBottom: '24px',
            }}
        >
            <div
                style={{
                    padding: '20px',
                    background: '#f8fafc',
                    borderRadius: '12px',
                    border: '1px solid #e2e8f0',
                }}
            >
                <div style={{ fontSize: '13px', color: '#64748b', fontWeight: '600' }}>
                    Directional Accuracy
                </div>
                <div
                    style={{
                        fontSize: '28px',
                        fontWeight: '700',
                        color: '#0f172a',
                        marginTop: '4px',
                    }}
                >
                    {accuracyPct}%
                </div>
                <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>
                    {correctCount} / {totalEvaluated} correct
                </div>
            </div>

            <div
                style={{
                    padding: '20px',
                    background: '#f8fafc',
                    borderRadius: '12px',
                    border: '1px solid #e2e8f0',
                }}
            >
                <div style={{ fontSize: '13px', color: '#64748b', fontWeight: '600' }}>
                    Intraday Target Hit (30%)
                </div>
                <div
                    style={{
                        fontSize: '28px',
                        fontWeight: '700',
                        color: '#0f172a',
                        marginTop: '4px',
                    }}
                >
                    {intradayHitPct}%
                </div>
                <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>
                    Target reached intraday
                </div>
            </div>

            <div
                style={{
                    padding: '20px',
                    background: '#f8fafc',
                    borderRadius: '12px',
                    border: '1px solid #e2e8f0',
                }}
            >
                <div style={{ fontSize: '13px', color: '#64748b', fontWeight: '600' }}>
                    Brier Calibration Score
                </div>
                <div
                    style={{
                        fontSize: '28px',
                        fontWeight: '700',
                        color: '#0f172a',
                        marginTop: '4px',
                    }}
                >
                    {avgBrier}
                </div>
                <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>
                    Lower is better (0.0000 = perfect)
                </div>
            </div>

            <div
                style={{
                    padding: '20px',
                    background: '#f8fafc',
                    borderRadius: '12px',
                    border: '1px solid #e2e8f0',
                }}
            >
                <div style={{ fontSize: '13px', color: '#64748b', fontWeight: '600' }}>
                    Total Predictions
                </div>
                <div
                    style={{
                        fontSize: '28px',
                        fontWeight: '700',
                        color: '#0f172a',
                        marginTop: '4px',
                    }}
                >
                    {totalPredictions}
                </div>
                <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>
                    Logged predictions count
                </div>
            </div>

            <div
                style={{
                    padding: '20px',
                    background: '#f8fafc',
                    borderRadius: '12px',
                    border: '1px solid #e2e8f0',
                }}
            >
                <div
                    style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                    }}
                >
                    <span style={{ fontSize: '13px', color: '#64748b', fontWeight: '600' }}>
                        Active Prompt Variant
                    </span>
                    <span
                        style={{
                            fontSize: '11px',
                            fontWeight: '700',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            background: '#dcfce7',
                            color: '#15803d',
                        }}
                    >
                        🟢 ACTIVE
                    </span>
                </div>
                <div
                    style={{
                        fontSize: '18px',
                        fontWeight: '700',
                        color: '#2563eb',
                        marginTop: '8px',
                        wordBreak: 'break-all',
                    }}
                >
                    {activePromptTag}
                </div>
                <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>
                    Mutates twice weekly
                </div>
            </div>
        </div>
    );
}

function HeroPredictionCard({ prediction }: { prediction: DailyPrediction }) {
    const isUp = prediction.predicted_direction === 'UP';

    return (
        <div
            style={{
                padding: '24px',
                borderRadius: '16px',
                background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
                color: '#ffffff',
                marginBottom: '32px',
                boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)',
            }}
        >
            <div
                style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '16px',
                }}
            >
                <span
                    style={{
                        fontSize: '14px',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        color: '#94a3b8',
                        fontWeight: '600',
                    }}
                >
                    Latest Prediction • {prediction.target_date} ({prediction.ticker})
                </span>
                <span
                    style={{
                        padding: '6px 14px',
                        borderRadius: '20px',
                        fontSize: '13px',
                        fontWeight: '700',
                        background: prediction.status === 'evaluated' ? '#334155' : '#1e3a8a',
                        color: prediction.status === 'evaluated' ? '#cbd5e1' : '#93c5fd',
                    }}
                >
                    {prediction.status.toUpperCase()}
                </span>
            </div>

            <div
                style={{
                    display: 'flex',
                    alignItems: 'baseline',
                    gap: '16px',
                    marginBottom: '16px',
                }}
            >
                <span
                    style={{
                        fontSize: '36px',
                        fontWeight: '900',
                        color: isUp ? '#4ade80' : '#f87171',
                    }}
                >
                    {isUp ? '▲ UP' : '▼ DOWN'}
                </span>
                <span style={{ fontSize: '20px', fontWeight: '600', color: '#e2e8f0' }}>
                    {prediction.confidence}% Confidence
                </span>
                {prediction.expected_return_pct !== null && (
                    <span style={{ fontSize: '16px', color: '#94a3b8' }}>
                        (Expected Return: {prediction.expected_return_pct > 0 ? '+' : ''}
                        {prediction.expected_return_pct}%)
                    </span>
                )}
            </div>

            {prediction.rationale && (
                <div
                    style={{
                        fontSize: '15px',
                        lineHeight: '1.6',
                        color: '#cbd5e1',
                        marginBottom: '16px',
                    }}
                >
                    <strong>Rationale:</strong> {prediction.rationale}
                </div>
            )}

            {prediction.catalysts && prediction.catalysts.length > 0 && (
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {prediction.catalysts.map((cat) => (
                        <span
                            key={cat}
                            style={{
                                padding: '4px 10px',
                                background: '#334155',
                                borderRadius: '6px',
                                fontSize: '12px',
                                color: '#e2e8f0',
                            }}
                        >
                            {cat}
                        </span>
                    ))}
                </div>
            )}
        </div>
    );
}

interface PredictionRowProps {
    p: DailyPrediction;
    isExpanded: boolean;
    onToggleExpand: () => void;
    matchingExp?: PromptExperiment;
}

function PredictionTableRowItem({
    p,
    isExpanded,
    onToggleExpand,
    matchingExp,
}: PredictionRowProps) {
    return (
        <>
            <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                <td style={{ padding: '12px 16px', fontWeight: '600' }}>{p.target_date}</td>
                <td style={{ padding: '12px 16px' }}>{p.ticker}</td>
                <td
                    style={{
                        padding: '12px 16px',
                        fontWeight: '700',
                        color: p.predicted_direction === 'UP' ? '#16a34a' : '#dc2626',
                    }}
                >
                    {p.predicted_direction}
                </td>
                <td style={{ padding: '12px 16px' }}>{p.confidence}%</td>
                <td style={{ padding: '12px 16px' }}>
                    {p.open_price !== null ? `$${p.open_price.toFixed(2)}` : '-'}
                </td>
                <td style={{ padding: '12px 16px' }}>
                    {p.close_price !== null ? `$${p.close_price.toFixed(2)}` : '-'}
                </td>
                <td style={{ padding: '12px 16px', fontWeight: '600' }}>
                    {p.actual_direction || '-'}
                </td>
                <td style={{ padding: '12px 16px' }}>
                    {p.intraday_hit === true && (
                        <span
                            style={{
                                padding: '4px 8px',
                                borderRadius: '4px',
                                background: '#e0f2fe',
                                color: '#0369a1',
                                fontWeight: '600',
                                fontSize: '12px',
                            }}
                        >
                            HIT
                        </span>
                    )}
                    {p.intraday_hit === false && (
                        <span
                            style={{
                                padding: '4px 8px',
                                borderRadius: '4px',
                                background: '#fef3c7',
                                color: '#b45309',
                                fontWeight: '600',
                                fontSize: '12px',
                            }}
                        >
                            MISSED
                        </span>
                    )}
                    {p.intraday_hit === null && (
                        <span style={{ color: '#94a3b8', fontSize: '12px' }}>-</span>
                    )}
                </td>
                <td style={{ padding: '12px 16px' }}>
                    {p.is_correct === true && (
                        <span
                            style={{
                                padding: '4px 8px',
                                borderRadius: '4px',
                                background: '#dcfce7',
                                color: '#15803d',
                                fontWeight: '600',
                                fontSize: '12px',
                            }}
                        >
                            PASS
                        </span>
                    )}
                    {p.is_correct === false && (
                        <span
                            style={{
                                padding: '4px 8px',
                                borderRadius: '4px',
                                background: '#fee2e2',
                                color: '#b91c1c',
                                fontWeight: '600',
                                fontSize: '12px',
                            }}
                        >
                            FAIL
                        </span>
                    )}
                    {p.is_correct === null && (
                        <span
                            style={{
                                padding: '4px 8px',
                                borderRadius: '4px',
                                background: '#f1f5f9',
                                color: '#64748b',
                                fontSize: '12px',
                            }}
                        >
                            PENDING
                        </span>
                    )}
                </td>
                <td style={{ padding: '12px 16px' }}>
                    {p.brier_score !== null ? p.brier_score.toFixed(4) : '-'}
                </td>
                <td style={{ padding: '12px 16px' }}>
                    <button
                        type="button"
                        onClick={onToggleExpand}
                        style={{
                            padding: '4px 10px',
                            borderRadius: '6px',
                            border: '1px solid #cbd5e1',
                            background: isExpanded ? '#e2e8f0' : '#ffffff',
                            color: '#2563eb',
                            fontWeight: '600',
                            fontSize: '12px',
                            cursor: 'pointer',
                        }}
                    >
                        {isExpanded ? 'Hide Details' : 'View Details & Prompt'}
                    </button>
                </td>
            </tr>
            {isExpanded && <PredictionExpandedDetail p={p} matchingExp={matchingExp} />}
        </>
    );
}

function PredictionExpandedDetail({
    p,
    matchingExp,
}: {
    p: DailyPrediction;
    matchingExp?: PromptExperiment;
}) {
    return (
        <tr
            style={{
                background: '#f8fafc',
                borderBottom: '2px solid #e2e8f0',
            }}
        >
            <td colSpan={11} style={{ padding: '16px 24px' }}>
                <div
                    style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '16px',
                    }}
                >
                    {/* Rationale & Catalysts */}
                    <div>
                        <div
                            style={{
                                fontSize: '13px',
                                fontWeight: '700',
                                color: '#475569',
                                marginBottom: '6px',
                            }}
                        >
                            PREDICTION RATIONALE & CATALYSTS
                        </div>
                        <p
                            style={{
                                fontSize: '14px',
                                color: '#1e293b',
                                margin: '0 0 10px 0',
                                lineHeight: '1.6',
                            }}
                        >
                            {p.rationale || 'No detailed rationale recorded for this prediction.'}
                        </p>
                        {p.catalysts && p.catalysts.length > 0 && (
                            <div
                                style={{
                                    display: 'flex',
                                    gap: '8px',
                                    flexWrap: 'wrap',
                                }}
                            >
                                {p.catalysts.map((cat) => (
                                    <span
                                        key={cat}
                                        style={{
                                            padding: '4px 10px',
                                            background: '#e2e8f0',
                                            borderRadius: '6px',
                                            fontSize: '12px',
                                            fontWeight: '600',
                                            color: '#334155',
                                        }}
                                    >
                                        {cat}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Price & Intraday Metrics */}
                    <div
                        style={{
                            display: 'flex',
                            gap: '20px',
                            fontSize: '13px',
                            color: '#64748b',
                            flexWrap: 'wrap',
                        }}
                    >
                        <div>
                            <strong>Expected Return:</strong>{' '}
                            {p.expected_return_pct !== null
                                ? `${p.expected_return_pct > 0 ? '+' : ''}${p.expected_return_pct}%`
                                : '-'}
                        </div>
                        <div>
                            <strong>Open:</strong>{' '}
                            {p.open_price !== null ? `$${p.open_price.toFixed(2)}` : '-'}
                        </div>
                        <div>
                            <strong>High:</strong>{' '}
                            {p.high_price !== null && p.high_price !== undefined
                                ? `$${p.high_price.toFixed(2)}`
                                : '-'}
                        </div>
                        <div>
                            <strong>Low:</strong>{' '}
                            {p.low_price !== null && p.low_price !== undefined
                                ? `$${p.low_price.toFixed(2)}`
                                : '-'}
                        </div>
                        <div>
                            <strong>Close:</strong>{' '}
                            {p.close_price !== null ? `$${p.close_price.toFixed(2)}` : '-'}
                        </div>
                        <div>
                            <strong>Model:</strong> {p.model_name}
                        </div>
                    </div>

                    {/* System Prompt Used */}
                    <div>
                        <div
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '10px',
                                marginBottom: '8px',
                            }}
                        >
                            <span
                                style={{
                                    fontSize: '13px',
                                    fontWeight: '700',
                                    color: '#475569',
                                }}
                            >
                                SYSTEM PROMPT VARIANT:
                            </span>
                            <span
                                style={{
                                    fontFamily: 'monospace',
                                    fontSize: '12px',
                                    fontWeight: '700',
                                    background: '#dbeafe',
                                    color: '#1e40af',
                                    padding: '2px 8px',
                                    borderRadius: '4px',
                                }}
                            >
                                {p.prompt_variant_tag || 'baseline'}
                            </span>
                        </div>
                        <pre
                            style={{
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-word',
                                fontSize: '12px',
                                background: '#ffffff',
                                padding: '14px',
                                borderRadius: '8px',
                                border: '1px solid #cbd5e1',
                                color: '#334155',
                                margin: 0,
                            }}
                        >
                            {matchingExp?.prompt_content ||
                                'Standard baseline system prompt active during prediction.'}
                        </pre>
                    </div>
                </div>
            </td>
        </tr>
    );
}

function PredictionsTable({
    predictions,
    experiments,
}: {
    predictions: DailyPrediction[];
    experiments: PromptExperiment[];
}) {
    const [expandedId, setExpandedId] = useState<string | null>(null);

    return (
        <div style={{ overflowX: 'auto', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
            <table
                style={{
                    width: '100%',
                    borderCollapse: 'collapse',
                    textAlign: 'left',
                    fontSize: '14px',
                }}
            >
                <thead>
                    <tr
                        style={{
                            background: '#f8fafc',
                            borderBottom: '1px solid #e2e8f0',
                            color: '#475569',
                        }}
                    >
                        <th style={{ padding: '12px 16px' }}>Date</th>
                        <th style={{ padding: '12px 16px' }}>Ticker</th>
                        <th style={{ padding: '12px 16px' }}>Prediction</th>
                        <th style={{ padding: '12px 16px' }}>Confidence</th>
                        <th style={{ padding: '12px 16px' }}>Open Price</th>
                        <th style={{ padding: '12px 16px' }}>Close Price</th>
                        <th style={{ padding: '12px 16px' }}>Actual Dir</th>
                        <th style={{ padding: '12px 16px' }}>Intraday Hit</th>
                        <th style={{ padding: '12px 16px' }}>Outcome</th>
                        <th style={{ padding: '12px 16px' }}>Brier Score</th>
                        <th style={{ padding: '12px 16px' }}>Prompt & Rationale</th>
                    </tr>
                </thead>
                <tbody>
                    {predictions.map((p) => {
                        const isExpanded = expandedId === p.id;
                        const matchingExp = experiments.find(
                            (e) => e.variant_tag === p.prompt_variant_tag,
                        );

                        return (
                            <PredictionTableRowItem
                                key={p.id}
                                p={p}
                                isExpanded={isExpanded}
                                onToggleExpand={() => setExpandedId(isExpanded ? null : p.id)}
                                matchingExp={matchingExp}
                            />
                        );
                    })}

                    {predictions.length === 0 && (
                        <tr>
                            <td
                                colSpan={11}
                                style={{ padding: '24px', textAlign: 'center', color: '#94a3b8' }}
                            >
                                No daily predictions logged yet. Run `python main.py
                                --daily-predictor` to generate one.
                            </td>
                        </tr>
                    )}
                </tbody>
            </table>
        </div>
    );
}

function computeDailyPredictionStats(predictions: DailyPrediction[]) {
    const evaluatedPredictions = predictions.filter((p) => p.status === 'evaluated');
    const totalEvaluated = evaluatedPredictions.length;
    const correctCount = evaluatedPredictions.filter((p) => p.is_correct === true).length;
    const accuracyPct =
        totalEvaluated > 0 ? ((correctCount / totalEvaluated) * 100).toFixed(1) : 'N/A';

    const intradayHitCount = evaluatedPredictions.filter(
        (p) => p.intraday_hit === true || (p.intraday_hit === null && p.is_correct === true),
    ).length;
    const intradayHitPct =
        totalEvaluated > 0 ? ((intradayHitCount / totalEvaluated) * 100).toFixed(1) : 'N/A';

    const brierScores = evaluatedPredictions
        .map((p) => p.brier_score)
        .filter((s): s is number => s !== null && s !== undefined);
    const avgBrier =
        brierScores.length > 0
            ? (brierScores.reduce((a, b) => a + b, 0) / brierScores.length).toFixed(4)
            : 'N/A';

    return { correctCount, totalEvaluated, accuracyPct, intradayHitPct, avgBrier };
}

interface ModelConfig {
    id: string;
    label: string;
    matches: (modelName: string) => boolean;
}

const PREDICTOR_MODELS: ModelConfig[] = [
    {
        id: 'deepseek-v4-flash',
        label: 'DeepSeek Flash',
        matches: (m: string) => m.toLowerCase().includes('deepseek'),
    },
    {
        id: 'MiniMax-M3',
        label: 'MiniMax M3',
        matches: (m: string) => m.toLowerCase().includes('minimax'),
    },
];

interface AutoresearchMilestonesProps {
    experiments: PromptExperiment[];
    allExperiments?: PromptExperiment[];
}

function resolveActiveDailyPrompt(
    modelExperiments: PromptExperiment[],
    allExperiments: PromptExperiment[] = [],
): { activePrompt: PromptExperiment | null; isFallback: boolean; isBaselineAnchor: boolean } {
    // 1. Model-specific track active prompt
    const trackActive = modelExperiments.find((e) => e.status === 'active');
    if (trackActive) {
        return { activePrompt: trackActive, isFallback: false, isBaselineAnchor: false };
    }

    // 2. Global active prompt across tracks (e.g. shared arena fallback)
    const globalActive = allExperiments.find((e) => e.status === 'active');
    if (globalActive) {
        return { activePrompt: globalActive, isFallback: true, isBaselineAnchor: false };
    }

    // 3. Fall back to best baseline prompt in model track
    const trackBaseline = modelExperiments.find((e) => e.status === 'baseline');
    if (trackBaseline) {
        return { activePrompt: trackBaseline, isFallback: false, isBaselineAnchor: true };
    }

    // 4. Fall back to global baseline prompt
    const globalBaseline = allExperiments.find((e) => e.status === 'baseline');
    if (globalBaseline) {
        return { activePrompt: globalBaseline, isFallback: true, isBaselineAnchor: true };
    }

    return {
        activePrompt: modelExperiments[0] || allExperiments[0] || null,
        isFallback: false,
        isBaselineAnchor: false,
    };
}

function computeExperimentMilestones(
    experiments: PromptExperiment[],
    allExperiments: PromptExperiment[] = [],
) {
    const { activePrompt, isFallback, isBaselineAnchor } = resolveActiveDailyPrompt(
        experiments,
        allExperiments,
    );
    const activeScore = activePrompt?.metrics?.score ?? null;

    let bestBaselineScore: number | null = null;
    for (const exp of experiments) {
        const s = exp.metrics?.score;
        if (typeof s === 'number' && (bestBaselineScore === null || s > bestBaselineScore)) {
            bestBaselineScore = s;
        }
    }

    const parentExp = experiments.find((e) => e.variant_tag === activePrompt?.parent_tag);
    const parentScore = parentExp?.metrics?.score ?? null;
    const delta =
        activeScore !== null && parentScore !== null
            ? Number(activeScore) - Number(parentScore)
            : null;

    return {
        activeExp: activePrompt,
        activeScore,
        bestBaselineScore,
        delta,
        isFallback,
        isBaselineAnchor,
    };
}

interface MilestoneCardProps {
    title: string;
    value: React.ReactNode;
    subtitle: string;
    valueColor?: string;
    fontSize?: string;
}

function MilestoneCard({
    title,
    value,
    subtitle,
    valueColor = '#0f172a',
    fontSize = '28px',
}: MilestoneCardProps) {
    return (
        <div
            style={{
                padding: '20px',
                background: '#f8fafc',
                borderRadius: '12px',
                border: '1px solid #e2e8f0',
            }}
        >
            <div style={{ fontSize: '13px', color: '#64748b', fontWeight: '600' }}>{title}</div>
            <div
                style={{
                    fontSize,
                    fontWeight: '700',
                    color: valueColor,
                    marginTop: '4px',
                }}
            >
                {value}
            </div>
            <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>{subtitle}</div>
        </div>
    );
}

function formatDeltaText(delta: number | null): string {
    if (delta === null) return 'Baseline Initialized';
    const sign = delta > 0 ? '▲ +' : delta < 0 ? '▼ ' : '';
    return `${sign}${delta.toFixed(2)} vs Parent`;
}

function getDeltaColor(delta: number | null): string {
    if (delta === null) return '#0f172a';
    if (delta > 0) return '#16a34a';
    if (delta < 0) return '#dc2626';
    return '#0f172a';
}

function getActiveBadge(status?: string) {
    if (status === 'active') {
        return { text: '🟢 ACTIVE', bg: '#dcfce7', color: '#15803d' };
    }
    if (status === 'baseline') {
        return { text: '🏆 BASELINE', bg: '#ede9fe', color: '#6b21a8' };
    }
    return {
        text: `📦 ${status?.toUpperCase() || 'BASELINE'}`,
        bg: '#f1f5f9',
        color: '#475569',
    };
}

function getMilestoneSubtitle(
    isFallback: boolean,
    isBaselineAnchor: boolean,
    status?: string,
): string {
    if (isFallback) return 'Track mutation discarded; relying on arena active fallback';
    if (isBaselineAnchor) return 'Ratchet-reverted to all-time benchmark';
    if (status === 'active') return 'Live mutated strategy undergoing evaluation';
    return `Status: ${status || 'baseline'}`;
}

function AutoresearchMilestoneCards({
    experiments,
    allExperiments = [],
}: AutoresearchMilestonesProps) {
    const { activeExp, activeScore, bestBaselineScore, delta, isFallback, isBaselineAnchor } =
        computeExperimentMilestones(experiments, allExperiments);

    const deltaColor = getDeltaColor(delta);
    const deltaText = formatDeltaText(delta);

    const isScorePositive = activeScore !== null && Number(activeScore) > 0;
    const activeScoreColor = isScorePositive ? '#16a34a' : '#0f172a';
    const activeScoreDisplay = activeScore !== null ? Number(activeScore).toFixed(2) : 'N/A';
    const bestBaselineDisplay = bestBaselineScore !== null ? bestBaselineScore.toFixed(2) : 'N/A';

    const activeTagDisplay = activeExp?.variant_tag || 'daily-pred-baseline';
    const activeBadge = getActiveBadge(activeExp?.status);
    const activeSubtitle = getMilestoneSubtitle(isFallback, isBaselineAnchor, activeExp?.status);

    return (
        <div
            style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                gap: '16px',
                marginBottom: '24px',
            }}
        >
            <MilestoneCard
                title="Current Active Prompt"
                value={
                    <div
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            flexWrap: 'wrap',
                        }}
                    >
                        <span
                            style={{
                                fontSize: '15px',
                                fontWeight: '700',
                                color: '#2563eb',
                                wordBreak: 'break-all',
                            }}
                        >
                            {activeTagDisplay}
                        </span>
                        <span
                            style={{
                                fontSize: '10px',
                                fontWeight: '700',
                                padding: '2px 6px',
                                borderRadius: '4px',
                                background: activeBadge.bg,
                                color: activeBadge.color,
                            }}
                        >
                            {activeBadge.text}
                        </span>
                    </div>
                }
                subtitle={activeSubtitle}
            />
            <MilestoneCard
                title="Active Ratchet Score"
                value={activeScoreDisplay}
                subtitle="Weighted accuracy, target hit & Brier"
                valueColor={activeScoreColor}
            />
            <MilestoneCard
                title="All-Time Best Baseline"
                value={bestBaselineDisplay}
                subtitle="Highest performance benchmark"
                valueColor="#4f46e5"
            />
            <MilestoneCard
                title="Score Progression"
                value={deltaText}
                subtitle={activeSubtitle}
                valueColor={deltaColor}
                fontSize="24px"
            />
            <MilestoneCard
                title="Mutated Variants Tracked"
                value={experiments.length}
                subtitle="Evolution iterations for model"
            />
        </div>
    );
}

interface VariantSidebarItemProps {
    exp: PromptExperiment;
    isSelected: boolean;
    isActiveVariant?: boolean;
    onSelect: () => void;
}

function getSidebarStatusBadge(status: string) {
    if (status === 'active') return { bg: '#dcfce7', color: '#15803d', label: '🟢 ACTIVE' };
    if (status === 'baseline') return { bg: '#ede9fe', color: '#6b21a8', label: '🏆 BASELINE' };
    if (status === 'discarded') return { bg: '#fee2e2', color: '#b91c1c', label: '❌ DISCARDED' };
    return { bg: '#f1f5f9', color: '#475569', label: '📦 SAVED' };
}

function VariantSidebarItem({
    exp,
    isSelected,
    isActiveVariant,
    onSelect,
}: VariantSidebarItemProps) {
    const score = exp.metrics?.score;
    const isScorePositive = typeof score === 'number' && score > 0;
    const statusBadge = getSidebarStatusBadge(exp.status);

    const borderStyle = isSelected
        ? '2px solid #3b82f6'
        : isActiveVariant
          ? '2px solid #22c55e'
          : '1px solid #e2e8f0';
    const bgStyle = isSelected ? '#eff6ff' : isActiveVariant ? '#f0fdf4' : '#ffffff';

    return (
        <button
            type="button"
            onClick={onSelect}
            style={{
                padding: '12px',
                borderRadius: '8px',
                border: borderStyle,
                background: bgStyle,
                textAlign: 'left',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
            }}
        >
            <div
                style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    gap: '8px',
                }}
            >
                <span
                    style={{
                        fontWeight: '700',
                        fontSize: '13px',
                        color: isSelected ? '#1d4ed8' : '#0f172a',
                        wordBreak: 'break-all',
                    }}
                >
                    {exp.variant_tag}
                </span>
                {typeof score === 'number' && (
                    <span
                        style={{
                            fontSize: '12px',
                            fontWeight: '700',
                            color: isScorePositive ? '#15803d' : '#b91c1c',
                            background: isScorePositive ? '#dcfce7' : '#fee2e2',
                            padding: '2px 6px',
                            borderRadius: '4px',
                        }}
                    >
                        {score.toFixed(1)}
                    </span>
                )}
            </div>
            <div
                style={{
                    display: 'flex',
                    gap: '6px',
                    marginTop: '6px',
                    flexWrap: 'wrap',
                }}
            >
                <span
                    style={{
                        padding: '2px 6px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        fontWeight: '700',
                        background: statusBadge.bg,
                        color: statusBadge.color,
                    }}
                >
                    {statusBadge.label}
                </span>
                <span
                    style={{
                        fontSize: '11px',
                        color: '#64748b',
                        alignSelf: 'center',
                    }}
                >
                    {exp.experiment_type || 'incremental'}
                </span>
            </div>
        </button>
    );
}

function SelectedVariantHeader({
    experiment,
    isActiveVariant,
}: {
    experiment: PromptExperiment;
    isActiveVariant: boolean;
}) {
    const statusBadge = getSidebarStatusBadge(experiment.status);

    return (
        <div>
            <div
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '8px',
                    marginBottom: '8px',
                }}
            >
                <h3
                    style={{
                        fontSize: '16px',
                        fontWeight: '700',
                        color: '#0f172a',
                        margin: 0,
                    }}
                >
                    {experiment.variant_tag}
                </h3>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    {isActiveVariant && (
                        <span
                            style={{
                                fontSize: '11px',
                                fontWeight: '700',
                                padding: '2px 8px',
                                borderRadius: '4px',
                                background: '#dcfce7',
                                color: '#15803d',
                            }}
                        >
                            🟢 CURRENT ACTIVE
                        </span>
                    )}
                    <span
                        style={{
                            padding: '4px 10px',
                            borderRadius: '6px',
                            fontSize: '12px',
                            fontWeight: '700',
                            background: statusBadge.bg,
                            color: statusBadge.color,
                        }}
                    >
                        {statusBadge.label}
                    </span>
                </div>
            </div>

            <div
                style={{
                    display: 'flex',
                    gap: '16px',
                    fontSize: '13px',
                    color: '#64748b',
                    flexWrap: 'wrap',
                    marginTop: '8px',
                }}
            >
                <div>
                    <strong>Score:</strong>{' '}
                    {experiment.metrics?.score !== undefined
                        ? Number(experiment.metrics.score).toFixed(2)
                        : 'Pending'}
                </div>
                {experiment.parent_tag && (
                    <div>
                        <strong>Parent Variant:</strong> <code>{experiment.parent_tag}</code>
                    </div>
                )}
                {experiment.week_start && (
                    <div>
                        <strong>Period:</strong> {experiment.week_start}
                        {experiment.week_end ? ` → ${experiment.week_end}` : ''}
                    </div>
                )}
            </div>
        </div>
    );
}

function AutoresearchHistoryArena({
    experiments,
    selectedExpId,
    activePromptTag,
    onSelectExp,
}: {
    experiments: PromptExperiment[];
    selectedExpId: string | null;
    activePromptTag?: string | null;
    onSelectExp: (id: string) => void;
}) {
    const selectedExperiment =
        experiments.find((e) => e.id === selectedExpId) || experiments[0] || null;

    if (experiments.length === 0) {
        return (
            <div
                style={{
                    background: '#ffffff',
                    borderRadius: '12px',
                    border: '1px solid #e2e8f0',
                    padding: '32px',
                    textAlign: 'center',
                    color: '#64748b',
                }}
            >
                No prompt experiments or autoresearch runs recorded for this model track yet. Runs
                execute twice weekly (Sun & Wed 6:00 PM ET).
            </div>
        );
    }

    return (
        <div
            className="p-4 sm:p-6"
            style={{
                background: '#ffffff',
                borderRadius: '12px',
                border: '1px solid #e2e8f0',
                boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
            }}
        >
            <div
                style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '12px',
                    marginBottom: '16px',
                }}
            >
                <h2
                    style={{
                        fontSize: '18px',
                        fontWeight: '700',
                        color: '#0f172a',
                        margin: 0,
                    }}
                >
                    Autoresearch Prompt Lineage & Benchmarks
                </h2>
                {activePromptTag && (
                    <div
                        style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            background: '#f0fdf4',
                            border: '1px solid #bbf7d0',
                            padding: '4px 12px',
                            borderRadius: '20px',
                            fontSize: '12px',
                            color: '#15803d',
                            fontWeight: '600',
                        }}
                    >
                        <span>🟢 Active Runtime:</span>
                        <code style={{ fontFamily: 'monospace', fontWeight: '700' }}>
                            {activePromptTag}
                        </code>
                    </div>
                )}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-[minmax(280px,340px)_1fr] gap-6 mt-4">
                {/* Variant List Sidebar */}
                <div className="border-b lg:border-b-0 lg:border-r border-slate-100 pb-6 lg:pb-0 lg:pr-4">
                    <div
                        style={{
                            fontSize: '12px',
                            fontWeight: '700',
                            color: '#94a3b8',
                            marginBottom: '10px',
                            textTransform: 'uppercase',
                            letterSpacing: '0.05em',
                        }}
                    >
                        Experiment Lineage
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {experiments.map((exp) => (
                            <VariantSidebarItem
                                key={exp.id}
                                exp={exp}
                                isSelected={exp.id === selectedExperiment?.id}
                                isActiveVariant={exp.variant_tag === activePromptTag}
                                onSelect={() => onSelectExp(exp.id)}
                            />
                        ))}
                    </div>
                </div>

                {/* Variant Details & Prompt Inspector */}
                {selectedExperiment && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        <SelectedVariantHeader
                            experiment={selectedExperiment}
                            isActiveVariant={selectedExperiment.variant_tag === activePromptTag}
                        />

                        {selectedExperiment.change_description && (
                            <div
                                style={{
                                    background: '#f8fafc',
                                    padding: '12px 16px',
                                    borderRadius: '8px',
                                    border: '1px solid #e2e8f0',
                                    fontSize: '13px',
                                    color: '#334155',
                                }}
                            >
                                <strong>Mutation Rationale:</strong>{' '}
                                {selectedExperiment.change_description}
                            </div>
                        )}

                        <div>
                            <div
                                style={{
                                    fontSize: '13px',
                                    fontWeight: '700',
                                    color: '#475569',
                                    marginBottom: '6px',
                                }}
                            >
                                SYSTEM PROMPT STRATEGY CONTENT:
                            </div>
                            <pre
                                style={{
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word',
                                    fontSize: '12px',
                                    background: '#0f172a',
                                    color: '#f8fafc',
                                    padding: '16px',
                                    borderRadius: '8px',
                                    lineHeight: '1.5',
                                    maxHeight: '400px',
                                    overflowY: 'auto',
                                    margin: 0,
                                }}
                            >
                                {selectedExperiment.prompt_content}
                            </pre>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export function DailyPredictionsPage({ initialPredictions, experiments }: Props) {
    const [predictions] = useState<DailyPrediction[]>(initialPredictions);
    const [promptExperiments] = useState<PromptExperiment[]>(experiments);
    const [selectedModelId, setSelectedModelId] = useState<string>(PREDICTOR_MODELS[0].id);
    const [viewMode, setViewMode] = useState<'predictions' | 'autoresearch'>('predictions');
    const [selectedExpId, setSelectedExpId] = useState<string | null>(null);

    // Identify dynamic or configured models
    const activeModelCfg =
        PREDICTOR_MODELS.find((m) => m.id === selectedModelId) || PREDICTOR_MODELS[0];

    const modelPredictions = predictions.filter((p) => activeModelCfg.matches(p.model_name));
    const modelExperiments = promptExperiments.filter((e) =>
        e.track_id ? activeModelCfg.matches(e.track_id) : true,
    );

    const latestPrediction = modelPredictions.length > 0 ? modelPredictions[0] : null;
    const { correctCount, totalEvaluated, accuracyPct, intradayHitPct, avgBrier } =
        computeDailyPredictionStats(modelPredictions);

    const { activePrompt } = resolveActiveDailyPrompt(modelExperiments, promptExperiments);

    return (
        <div
            style={{
                padding: '24px',
                maxWidth: '1200px',
                margin: '0 auto',
                fontFamily: 'system-ui, sans-serif',
            }}
        >
            <div
                style={{
                    marginBottom: '24px',
                }}
            >
                <h1
                    style={{
                        fontSize: '28px',
                        fontWeight: '700',
                        margin: '0 0 8px 0',
                        color: '#0f172a',
                    }}
                >
                    Daily S&P Market Predictor
                </h1>
                <p style={{ margin: 0, color: '#64748b', fontSize: '15px' }}>
                    9:15 AM ET Intraday (Open to Close) Directional AI Predictions powered by
                    DeepSeek Flash & MiniMax.
                </p>
            </div>

            {/* Model Navigation Tabs and Relocated Backtest Arena Button */}
            <div
                style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    borderBottom: '2px solid #e2e8f0',
                    marginBottom: '20px',
                    gap: '16px',
                    flexWrap: 'wrap',
                }}
            >
                <div style={{ display: 'flex', gap: '8px' }}>
                    {PREDICTOR_MODELS.map((model) => {
                        const count = predictions.filter((p) => model.matches(p.model_name)).length;
                        const isSelected = activeModelCfg.id === model.id;
                        return (
                            <button
                                key={model.id}
                                type="button"
                                onClick={() => setSelectedModelId(model.id)}
                                style={{
                                    padding: '12px 20px',
                                    border: 'none',
                                    background: 'none',
                                    fontWeight: '600',
                                    fontSize: '15px',
                                    cursor: 'pointer',
                                    color: isSelected ? '#2563eb' : '#64748b',
                                    borderBottom: isSelected
                                        ? '3px solid #2563eb'
                                        : '3px solid transparent',
                                    marginBottom: '-2px',
                                }}
                            >
                                {model.label} ({count})
                            </button>
                        );
                    })}
                </div>

                <div style={{ paddingBottom: '8px' }}>
                    <Link
                        to="/daily-predictions-backtest"
                        style={{
                            padding: '8px 16px',
                            borderRadius: '8px',
                            background: '#f8fafc',
                            color: '#334155',
                            textDecoration: 'none',
                            fontWeight: '600',
                            fontSize: '14px',
                            border: '1px solid #cbd5e1',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                        }}
                    >
                        Backtest Arena ↗
                    </Link>
                </div>
            </div>

            {/* Sub-view Switcher: Predictions Log vs Autoresearch & Benchmark History */}
            <div
                style={{
                    display: 'inline-flex',
                    background: '#f1f5f9',
                    padding: '4px',
                    borderRadius: '10px',
                    marginBottom: '24px',
                    gap: '4px',
                }}
            >
                <button
                    type="button"
                    onClick={() => setViewMode('predictions')}
                    style={{
                        padding: '8px 16px',
                        borderRadius: '7px',
                        border: 'none',
                        background: viewMode === 'predictions' ? '#ffffff' : 'transparent',
                        color: viewMode === 'predictions' ? '#0f172a' : '#64748b',
                        fontWeight: '600',
                        fontSize: '13px',
                        cursor: 'pointer',
                        boxShadow:
                            viewMode === 'predictions' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                    }}
                >
                    Predictions Log
                </button>
                <button
                    type="button"
                    onClick={() => setViewMode('autoresearch')}
                    style={{
                        padding: '8px 16px',
                        borderRadius: '7px',
                        border: 'none',
                        background: viewMode === 'autoresearch' ? '#ffffff' : 'transparent',
                        color: viewMode === 'autoresearch' ? '#0f172a' : '#64748b',
                        fontWeight: '600',
                        fontSize: '13px',
                        cursor: 'pointer',
                        boxShadow:
                            viewMode === 'autoresearch' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                    }}
                >
                    Autoresearch & Benchmark History
                </button>
            </div>

            {viewMode === 'predictions' ? (
                <>
                    <DailyMetricsOverview
                        accuracyPct={accuracyPct}
                        intradayHitPct={intradayHitPct}
                        correctCount={correctCount}
                        totalEvaluated={totalEvaluated}
                        avgBrier={avgBrier}
                        totalPredictions={modelPredictions.length}
                        activePromptTag={activePrompt?.variant_tag || 'daily-pred-baseline'}
                    />

                    {latestPrediction && <HeroPredictionCard prediction={latestPrediction} />}

                    <PredictionsTable
                        predictions={modelPredictions}
                        experiments={promptExperiments}
                    />
                </>
            ) : (
                <>
                    <AutoresearchMilestoneCards
                        experiments={modelExperiments}
                        allExperiments={promptExperiments}
                    />
                    <AutoresearchHistoryArena
                        experiments={modelExperiments}
                        selectedExpId={selectedExpId}
                        activePromptTag={activePrompt?.variant_tag}
                        onSelectExp={(id) => setSelectedExpId(id)}
                    />
                </>
            )}
        </div>
    );
}
