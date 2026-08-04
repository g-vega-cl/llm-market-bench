import type { PromptExperiment } from '@llm-market-bench/database';
import { useState } from 'react';
import type { DailyPrediction } from '../api/fetch-daily-predictions';

interface Props {
    initialPredictions: DailyPrediction[];
    experiments: PromptExperiment[];
    refreshFn?: () => Promise<{ predictions: DailyPrediction[]; experiments: PromptExperiment[] }>;
}

function DailyMetricsOverview({
    accuracyPct,
    correctCount,
    totalEvaluated,
    avgBrier,
    totalPredictions,
    activePromptTag,
}: {
    accuracyPct: string;
    correctCount: number;
    totalEvaluated: number;
    avgBrier: string;
    totalPredictions: number;
    activePromptTag: string;
}) {
    return (
        <div
            style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                gap: '16px',
                marginBottom: '32px',
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
                <div style={{ fontSize: '13px', color: '#64748b', fontWeight: '600' }}>
                    Active Prompt Variant
                </div>
                <div
                    style={{
                        fontSize: '18px',
                        fontWeight: '700',
                        color: '#2563eb',
                        marginTop: '8px',
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

function PredictionsTable({ predictions }: { predictions: DailyPrediction[] }) {
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
                        <th style={{ padding: '12px 16px' }}>Outcome</th>
                        <th style={{ padding: '12px 16px' }}>Brier Score</th>
                    </tr>
                </thead>
                <tbody>
                    {predictions.map((p) => (
                        <tr key={p.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                            <td style={{ padding: '12px 16px', fontWeight: '600' }}>
                                {p.target_date}
                            </td>
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
                        </tr>
                    ))}

                    {predictions.length === 0 && (
                        <tr>
                            <td
                                colSpan={9}
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

function AutoresearchTab({ experiments }: { experiments: PromptExperiment[] }) {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {experiments.map((exp) => (
                <div
                    key={exp.id || exp.variant_tag}
                    style={{
                        padding: '20px',
                        borderRadius: '12px',
                        border: '1px solid #e2e8f0',
                        background: '#ffffff',
                    }}
                >
                    <div
                        style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            marginBottom: '12px',
                        }}
                    >
                        <div>
                            <span
                                style={{
                                    fontWeight: '700',
                                    fontSize: '16px',
                                    color: '#0f172a',
                                    marginRight: '12px',
                                }}
                            >
                                {exp.variant_tag}
                            </span>
                            <span
                                style={{
                                    padding: '4px 8px',
                                    borderRadius: '4px',
                                    fontSize: '12px',
                                    fontWeight: '600',
                                    background:
                                        exp.status === 'active'
                                            ? '#dbeafe'
                                            : exp.status === 'baseline'
                                              ? '#dcfce7'
                                              : '#f1f5f9',
                                    color:
                                        exp.status === 'active'
                                            ? '#1e40af'
                                            : exp.status === 'baseline'
                                              ? '#166534'
                                              : '#475569',
                                }}
                            >
                                {exp.status.toUpperCase()}
                            </span>
                        </div>
                        <div style={{ fontSize: '13px', color: '#64748b' }}>
                            {exp.created_at ? new Date(exp.created_at).toLocaleDateString() : ''}
                        </div>
                    </div>

                    {exp.change_description && (
                        <p
                            style={{
                                margin: '0 0 12px 0',
                                fontSize: '14px',
                                color: '#475569',
                                fontStyle: 'italic',
                            }}
                        >
                            "{exp.change_description}"
                        </p>
                    )}

                    <details
                        style={{
                            background: '#f8fafc',
                            padding: '12px',
                            borderRadius: '8px',
                            border: '1px solid #f1f5f9',
                        }}
                    >
                        <summary
                            style={{
                                cursor: 'pointer',
                                fontWeight: '600',
                                fontSize: '13px',
                                color: '#2563eb',
                            }}
                        >
                            View Full System Prompt Text
                        </summary>
                        <pre
                            style={{
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-word',
                                fontSize: '12px',
                                marginTop: '12px',
                                color: '#334155',
                            }}
                        >
                            {exp.prompt_content}
                        </pre>
                    </details>
                </div>
            ))}

            {experiments.length === 0 && (
                <div
                    style={{
                        padding: '24px',
                        textAlign: 'center',
                        color: '#94a3b8',
                        border: '1px solid #e2e8f0',
                        borderRadius: '12px',
                    }}
                >
                    No prompt experiments recorded yet.
                </div>
            )}
        </div>
    );
}

export function DailyPredictionsPage({ initialPredictions, experiments, refreshFn }: Props) {
    const [predictions, setPredictions] = useState<DailyPrediction[]>(initialPredictions);
    const [promptExperiments, setPromptExperiments] = useState<PromptExperiment[]>(experiments);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [activeTab, setActiveTab] = useState<'predictions' | 'autoresearch'>('predictions');

    const handleRefresh = async () => {
        if (!refreshFn) return;
        setIsRefreshing(true);
        try {
            const res = await refreshFn();
            setPredictions(res.predictions);
            setPromptExperiments(res.experiments);
        } catch (err) {
            console.error('Failed to refresh daily predictions data:', err);
        } finally {
            setIsRefreshing(false);
        }
    };

    const latestPrediction = predictions.length > 0 ? predictions[0] : null;
    const evaluatedPredictions = predictions.filter((p) => p.status === 'evaluated');
    const correctCount = evaluatedPredictions.filter((p) => p.is_correct === true).length;
    const totalEvaluated = evaluatedPredictions.length;
    const accuracyPct =
        totalEvaluated > 0 ? ((correctCount / totalEvaluated) * 100).toFixed(1) : 'N/A';

    const brierScores = evaluatedPredictions
        .map((p) => p.brier_score)
        .filter((s): s is number => s !== null && s !== undefined);
    const avgBrier =
        brierScores.length > 0
            ? (brierScores.reduce((a, b) => a + b, 0) / brierScores.length).toFixed(4)
            : 'N/A';

    const activePrompt =
        promptExperiments.find((e) => e.status === 'active') || promptExperiments[0] || null;

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
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '24px',
                }}
            >
                <div>
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
                        9:00 AM ET Intraday (Open to Close) Directional AI Predictions powered by
                        DeepSeek Flash & Autoresearch.
                    </p>
                </div>
                {refreshFn && (
                    <button
                        type="button"
                        onClick={handleRefresh}
                        disabled={isRefreshing}
                        style={{
                            padding: '8px 16px',
                            borderRadius: '8px',
                            background: '#2563eb',
                            color: '#ffffff',
                            border: 'none',
                            fontWeight: '600',
                            cursor: isRefreshing ? 'not-allowed' : 'pointer',
                            opacity: isRefreshing ? 0.7 : 1,
                        }}
                    >
                        {isRefreshing ? 'Refreshing...' : 'Refresh Data'}
                    </button>
                )}
            </div>

            <DailyMetricsOverview
                accuracyPct={accuracyPct}
                correctCount={correctCount}
                totalEvaluated={totalEvaluated}
                avgBrier={avgBrier}
                totalPredictions={predictions.length}
                activePromptTag={activePrompt?.variant_tag || 'daily-pred-baseline'}
            />

            {latestPrediction && <HeroPredictionCard prediction={latestPrediction} />}

            <div
                style={{ display: 'flex', borderBottom: '2px solid #e2e8f0', marginBottom: '24px' }}
            >
                <button
                    type="button"
                    onClick={() => setActiveTab('predictions')}
                    style={{
                        padding: '12px 24px',
                        border: 'none',
                        background: 'none',
                        fontWeight: '600',
                        fontSize: '15px',
                        cursor: 'pointer',
                        color: activeTab === 'predictions' ? '#2563eb' : '#64748b',
                        borderBottom:
                            activeTab === 'predictions'
                                ? '3px solid #2563eb'
                                : '3px solid transparent',
                        marginBottom: '-2px',
                    }}
                >
                    Predictions Log
                </button>
                <button
                    type="button"
                    onClick={() => setActiveTab('autoresearch')}
                    style={{
                        padding: '12px 24px',
                        border: 'none',
                        background: 'none',
                        fontWeight: '600',
                        fontSize: '15px',
                        cursor: 'pointer',
                        color: activeTab === 'autoresearch' ? '#2563eb' : '#64748b',
                        borderBottom:
                            activeTab === 'autoresearch'
                                ? '3px solid #2563eb'
                                : '3px solid transparent',
                        marginBottom: '-2px',
                    }}
                >
                    Autoresearch & Prompt Evolution ({promptExperiments.length})
                </button>
            </div>

            {activeTab === 'predictions' ? (
                <PredictionsTable predictions={predictions} />
            ) : (
                <AutoresearchTab experiments={promptExperiments} />
            )}
        </div>
    );
}
