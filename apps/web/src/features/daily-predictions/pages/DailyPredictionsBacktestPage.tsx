import type { PromptExperiment } from '@llm-market-bench/database';
import {
    Badge,
    Card,
    SectionHeading,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { useState } from 'react';
import { formatEasternShortDateWithYear } from '~/utils/date';
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
        <TableRow>
            <TableCell className="font-bold text-boxel-ink">
                {pred.target_date || pred.prediction_date}
            </TableCell>
            <TableCell className="font-bold font-mono text-boxel-ink">{pred.ticker}</TableCell>
            <TableCell>
                <Badge colorScheme={isUp ? 'success' : 'danger'} variant="soft" size="xs">
                    {pred.predicted_direction}
                </Badge>
            </TableCell>
            <TableCell className="font-bold font-mono text-boxel-ink">{pred.confidence}%</TableCell>
            <TableCell className="font-mono text-boxel-muted">
                {pred.open_price !== null && pred.close_price !== null ? (
                    <span>
                        ${pred.open_price.toFixed(2)} → ${pred.close_price.toFixed(2)}
                    </span>
                ) : (
                    'Pending'
                )}
            </TableCell>
            <TableCell>
                {pred.status === 'evaluated' ? (
                    <span className={`font-bold ${isCorrect ? 'text-success' : 'text-danger'}`}>
                        {isCorrect ? '✓ Correct' : '✗ Incorrect'}
                    </span>
                ) : (
                    <span className="text-boxel-muted">Pending</span>
                )}
            </TableCell>
            <TableCell className="font-mono text-boxel-muted">
                {pred.brier_score !== null ? pred.brier_score.toFixed(4) : '-'}
            </TableCell>
            <TableCell className="text-boxel-muted">
                <code className="text-accent">{pred.prompt_variant_tag || 'baseline'}</code>
            </TableCell>
        </TableRow>
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
        <div className="w-full max-w-7xl mx-auto p-6 font-sans flex flex-col gap-6 min-w-0">
            {/* Header */}
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-3 flex-wrap">
                        <SectionHeading>S&P Daily Predictor Backtest Arena</SectionHeading>
                        <Badge colorScheme="accent" variant="soft">
                            DeepSeek Flash Sandbox
                        </Badge>
                    </div>
                    <p className="text-xs font-normal text-boxel-muted">
                        Temporal sandbox audit of S&P 500 (SPY) daily open-to-close predictions and
                        weekly prompt mutations.
                    </p>
                </div>

                <div className="flex gap-2 flex-wrap">
                    <Link
                        to="/daily-predictions"
                        className="voxel-btn bg-boxel-surface text-boxel-ink px-4 py-2 text-sm font-bold no-underline hover:text-accent transition-colors"
                    >
                        ← Live Predictions
                    </Link>
                    <Link
                        to="/autoresearch-backtest"
                        className="voxel-btn bg-boxel-surface text-boxel-ink px-4 py-2 text-sm font-bold no-underline hover:text-accent transition-colors"
                    >
                        Portfolio Backtests →
                    </Link>
                </div>
            </div>

            {/* Metrics Overview Cards */}
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,13rem),1fr))] gap-4 items-stretch min-w-0">
                <Card className="p-5 flex flex-col justify-between gap-2 h-full rounded-none">
                    <div className="text-sm font-bold uppercase tracking-wider text-boxel-muted">
                        Backtest Directional Accuracy
                    </div>
                    <div className="text-lg font-bold font-mono text-boxel-ink tabular-nums">
                        {accuracyPct}%
                    </div>
                    <div className="text-xs font-normal text-boxel-muted">
                        {correctCount} / {totalEvaluated} correct predictions
                    </div>
                </Card>

                <Card className="p-5 flex flex-col justify-between gap-2 h-full rounded-none">
                    <div className="text-sm font-bold uppercase tracking-wider text-boxel-muted">
                        Brier Calibration Score
                    </div>
                    <div className="text-lg font-bold font-mono text-boxel-ink tabular-nums">
                        {avgBrier}
                    </div>
                    <div className="text-xs font-normal text-boxel-muted">
                        Lower is better (0.0000 = perfect calibration)
                    </div>
                </Card>

                <Card className="p-5 flex flex-col justify-between gap-2 h-full rounded-none">
                    <div className="text-sm font-bold uppercase tracking-wider text-boxel-muted">
                        Backtest Runs Logged
                    </div>
                    <div className="text-lg font-bold font-mono text-boxel-ink tabular-nums">
                        {initialPredictions.length}
                    </div>
                    <div className="text-xs font-normal text-boxel-muted">
                        Model: DeepSeek Flash (`deepseek-v4-flash`)
                    </div>
                </Card>

                <Card className="p-5 flex flex-col justify-between gap-2 h-full rounded-none">
                    <div className="text-sm font-bold uppercase tracking-wider text-boxel-muted">
                        Prompt Experiments
                    </div>
                    <div className="text-lg font-bold font-mono text-accent tabular-nums">
                        {experiments.length}
                    </div>
                    <div className="text-xs font-normal text-boxel-muted">
                        Mutated strategy variants tracked
                    </div>
                </Card>
            </div>

            {/* Backtest Predictions Log */}
            <Card className="p-6 flex flex-col gap-4 rounded-none min-w-0">
                <div className="text-sm font-bold text-boxel-ink uppercase tracking-wider">
                    Historical Backtest Predictions Log
                </div>

                {initialPredictions.length === 0 ? (
                    <div className="voxel-trough p-6 text-center text-xs font-normal text-boxel-muted">
                        No backtest predictions found. Run `python apps/engine/main.py
                        backtest-daily-autoresearch --weeks 1` to populate results.
                    </div>
                ) : (
                    <div className="overflow-x-auto min-w-0">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Date</TableHead>
                                    <TableHead>Ticker</TableHead>
                                    <TableHead>Predicted</TableHead>
                                    <TableHead>Confidence</TableHead>
                                    <TableHead>Actual Open / Close</TableHead>
                                    <TableHead>Outcome</TableHead>
                                    <TableHead>Brier Score</TableHead>
                                    <TableHead>Prompt Variant</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {initialPredictions.map((pred) => (
                                    <PredictionTableRow key={pred.id} pred={pred} />
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                )}
            </Card>

            {/* Backtest Prompt Experiments Arena */}
            <Card className="p-6 flex flex-col gap-4 rounded-none min-w-0">
                <div className="text-sm font-bold text-boxel-ink uppercase tracking-wider">
                    Backtest Prompt Experiments Arena
                </div>

                {experiments.length === 0 ? (
                    <div className="voxel-trough p-6 text-center text-xs font-normal text-boxel-muted">
                        No prompt experiments recorded in backtest database.
                    </div>
                ) : (
                    <div className="flex flex-wrap gap-6 items-start min-w-0 w-full">
                        {/* Variant List Sidebar */}
                        <div className="w-full flex-1 basis-72 min-w-0 flex flex-col gap-2">
                            <div className="text-xs font-bold uppercase tracking-wider text-boxel-muted">
                                Variant Lineage
                            </div>
                            <div className="flex flex-col gap-2 max-h-96 overflow-y-auto pr-1 min-w-0">
                                {experiments.map((exp) => {
                                    const isSelected = exp.id === selectedExperiment?.id;
                                    return (
                                        <button
                                            type="button"
                                            key={exp.id}
                                            onClick={() => setSelectedExpId(exp.id)}
                                            className={`w-full text-left cursor-pointer min-w-0 p-3 rounded-none transition-colors border-2 ${
                                                isSelected
                                                    ? 'voxel-card bg-boxel-elevated border-accent text-accent'
                                                    : 'voxel-trough border-boxel-bevel-hi text-boxel-ink hover:bg-boxel-surface'
                                            }`}
                                        >
                                            <div className="text-sm font-bold break-all">
                                                {exp.variant_tag}
                                            </div>
                                            <div className="text-xs font-normal text-boxel-muted mt-1">
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
                                <div className="min-w-0 flex flex-col gap-4">
                                    <div className="flex justify-between items-center flex-wrap gap-2 min-w-0">
                                        <h3 className="text-sm font-bold text-boxel-ink break-all m-0">
                                            Variant: {selectedExperiment.variant_tag}
                                        </h3>
                                        <span className="text-xs font-normal text-boxel-muted">
                                            Created:{' '}
                                            {formatEasternShortDateWithYear(
                                                selectedExperiment.created_at,
                                            )}
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
                                            <div className="flex flex-col gap-6 min-w-0">
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
                                                            <div className="p-4 voxel-trough rounded-none flex flex-col gap-2 min-w-0">
                                                                <div className="text-xs font-bold uppercase tracking-wider text-boxel-muted">
                                                                    The Predictor Prompt
                                                                </div>
                                                                <pre className="whitespace-pre-wrap break-words font-mono text-xs max-h-96 overflow-y-auto m-0 text-boxel-ink">
                                                                    {
                                                                        selectedExperiment.prompt_content
                                                                    }
                                                                </pre>
                                                            </div>
                                                        );
                                                    }

                                                    return (
                                                        <div className="flex flex-col gap-4 min-w-0">
                                                            {header && (
                                                                <div className="p-4 voxel-trough rounded-none flex flex-col gap-2 min-w-0">
                                                                    <div className="text-xs font-bold text-boxel-muted uppercase tracking-wider">
                                                                        Frozen System Header
                                                                    </div>
                                                                    <pre className="whitespace-pre-wrap break-words font-mono text-xs text-boxel-muted max-h-48 overflow-y-auto m-0">
                                                                        {header}
                                                                    </pre>
                                                                </div>
                                                            )}

                                                            <div className="p-4 voxel-card rounded-none flex flex-col gap-2 min-w-0 border-l-4 border-l-success">
                                                                <div className="flex items-center justify-between">
                                                                    <div className="text-xs font-bold text-success uppercase tracking-wider">
                                                                        Mutable Analytical
                                                                        Strategies
                                                                    </div>
                                                                    <span className="text-xs text-success px-2 py-0.5 rounded-none font-mono font-bold voxel-trough">
                                                                        v
                                                                        {
                                                                            selectedExperiment.variant_tag
                                                                        }
                                                                    </span>
                                                                </div>
                                                                <pre className="whitespace-pre-wrap break-words font-mono text-xs text-boxel-ink max-h-96 overflow-y-auto m-0">
                                                                    {mutable}
                                                                </pre>
                                                            </div>

                                                            {footer && (
                                                                <div className="p-4 voxel-trough rounded-none flex flex-col gap-2 min-w-0">
                                                                    <div className="text-xs font-bold text-boxel-muted uppercase tracking-wider">
                                                                        Frozen Output Format &
                                                                        Schema
                                                                    </div>
                                                                    <pre className="whitespace-pre-wrap break-words font-mono text-xs text-boxel-muted max-h-48 overflow-y-auto m-0">
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
            </Card>
        </div>
    );
}
