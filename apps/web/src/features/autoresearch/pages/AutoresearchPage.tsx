import type { PromptExperiment } from '@llm-market-bench/database';
import { PageLayout, SectionHeading } from '@llm-market-bench/ui-design-system';
import { useSuspenseQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { useState } from 'react';
import { ExperimentDetails } from '../components/ExperimentDetails';
import { ExperimentList } from '../components/ExperimentList';
import { ScoreCalculation } from '../components/ScoreCalculation';
import { TrackTabs } from '../components/TrackTabs';
import { autoresearchQueries } from '../queries/options';

interface AutoresearchPageProps {
    initialData: PromptExperiment[];
    fetchFn: () => Promise<PromptExperiment[]>;
}

export function AutoresearchPage({ initialData, fetchFn }: AutoresearchPageProps) {
    const { data: experiments } = useSuspenseQuery({
        ...autoresearchQueries.experiments({ fetchFn }),
        initialData,
    });

    const [activeTrack, setActiveTrack] = useState<string>('track_default');

    const filteredExperiments = experiments.filter(
        (exp) => (exp.track_id || 'track_default') === activeTrack,
    );

    const [selectedExperiment, setSelectedExperiment] = useState<PromptExperiment | null>(
        filteredExperiments.length > 0 ? filteredExperiments[0] : null,
    );

    const handleSelectTrack = (trackId: string) => {
        setActiveTrack(trackId);
        const trackExps = experiments.filter(
            (exp) => (exp.track_id || 'track_default') === trackId,
        );
        setSelectedExperiment(trackExps.length > 0 ? trackExps[0] : null);
    };

    return (
        <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
            <div className="bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800 py-12">
                <PageLayout>
                    <div className="flex flex-col gap-2">
                        <div className="flex flex-wrap items-center justify-between gap-4">
                            <h1 className="text-lg font-bold text-boxel-ink tracking-tight uppercase">
                                Auto-Research <span className="text-accent">Arena</span>
                            </h1>
                            <Link
                                to="/autoresearch-backtest"
                                className="voxel-btn inline-flex items-center justify-center text-sm font-bold text-boxel-ink bg-boxel-surface hover:bg-boxel-elevated border border-boxel-bevel-hi px-4 py-2 rounded-none transition-all"
                            >
                                Switch to Backtest Arena →
                            </Link>
                        </div>
                        <p className="text-boxel-muted text-xs font-normal max-w-2xl leading-relaxed">
                            Track the evolution of our autonomous trading prompts. Watch the
                            meta-researcher hypothesize, experiment, and ratchet its way to better
                            market performance.
                        </p>
                    </div>
                </PageLayout>
            </div>

            <PageLayout className="py-12 space-y-12">
                <ScoreCalculation />

                <TrackTabs
                    experiments={experiments}
                    activeTrack={activeTrack}
                    onSelectTrack={handleSelectTrack}
                />

                <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
                    {/* Sidebar: List of Experiments */}
                    <div className="xl:col-span-4 space-y-6">
                        <div className="flex items-center justify-between px-2">
                            <SectionHeading>History</SectionHeading>
                            <span className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                                {filteredExperiments.length} Experiments
                            </span>
                        </div>
                        <ExperimentList
                            experiments={filteredExperiments}
                            onSelect={setSelectedExperiment}
                            selectedId={selectedExperiment?.id}
                        />
                    </div>

                    {/* Main: Details */}
                    <div className="xl:col-span-8 space-y-6">
                        {selectedExperiment ? (
                            <div className="space-y-6">
                                <div className="flex items-center space-x-4 px-2">
                                    <SectionHeading>Experiment Details</SectionHeading>
                                    <div className="h-px flex-1 bg-zinc-200 dark:bg-zinc-800" />
                                    <span className="text-sm font-mono text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded">
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
                                Select an experiment to view details
                            </div>
                        )}
                    </div>
                </div>
            </PageLayout>
        </div>
    );
}
