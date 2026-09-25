import type { PromptExperiment } from '@llm-market-bench/database';
import { Link } from '@tanstack/react-router';
import { useState } from 'react';
import { CognitiveToolboxCard } from '../../autoresearch/components/CognitiveToolboxCard';
import { PromptBlocksCard } from '../../autoresearch/components/PromptBlocksCard';
import { PromptChanges } from '../../autoresearch/components/PromptChanges';
import { ResearchRationaleCard } from '../../autoresearch/components/ResearchRationaleCard';
import { splitPromptSections } from '../../autoresearch/utils/promptSections';
import type { DailyPrediction } from '../api/fetch-daily-predictions';
import { DEFAULT_DAILY_PREDICTOR_TOOLS } from './DailyPredictionsPage';

interface Props {
    initialPredictions: DailyPrediction[];
    experiments: PromptExperiment[];
}

function PredictionTableRow({ pred }: { pred: DailyPrediction }) {
    const isUp = pred.predicted_direction === 'UP';
    const isCorrect = pred.is_correct === true;

    return (
        <tr style={{ borderBottom: '1px solid #f8fafc' }}>
            <td style={{ padding: '12px 8px', fontWeight: '600', color: '#334155' }}>
                {pred.target_date || pred.prediction_date}
            </td>
            <td style={{ padding: '12px 8px', fontWeight: '700', color: '#0f172a' }}>
                {pred.ticker}
            </td>
            <td style={{ padding: '12px 8px' }}>
                <span
                    style={{
                        padding: '4px 8px',
                        borderRadius: '6px',
                        fontSize: '12px',
                        fontWeight: '700',
                        background: isUp ? '#dcfce7' : '#fee2e2',
                        color: isUp ? '#15803d' : '#b91c1c',
                    }}
                >
                    {pred.predicted_direction}
                </span>
            </td>
            <td style={{ padding: '12px 8px', fontWeight: '600', color: '#475569' }}>
                {pred.confidence}%
            </td>
            <td style={{ padding: '12px 8px', color: '#64748b' }}>
                {pred.open_price !== null && pred.close_price !== null ? (
                    <span>
                        ${pred.open_price.toFixed(2)} → ${pred.close_price.toFixed(2)}
                    </span>
                ) : (
                    'Pending'
                )}
            </td>
            <td style={{ padding: '12px 8px' }}>
                {pred.status === 'evaluated' ? (
                    <span
                        style={{
                            fontWeight: '700',
                            color: isCorrect ? '#16a34a' : '#dc2626',
                        }}
                    >
                        {isCorrect ? '✓ Correct' : '✗ Incorrect'}
                    </span>
                ) : (
                    <span style={{ color: '#94a3b8' }}>Pending</span>
                )}
            </td>
            <td style={{ padding: '12px 8px', fontFamily: 'monospace', color: '#475569' }}>
                {pred.brier_score !== null ? pred.brier_score.toFixed(4) : '-'}
            </td>
            <td style={{ padding: '12px 8px', fontSize: '12px', color: '#64748b' }}>
                <code>{pred.prompt_variant_tag || 'baseline'}</code>
            </td>
        </tr>
    );
}

export function DailyPredictionsBacktestPage({ initialPredictions, experiments }: Props) {
    const [selectedExpId, setSelectedExpId] = useState<string | null>(
        experiments.length > 0 ? experiments[0].id : null,
    );

    const evaluatedPredictions = initialPredictions.filter((p) => p.status === 'evaluated');
    const correctCount = evaluatedPredictions.filter((p) => p.is_correct === true).length;
    const totalEvaluated = evaluatedPredictions.length;
    const accuracyPct =
        totalEvaluated > 0 ? ((correctCount / totalEvaluated) * 100).toFixed(1) : '0.0';

    const brierScores = evaluatedPredictions
        .map((p) => p.brier_score)
        .filter((s): s is number => s !== null && s !== undefined);

    const avgBrier =
        brierScores.length > 0
            ? (brierScores.reduce((a, b) => a + b, 0) / brierScores.length).toFixed(4)
            : 'N/A';

    const selectedExperiment = experiments.find((e) => e.id === selectedExpId) || experiments[0];

    return (
        <div
            style={{
                maxWidth: '1200px',
                margin: '0 auto',
                padding: '32px 16px',
                fontFamily: 'sans-serif',
            }}
        >
            {/* Header */}
            <div
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '16px',
                    marginBottom: '24px',
                }}
            >
                <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <h1
                            style={{
                                fontSize: '28px',
                                fontWeight: '800',
                                color: '#0f172a',
                                margin: 0,
                            }}
                        >
                            S&P Daily Predictor Backtest Arena
                        </h1>
                        <span
                            style={{
                                background: '#e0e7ff',
                                color: '#4338ca',
                                padding: '4px 10px',
                                borderRadius: '9999px',
                                fontSize: '12px',
                                fontWeight: '700',
                            }}
                        >
                            DeepSeek Flash Sandbox
                        </span>
                    </div>
                    <p style={{ color: '#64748b', fontSize: '14px', marginTop: '6px', margin: 0 }}>
                        Temporal sandbox audit of S&P 500 (SPY) daily open-to-close predictions and
                        weekly prompt mutations.
                    </p>
                </div>

                <div style={{ display: 'flex', gap: '10px' }}>
                    <Link
                        to="/daily-predictions"
                        style={{
                            padding: '8px 16px',
                            borderRadius: '8px',
                            background: '#f1f5f9',
                            color: '#475569',
                            textDecoration: 'none',
                            fontWeight: '600',
                            fontSize: '13px',
                        }}
                    >
                        ← Live Predictions
                    </Link>
                    <Link
                        to="/autoresearch-backtest"
                        style={{
                            padding: '8px 16px',
                            borderRadius: '8px',
                            background: '#f1f5f9',
                            color: '#475569',
                            textDecoration: 'none',
                            fontWeight: '600',
                            fontSize: '13px',
                        }}
                    >
                        Portfolio Backtests →
                    </Link>
                </div>
            </div>

            {/* Metrics Overview Cards */}
            <div
                style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 13rem), 1fr))',
                    gap: '16px',
                    marginBottom: '32px',
                }}
            >
                <div
                    style={{
                        padding: '20px',
                        background: '#ffffff',
                        borderRadius: '12px',
                        border: '1px solid #e2e8f0',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                    }}
                >
                    <div style={{ fontSize: '13px', color: '#64748b', fontWeight: '600' }}>
                        Backtest Directional Accuracy
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
                        {correctCount} / {totalEvaluated} correct predictions
                    </div>
                </div>

                <div
                    style={{
                        padding: '20px',
                        background: '#ffffff',
                        borderRadius: '12px',
                        border: '1px solid #e2e8f0',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
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
                        Lower is better (0.0000 = perfect calibration)
                    </div>
                </div>

                <div
                    style={{
                        padding: '20px',
                        background: '#ffffff',
                        borderRadius: '12px',
                        border: '1px solid #e2e8f0',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                    }}
                >
                    <div style={{ fontSize: '13px', color: '#64748b', fontWeight: '600' }}>
                        Backtest Runs Logged
                    </div>
                    <div
                        style={{
                            fontSize: '28px',
                            fontWeight: '700',
                            color: '#0f172a',
                            marginTop: '4px',
                        }}
                    >
                        {initialPredictions.length}
                    </div>
                    <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>
                        Model: DeepSeek Flash (`deepseek-v4-flash`)
                    </div>
                </div>

                <div
                    style={{
                        padding: '20px',
                        background: '#ffffff',
                        borderRadius: '12px',
                        border: '1px solid #e2e8f0',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                    }}
                >
                    <div style={{ fontSize: '13px', color: '#64748b', fontWeight: '600' }}>
                        Prompt Experiments
                    </div>
                    <div
                        style={{
                            fontSize: '28px',
                            fontWeight: '700',
                            color: '#4f46e5',
                            marginTop: '4px',
                        }}
                    >
                        {experiments.length}
                    </div>
                    <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>
                        Mutated strategy variants tracked
                    </div>
                </div>
            </div>

            {/* Backtest Predictions Log */}
            <div
                style={{
                    background: '#ffffff',
                    borderRadius: '12px',
                    border: '1px solid #e2e8f0',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                    padding: '24px',
                    marginBottom: '32px',
                }}
            >
                <h2
                    style={{
                        fontSize: '18px',
                        fontWeight: '700',
                        color: '#0f172a',
                        marginBottom: '16px',
                    }}
                >
                    Historical Backtest Predictions Log
                </h2>

                {initialPredictions.length === 0 ? (
                    <div style={{ padding: '32px', textAlign: 'center', color: '#64748b' }}>
                        No backtest predictions found. Run `python apps/engine/main.py
                        backtest-daily-autoresearch --weeks 1` to populate results.
                    </div>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
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
                                        borderBottom: '2px solid #f1f5f9',
                                        color: '#64748b',
                                    }}
                                >
                                    <th style={{ padding: '12px 8px' }}>Date</th>
                                    <th style={{ padding: '12px 8px' }}>Ticker</th>
                                    <th style={{ padding: '12px 8px' }}>Predicted</th>
                                    <th style={{ padding: '12px 8px' }}>Confidence</th>
                                    <th style={{ padding: '12px 8px' }}>Actual Open / Close</th>
                                    <th style={{ padding: '12px 8px' }}>Outcome</th>
                                    <th style={{ padding: '12px 8px' }}>Brier Score</th>
                                    <th style={{ padding: '12px 8px' }}>Prompt Variant</th>
                                </tr>
                            </thead>
                            <tbody>
                                {initialPredictions.map((pred) => (
                                    <PredictionTableRow key={pred.id} pred={pred} />
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Backtest Prompt Experiments Arena */}
            <div
                style={{
                    background: '#ffffff',
                    borderRadius: '12px',
                    border: '1px solid #e2e8f0',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                    padding: '24px',
                }}
            >
                <h2
                    style={{
                        fontSize: '18px',
                        fontWeight: '700',
                        color: '#0f172a',
                        marginBottom: '16px',
                    }}
                >
                    Backtest Prompt Experiments Arena
                </h2>

                {experiments.length === 0 ? (
                    <div style={{ color: '#64748b', fontSize: '14px' }}>
                        No prompt experiments recorded in backtest database.
                    </div>
                ) : (
                    <div className="flex flex-wrap gap-6 mt-4 items-start min-w-0 w-full">
                        {/* Variant List Sidebar */}
                        <div className="w-full flex-1 basis-72 min-w-0">
                            <div
                                style={{
                                    fontSize: '12px',
                                    fontWeight: '700',
                                    color: '#94a3b8',
                                    marginBottom: '8px',
                                }}
                            >
                                VARIANT LINEAGE
                            </div>
                            <div className="flex flex-col gap-2 max-h-96 overflow-y-auto pr-1 min-w-0">
                                {experiments.map((exp) => {
                                    const isSelected = exp.id === selectedExperiment?.id;
                                    return (
                                        <button
                                            type="button"
                                            key={exp.id}
                                            onClick={() => setSelectedExpId(exp.id)}
                                            className="w-full text-left cursor-pointer min-w-0"
                                            style={{
                                                padding: '12px',
                                                borderRadius: '8px',
                                                border: isSelected
                                                    ? '1px solid #6366f1'
                                                    : '1px solid #e2e8f0',
                                                background: isSelected ? '#eef2ff' : '#ffffff',
                                            }}
                                        >
                                            <div
                                                style={{
                                                    fontWeight: '700',
                                                    fontSize: '13px',
                                                    color: isSelected ? '#4338ca' : '#0f172a',
                                                    wordBreak: 'break-all',
                                                }}
                                            >
                                                {exp.variant_tag}
                                            </div>
                                            <div
                                                style={{
                                                    fontSize: '11px',
                                                    color: '#64748b',
                                                    marginTop: '4px',
                                                }}
                                            >
                                                {exp.status.toUpperCase()} •{' '}
                                                {exp.experiment_type || 'incremental'}
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>

                        {/* Variant Details */}
                        <div className="w-full flex-[3] basis-96 min-w-0 flex flex-col gap-6">
                            {selectedExperiment && (
                                <div className="min-w-0">
                                    <div
                                        style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            alignItems: 'center',
                                            marginBottom: '12px',
                                            flexWrap: 'wrap',
                                            gap: '8px',
                                            minWidth: 0,
                                        }}
                                    >
                                        <h3
                                            style={{
                                                fontSize: '16px',
                                                fontWeight: '700',
                                                color: '#0f172a',
                                                margin: 0,
                                                wordBreak: 'break-all',
                                            }}
                                        >
                                            Variant: {selectedExperiment.variant_tag}
                                        </h3>
                                        <span style={{ fontSize: '12px', color: '#64748b' }}>
                                            Created:{' '}
                                            {new Date(
                                                selectedExperiment.created_at,
                                            ).toLocaleDateString()}
                                        </span>
                                    </div>

                                    {(() => {
                                        const parentExperiment = selectedExperiment.parent_tag
                                            ? experiments.find(
                                                  (e) =>
                                                      e.variant_tag ===
                                                      selectedExperiment.parent_tag,
                                              )
                                            : null;

                                        return (
                                            <div className="space-y-6 min-w-0">
                                                {/* Cognitive Toolbox */}
                                                <CognitiveToolboxCard
                                                    selectedTools={
                                                        (
                                                            selectedExperiment.research_output as {
                                                                selected_tools?: string[];
                                                            }
                                                        )?.selected_tools ||
                                                        DEFAULT_DAILY_PREDICTOR_TOOLS
                                                    }
                                                    parentSelectedTools={
                                                        parentExperiment
                                                            ? (
                                                                  parentExperiment.research_output as {
                                                                      selected_tools?: string[];
                                                                  }
                                                              )?.selected_tools ||
                                                              DEFAULT_DAILY_PREDICTOR_TOOLS
                                                            : undefined
                                                    }
                                                    title="Daily Predictor Cognitive Toolbox"
                                                    subtitle="Contextual data feeds and analytical tools provided to the daily predictor model."
                                                />

                                                {/* Modular Reasoning Blocks */}
                                                <PromptBlocksCard
                                                    selectedBlocks={
                                                        (
                                                            selectedExperiment.research_output as {
                                                                selected_prompt_blocks?: string[];
                                                            }
                                                        )?.selected_prompt_blocks
                                                    }
                                                    parentSelectedBlocks={
                                                        parentExperiment
                                                            ? (
                                                                  parentExperiment.research_output as {
                                                                      selected_prompt_blocks?: string[];
                                                                  }
                                                              )?.selected_prompt_blocks
                                                            : undefined
                                                    }
                                                />

                                                {/* Meta-Researcher Rationale & Conviction */}
                                                <ResearchRationaleCard
                                                    experiment={selectedExperiment}
                                                />

                                                {/* Prompt Changes Diff */}
                                                <PromptChanges
                                                    experiment={selectedExperiment}
                                                    parentExperiment={parentExperiment}
                                                />

                                                {/* Segmented Prompt Inspector */}
                                                {(() => {
                                                    const { header, mutable, footer, isSplit } =
                                                        splitPromptSections(
                                                            selectedExperiment.prompt_content,
                                                        );

                                                    if (!isSplit) {
                                                        return (
                                                            <div className="p-6 bg-slate-900 text-slate-100 rounded-xl space-y-3 min-w-0">
                                                                <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
                                                                    The Predictor Prompt
                                                                </div>
                                                                <pre className="whitespace-pre-wrap break-words font-mono text-xs max-h-96 overflow-y-auto">
                                                                    {
                                                                        selectedExperiment.prompt_content
                                                                    }
                                                                </pre>
                                                            </div>
                                                        );
                                                    }

                                                    return (
                                                        <div className="space-y-4 min-w-0">
                                                            {header && (
                                                                <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-2 min-w-0">
                                                                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                                                                        Frozen System Header
                                                                    </div>
                                                                    <pre className="whitespace-pre-wrap break-words font-mono text-xs text-slate-400 max-h-48 overflow-y-auto">
                                                                        {header}
                                                                    </pre>
                                                                </div>
                                                            )}

                                                            <div className="p-4 bg-emerald-950/20 border border-emerald-500/30 rounded-xl space-y-2 min-w-0">
                                                                <div className="flex items-center justify-between">
                                                                    <div className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">
                                                                        Mutable Analytical
                                                                        Strategies
                                                                    </div>
                                                                    <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded font-mono">
                                                                        v
                                                                        {
                                                                            selectedExperiment.variant_tag
                                                                        }
                                                                    </span>
                                                                </div>
                                                                <pre className="whitespace-pre-wrap break-words font-mono text-xs text-emerald-100 max-h-96 overflow-y-auto">
                                                                    {mutable}
                                                                </pre>
                                                            </div>

                                                            {footer && (
                                                                <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-2 min-w-0">
                                                                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                                                                        Frozen Output Format &
                                                                        Schema
                                                                    </div>
                                                                    <pre className="whitespace-pre-wrap break-words font-mono text-xs text-slate-400 max-h-48 overflow-y-auto">
                                                                        {footer}
                                                                    </pre>
                                                                </div>
                                                            )}
                                                        </div>
                                                    );
                                                })()}
                                            </div>
                                        );
                                    })()}
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
