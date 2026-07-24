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
                    <div className="space-y-6">
                        <div className="flex flex-wrap items-center justify-between gap-4">
                            <div className="space-y-2">
                                <div className="flex items-center space-x-3">
                                    <span className="text-xs font-semibold uppercase tracking-widest text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-800/60 px-2.5 py-0.5 rounded-full">
                                        Simulation Sandbox
                                    </span>
                                    <span className="text-xs font-medium text-zinc-400 dark:text-zinc-500">
                                        •
                                    </span>
                                    <span className="text-xs font-mono text-zinc-500">
                                        12-Week Window
                                    </span>
                                </div>
                                <h1 className="text-4xl md:text-5xl font-black text-zinc-900 dark:text-zinc-50 tracking-tight">
                                    Backtest Auto-Research{' '}
                                    <span className="text-indigo-500">Arena</span>
                                </h1>
                            </div>
                            <Link
                                to="/autoresearch"
                                className="inline-flex items-center justify-center text-xs font-semibold text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 px-4 py-2 rounded-xl transition-all"
                            >
                                ← Switch to Live Arena
                            </Link>
                        </div>
                        <p className="text-zinc-500 dark:text-zinc-400 text-lg max-w-2xl leading-relaxed">
                            Audit the performance of backtested prompts. Trace mutations, weekly
                            scores, and meta-researcher hypotheses generated inside our
                            point-in-time temporal sandbox.
                        </p>
                    </div>
                </PageLayout>
            </div>

            <PageLayout className="py-12 space-y-12">
                {/* Score Formula Reference Card */}
                <div className="bg-gradient-to-br from-indigo-50/50 to-purple-50/30 dark:from-indigo-950/20 dark:to-purple-950/10 border border-indigo-100 dark:border-indigo-950/40 rounded-3xl p-6">
                    <ScoreCalculation />
                </div>

                <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
                    {/* Sidebar: List of Backtest Experiments */}
                    <div className="xl:col-span-4 space-y-6">
                        <div className="flex items-center justify-between px-2">
                            <SectionHeading>Simulation Runs</SectionHeading>
                            <span className="text-xs font-medium text-zinc-400 uppercase tracking-widest bg-zinc-100 dark:bg-zinc-800 px-2 py-0.5 rounded">
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
                            <div className="h-full flex items-center justify-center p-12 border-2 border-dashed border-zinc-200 dark:border-zinc-800 rounded-3xl text-zinc-400">
                                Select a backtest run to view prompt details and mutation reasoning
                            </div>
                        )}
                    </div>
                </div>
            </PageLayout>
        </div>
    );
}
