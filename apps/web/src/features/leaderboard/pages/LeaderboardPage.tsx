import type { LLMLeaderboardRow } from '@llm-market-bench/database';
import { PageLayout, SectionHeading } from '@llm-market-bench/ui-design-system';
import { useQuery } from '@tanstack/react-query';
import { createServerFn } from '@tanstack/react-start';
import { useState } from 'react';
import { fetchLeaderboard } from '../api/fetch-leaderboard';
import { LeaderboardPodium } from '../components/LeaderboardPodium';
import { LeaderboardTable } from '../components/LeaderboardTable';
import { ModelComparison } from '../components/ModelComparison';

const getLeaderboardFn = createServerFn({ method: 'GET' })
    .inputValidator((d: number | null) => d)
    .handler(async ({ data: timeframe }: { data: number | null }) => {
        return fetchLeaderboard(timeframe);
    });

interface LeaderboardPageProps {
    initialData: LLMLeaderboardRow[];
}

export function LeaderboardPage({ initialData }: LeaderboardPageProps) {
    const [timeframe, setTimeframe] = useState<number | null>(30);
    const [selectedModels, setSelectedModels] = useState<string[]>([]);

    const {
        data: models = [],
        isLoading,
        isFetching,
    } = useQuery<LLMLeaderboardRow[]>({
        queryKey: ['leaderboard', timeframe],
        queryFn: () => getLeaderboardFn({ data: timeframe }),
        initialData: timeframe === 30 ? initialData : undefined,
        refetchOnWindowFocus: false,
    });

    const handleToggleSelectModel = (modelName: string) => {
        setSelectedModels((prev) => {
            if (prev.includes(modelName)) {
                return prev.filter((m) => m !== modelName);
            }
            if (prev.length >= 2) {
                return prev;
            }
            return [...prev, modelName];
        });
    };

    const handleClearComparison = () => {
        setSelectedModels([]);
    };

    // Find selected models in the list
    const modelA = models.find((m: LLMLeaderboardRow) => m.model_name === selectedModels[0]);
    const modelB = models.find((m: LLMLeaderboardRow) => m.model_name === selectedModels[1]);

    const timeframes = [
        { label: '7 Days', value: 7 },
        { label: '30 Days', value: 30 },
        { label: '90 Days', value: 90 },
        { label: 'All-Time', value: null },
    ];

    return (
        <PageLayout>
            <div className="space-y-8 animate-in fade-in duration-500">
                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                    <div>
                        <SectionHeading gradient="ai">LLM Leaderboard</SectionHeading>
                        <p className="text-zinc-500 dark:text-zinc-400 text-lg leading-relaxed mt-2">
                            Rankings and diagnostics evaluating trading performance, reasoning
                            quality, and consistency.
                        </p>
                    </div>

                    {/* Timeframe selector */}
                    <div className="flex bg-white/5 p-1 rounded-2xl border border-white/10 shrink-0 self-start md:self-auto">
                        {timeframes.map((tf) => (
                            <button
                                key={tf.label}
                                type="button"
                                onClick={() => setTimeframe(tf.value)}
                                className={`px-4 py-1.5 text-xs font-mono font-bold rounded-xl transition-all ${
                                    timeframe === tf.value
                                        ? 'bg-accent text-zinc-950 shadow-[0_0_12px_rgba(56,189,248,0.3)]'
                                        : 'text-zinc-400 hover:text-white'
                                }`}
                            >
                                {tf.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Loading state indicator */}
                {isLoading ? (
                    <div className="flex flex-col items-center justify-center py-20 space-y-4">
                        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-accent" />
                        <p className="text-sm text-zinc-500 font-mono">
                            Aggregating engine metrics...
                        </p>
                    </div>
                ) : (
                    <>
                        {/* Podium Section (Top 3) */}
                        {models.length > 0 && <LeaderboardPodium models={models} />}

                        {/* Leaderboard Grid / Table */}
                        <div className="space-y-4">
                            <div className="flex justify-between items-center">
                                <h2 className="font-heading text-lg font-bold text-zinc-100 uppercase tracking-wider">
                                    All Running Models{' '}
                                    {isFetching && (
                                        <span className="text-xs text-zinc-500 font-mono normal-case">
                                            (updating...)
                                        </span>
                                    )}
                                </h2>
                            </div>
                            <LeaderboardTable
                                models={models}
                                selectedModels={selectedModels}
                                onToggleSelectModel={handleToggleSelectModel}
                            />
                        </div>

                        {/* Model Comparison Side-by-Side */}
                        {modelA && modelB && (
                            <div className="mt-12 pt-12 border-t border-white/10">
                                <ModelComparison
                                    modelA={modelA}
                                    modelB={modelB}
                                    onClear={handleClearComparison}
                                />
                            </div>
                        )}
                    </>
                )}
            </div>
        </PageLayout>
    );
}
export default LeaderboardPage;
