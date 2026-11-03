import type { PromptExperiment } from '@llm-market-bench/database';
import { PageLayout, SectionHeading } from '@llm-market-bench/ui-design-system';
import { useSuspenseQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { useState } from 'react';
import { ExperimentDetails } from '../components/ExperimentDetails';
import { ExperimentList } from '../components/ExperimentList';
import { ScoreCalculation } from '../components/ScoreCalculation';
import { autoresearchQueries } from '../queries/options';

interface BacktestAutoresearchPageProps {
    initialData: PromptExperiment[];
    fetchFn: () => Promise<PromptExperiment[]>;
}

export function BacktestAutoresearchPage({ initialData, fetchFn }: BacktestAutoresearchPageProps) {
    const { data: experiments } = useSuspenseQuery({
        ...autoresearchQueries.backtest({ fetchFn }),
        initialData,
    });

    const [selectedExperiment, setSelectedExperiment] = useState<PromptExperiment | null>(
        experiments.length > 0 ? experiments[0] : null,
    );

    return (
        <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
            {/* Page Header */}
            <div className="bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800 py-12">
                <PageLayout>
                    <div className="flex flex-col gap-4">
                        <div className="flex flex-wrap items-center justify-between gap-4">
                            <div className="flex flex-col gap-1">
                                <div className="flex items-center gap-2">
                                    <span className="text-xs font-normal uppercase tracking-widest text-accent bg-boxel-trough border border-boxel-bevel-hi px-2.5 py-0.5 rounded-none">
                                        Simulation Sandbox
                                    </span>
                                    <span className="text-xs font-normal text-boxel-muted">•</span>
                                    <span className="text-xs font-mono font-normal text-boxel-muted">
                                        12-Week Window
                                    </span>
                                </div>
                                <h1 className="text-lg font-bold text-boxel-ink tracking-tight uppercase">
                                    Backtest Auto-Research{' '}
                                    <span className="text-accent">Arena</span>
                                </h1>
                            </div>
                            <Link
                                to="/autoresearch"
                                className="voxel-btn inline-flex items-center justify-center text-sm font-bold text-boxel-ink bg-boxel-surface hover:bg-boxel-elevated border border-boxel-bevel-hi px-4 py-2 rounded-none transition-all"
                            >
                                ← Switch to Live Arena
                            </Link>
                        </div>
                        <p className="text-boxel-muted text-xs font-normal max-w-2xl leading-relaxed">
                            Audit the performance of backtested prompts. Trace mutations, weekly
                            scores, and meta-researcher hypotheses generated inside our
                            point-in-time temporal sandbox.
                        </p>
                    </div>
                </PageLayout>
            </div>

            <PageLayout className="py-12 space-y-12">
                {/* Score Formula Reference Card */}
                <div className="bg-boxel-surface border border-boxel-bevel-hi rounded-none p-6">
                    <ScoreCalculation />
                </div>

                <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
                    {/* Sidebar: List of Backtest Experiments */}
                    <div className="xl:col-span-4 space-y-6">
                        <div className="flex items-center justify-between px-2">
                            <SectionHeading>Simulation Runs</SectionHeading>
                            <span className="text-xs font-normal text-boxel-muted uppercase tracking-widest bg-boxel-trough border border-boxel-bevel-hi px-2 py-0.5 rounded-none">
                                {experiments.length} Runs
                            </span>
                        </div>
                        <ExperimentList
                            experiments={experiments}
                            onSelect={setSelectedExperiment}
                            selectedId={selectedExperiment?.id}
                        />
                    </div>

                    {/* Main Details Panel */}
                    <div className="xl:col-span-8 space-y-6">
                        {selectedExperiment ? (
                            <div className="space-y-6">
                                <div className="flex items-center space-x-4 px-2">
                                    <SectionHeading>Run Details</SectionHeading>
                                    <div className="h-px flex-1 bg-zinc-200 dark:bg-zinc-800" />
                                    <span className="text-sm font-mono text-indigo-500 bg-indigo-500/10 px-2.5 py-0.5 rounded border border-indigo-500/20">
                                        {selectedExperiment.variant_tag}
                                    </span>
                                </div>
                                <ExperimentDetails
                                    experiment={selectedExperiment}
                                    parentExperiment={
                                        selectedExperiment.parent_tag
                                            ? experiments.find(
                                                  (e) =>
                                                      e.variant_tag ===
                                                      selectedExperiment.parent_tag,
                                              )
                                            : null
                                    }
                                />
                            </div>
                        ) : (
                            <div className="h-full flex items-center justify-center p-12 border-2 border-dashed border-zinc-200 dark:border-zinc-800 rounded-none text-xs font-normal text-zinc-400">
                                Select a backtest run to view prompt details and mutation reasoning
                            </div>
                        )}
                    </div>
                </div>
            </PageLayout>
        </div>
    );
}
