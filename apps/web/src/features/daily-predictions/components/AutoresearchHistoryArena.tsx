import type { PromptExperiment } from '@llm-market-bench/database';
import { Badge } from '@llm-market-bench/ui-design-system';
import { CognitiveToolboxCard } from '../../autoresearch/components/CognitiveToolboxCard';
import { PromptBlocksCard } from '../../autoresearch/components/PromptBlocksCard';
import { PromptChanges } from '../../autoresearch/components/PromptChanges';
import { ResearchRationaleCard } from '../../autoresearch/components/ResearchRationaleCard';
import { isExperimentColdStart } from '../../autoresearch/utils/coldStart';
import type { DailyPrediction } from '../api/fetch-daily-predictions';
import {
    DEFAULT_DAILY_PREDICTOR_TOOLS,
    getSidebarStatusBadge,
} from '../utils/daily-predictions-helpers';
import { DailyLessonsLedgerCard } from './DailyLessonsLedgerCard';
import { DailyScoreBreakdown } from './DailyScoreBreakdown';
import { SegmentedPromptInspector } from './SegmentedPromptInspector';
import { VariantSidebar } from './VariantSidebar';

export interface SelectedVariantHeaderProps {
    experiment: PromptExperiment;
    isActiveVariant: boolean;
}

export function SelectedVariantHeader({ experiment, isActiveVariant }: SelectedVariantHeaderProps) {
    const statusBadge = getSidebarStatusBadge(experiment.status, isActiveVariant);

    return (
        <div className="min-w-0">
            <div className="flex items-center justify-between flex-wrap gap-2 mb-2 min-w-0">
                <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 m-0 break-all">
                    {experiment.variant_tag}
                </h3>
                <div className="flex gap-2 items-center">
                    {isExperimentColdStart(experiment) && (
                        <Badge colorScheme="warning" variant="soft" size="xs">
                            From 0
                        </Badge>
                    )}
                    {isActiveVariant && (
                        <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400">
                            🟢 CURRENT ACTIVE
                        </span>
                    )}
                    <Badge colorScheme={statusBadge.colorScheme} variant="soft" size="xs">
                        {statusBadge.label}
                    </Badge>
                </div>
            </div>

            <div className="flex gap-4 text-xs text-zinc-500 dark:text-zinc-400 flex-wrap mt-2 min-w-0">
                <div>
                    <strong>Score:</strong>{' '}
                    {experiment.metrics?.score !== undefined
                        ? Number(experiment.metrics.score).toFixed(2)
                        : 'Pending'}
                </div>
                {experiment.parent_tag && (
                    <div className="break-all">
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

export interface AutoresearchHistoryArenaProps {
    experiments: PromptExperiment[];
    predictions?: DailyPrediction[];
    selectedExpId: string | null;
    activePromptTag?: string | null;
    onSelectExp: (id: string) => void;
}

export function AutoresearchHistoryArena({
    experiments,
    predictions,
    selectedExpId,
    activePromptTag,
    onSelectExp,
}: AutoresearchHistoryArenaProps) {
    const selectedExperiment =
        experiments.find((e) => e.id === selectedExpId) ||
        experiments.find((e) => e.variant_tag === activePromptTag) ||
        experiments[0] ||
        null;

    const parentExperiment = selectedExperiment?.parent_tag
        ? experiments.find((e) => e.variant_tag === selectedExperiment.parent_tag)
        : null;

    if (experiments.length === 0) {
        return (
            <div className="p-8 text-center text-zinc-500 dark:text-zinc-400 bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800">
                No prompt experiments or autoresearch runs recorded for this model track yet. Runs
                execute weekly (Sun 6:00 PM ET / 10:00 PM UTC).
            </div>
        );
    }

    return (
        <div className="p-5 min-w-0 w-full overflow-hidden bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 shadow-sm">
            <div
                style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    gap: '12px',
                    marginBottom: '16px',
                }}
            >
                <h2 className="text-lg font-bold text-zinc-900 dark:text-zinc-100 m-0">
                    Autoresearch Prompt Lineage & Benchmarks
                </h2>
                {activePromptTag && (
                    <div className="inline-flex items-center gap-1.5 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 px-3 py-1 rounded-full text-xs text-emerald-700 dark:text-emerald-400 font-semibold">
                        <span>🟢 Active Runtime:</span>
                        <code className="font-mono font-bold">{activePromptTag}</code>
                    </div>
                )}
            </div>

            <div className="flex flex-wrap gap-6 mt-4 items-start min-w-0 w-full">
                {/* Variant List Sidebar */}
                <VariantSidebar
                    experiments={experiments}
                    selectedExpId={selectedExperiment?.id ?? null}
                    activePromptTag={activePromptTag}
                    onSelectExp={onSelectExp}
                />

                {/* Variant Details & Prompt Inspector */}
                {selectedExperiment && (
                    <div className="w-full flex-[3] basis-96 min-w-0 flex flex-col gap-4">
                        <SelectedVariantHeader
                            experiment={selectedExperiment}
                            isActiveVariant={selectedExperiment.variant_tag === activePromptTag}
                        />

                        {/* Interactive Score Calculation & Breakdown */}
                        <DailyScoreBreakdown
                            experiment={selectedExperiment}
                            predictions={predictions}
                        />

                        {/* Cognitive Toolbox Configuration */}
                        <CognitiveToolboxCard
                            selectedTools={
                                (
                                    selectedExperiment.research_output as {
                                        selected_tools?: string[];
                                    }
                                )?.selected_tools || DEFAULT_DAILY_PREDICTOR_TOOLS
                            }
                            parentSelectedTools={
                                parentExperiment
                                    ? (
                                          parentExperiment.research_output as {
                                              selected_tools?: string[];
                                          }
                                      )?.selected_tools || DEFAULT_DAILY_PREDICTOR_TOOLS
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
                        <ResearchRationaleCard experiment={selectedExperiment} />

                        {/* Daily Causal Lessons & Post-Mortems Feeding Prompt Evolution */}
                        <DailyLessonsLedgerCard predictions={predictions} />

                        {/* Prompt Evolution / Diff vs Parent */}
                        <PromptChanges
                            experiment={selectedExperiment}
                            parentExperiment={parentExperiment}
                        />

                        {/* Segmented Prompt Inspector */}
                        <SegmentedPromptInspector
                            promptContent={selectedExperiment.prompt_content}
                        />
                    </div>
                )}
            </div>
        </div>
    );
}
