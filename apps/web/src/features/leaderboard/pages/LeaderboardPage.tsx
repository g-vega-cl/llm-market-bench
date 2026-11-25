import type { LeaderboardPagePayload, LLMLeaderboardRow } from '@llm-market-bench/database';
import {
    type AtmospherePhase,
    Button,
    Card,
    PageLayout,
    SceneStage,
    Skeleton,
} from '@llm-market-bench/ui-design-system';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { createServerFn } from '@tanstack/react-start';
import { useState } from 'react';
import { CedarRidgeBackdrop } from '~/features/home/backdrop/CedarRidgeBackdrop';
import { SceneHudControls } from '~/features/home/backdrop/SceneHudControls';
import { useDioramaStage } from '~/features/home/backdrop/useDioramaStage';
import {
    type FetchLeaderboardPageParams,
    fetchLeaderboardPage,
    type LeaderboardCategory,
    type LeaderboardSortDir,
    type LeaderboardSortField,
} from '../api/fetch-leaderboard';
import { LeaderboardPodium } from '../components/LeaderboardPodium';
import { LEADERBOARD_PAGE_SIZE, LeaderboardTable } from '../components/LeaderboardTable';
import { ModelComparison } from '../components/ModelComparison';

const getLeaderboardPageFn = createServerFn({ method: 'GET' })
    .validator((d: FetchLeaderboardPageParams) => d)
    .handler(async ({ data }: { data: FetchLeaderboardPageParams }) => {
        return fetchLeaderboardPage(data);
    });

interface LeaderboardPageProps {
    initialData: LeaderboardPagePayload;
    initialAtmosphere?: AtmospherePhase;
}

export function LeaderboardPage({ initialData, initialAtmosphere }: LeaderboardPageProps) {
    const [timeframe, setTimeframe] = useState<number | null>(30);
    const [category, setCategory] = useState<LeaderboardCategory>('all');
    const [sortField, setSortField] = useState<LeaderboardSortField>('composite_score');
    const [sortOrder, setSortOrder] = useState<LeaderboardSortDir>('desc');
    const [currentPage, setCurrentPage] = useState<number>(1);
    const [selectedEntries, setSelectedEntries] = useState<LLMLeaderboardRow[]>([]);

    const { atmosphere, motion, cycleAtmosphere, toggleMotion } =
        useDioramaStage(initialAtmosphere);

    const isDefaultQuery =
        timeframe === 30 &&
        category === 'all' &&
        sortField === 'composite_score' &&
        sortOrder === 'desc' &&
        currentPage === 1;

    const { data, isLoading, isFetching } = useQuery<LeaderboardPagePayload>({
        queryKey: ['leaderboard', timeframe, category, sortField, sortOrder, currentPage],
        queryFn: () =>
            getLeaderboardPageFn({
                data: {
                    timeWindowDays: timeframe,
                    category,
                    sortBy: sortField,
                    sortDir: sortOrder,
                    page: currentPage,
                    pageSize: LEADERBOARD_PAGE_SIZE,
                },
            }),
        initialData: isDefaultQuery ? initialData : undefined,
        staleTime: 60_000,
        refetchOnWindowFocus: false,
        placeholderData: keepPreviousData,
    });

    const pageData = data ?? initialData;
    const rows = pageData.rows;
    const podium = pageData.podium;
    const counts = pageData.counts;
    const totalCount = pageData.totalCount;

    const selectedIds = selectedEntries.map((m) => m.model_name);

    const handleToggleSelectModel = (modelName: string) => {
        setSelectedEntries((prev) => {
            if (prev.some((m) => m.model_name === modelName)) {
                return prev.filter((m) => m.model_name !== modelName);
            }
            if (prev.length >= 2) {
                return prev;
            }
            const match =
                rows.find((m) => m.model_name === modelName) ??
                podium.find((m) => m.model_name === modelName);
            return match ? [...prev, match] : prev;
        });
    };

    const handleClearComparison = () => {
        setSelectedEntries([]);
    };

    const handleSortChange = (field: LeaderboardSortField) => {
        if (sortField === field) {
            setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'));
        } else {
            setSortField(field);
            setSortOrder('desc');
        }
        setCurrentPage(1);
    };

    const handleTimeframeChange = (nextTimeframe: number | null) => {
        setTimeframe(nextTimeframe);
        setCurrentPage(1);
        setSelectedEntries([]);
    };

    const categoryTabs: { id: LeaderboardCategory; label: string; count: number }[] = [
        { id: 'all', label: 'All', count: counts.all },
        { id: 'llm', label: 'LLMs', count: counts.llm },
        { id: 'system', label: 'System', count: counts.system },
        { id: 'user_bot', label: 'User Bots', count: counts.user_bot },
    ];

    const modelA = selectedEntries[0]
        ? (rows.find((m) => m.model_name === selectedEntries[0].model_name) ?? selectedEntries[0])
        : undefined;
    const modelB = selectedEntries[1]
        ? (rows.find((m) => m.model_name === selectedEntries[1].model_name) ?? selectedEntries[1])
        : undefined;

    const timeframes = [
        { label: '7 Days', value: 7 },
        { label: '30 Days', value: 30 },
        { label: '90 Days', value: 90 },
        { label: 'All-Time', value: null },
    ];

    return (
        <div className="min-h-screen bg-voxel-canvas text-voxel-ink flex flex-col">
            <SceneStage
                variant="hero"
                backdropMode="page"
                atmosphere={atmosphere}
                motionRole="reactive"
                aria-label="Leaderboard header"
                backdrop={
                    <CedarRidgeBackdrop
                        atmosphere={atmosphere}
                        motion={motion}
                        className="h-full w-full"
                    />
                }
            >
                <Card variant="default" padding="md" className="scene-scrim flex flex-col gap-4">
                    <div className="flex flex-wrap items-start justify-between gap-4 min-w-0">
                        <div className="flex flex-col gap-1 min-w-0 flex-1 basis-72">
                            <h1 className="text-lg font-bold text-voxel-ink">Leaderboard</h1>
                            <p className="text-xs font-normal text-voxel-muted leading-relaxed">
                                Unified rankings across LLMs, systematic portfolios, and public user
                                bots — scored on return, win rate, and daily return consistency.
                            </p>
                        </div>

                        <div className="flex flex-wrap items-center gap-2">
                            <SceneHudControls
                                atmosphere={atmosphere}
                                motion={motion}
                                onCycleAtmosphere={cycleAtmosphere}
                                onTogglePaused={toggleMotion}
                            />
                        </div>
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-4 pt-3 border-t border-voxel-bevel-hi">
                        {/* Category Filter Tabs */}
                        <div className="voxel-trough flex flex-wrap items-center gap-1 p-1 rounded-none">
                            {categoryTabs.map((tab) => (
                                <Button
                                    key={tab.id}
                                    type="button"
                                    size="sm"
                                    variant={category === tab.id ? 'solid' : 'outline'}
                                    colorScheme={category === tab.id ? 'accent' : 'neutral'}
                                    onClick={() => {
                                        setCategory(tab.id);
                                        setCurrentPage(1);
                                    }}
                                >
                                    {tab.label} ({tab.count})
                                </Button>
                            ))}
                        </div>

                        {/* Timeframe selector */}
                        <div className="voxel-trough flex flex-wrap items-center gap-1 p-1 rounded-none">
                            {timeframes.map((tf) => (
                                <Button
                                    key={tf.label}
                                    type="button"
                                    size="sm"
                                    variant={timeframe === tf.value ? 'solid' : 'outline'}
                                    colorScheme={timeframe === tf.value ? 'accent' : 'neutral'}
                                    onClick={() => handleTimeframeChange(tf.value)}
                                    className="font-mono"
                                >
                                    {tf.label}
                                </Button>
                            ))}
                        </div>
                    </div>
                </Card>
            </SceneStage>

            <PageLayout
                maxWidth="lg"
                withPadding={false}
                className="relative z-10 flex flex-col gap-6 px-6 pb-8"
            >
                {isLoading && rows.length === 0 ? (
                    <div className="flex flex-col gap-6" aria-busy="true">
                        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-6 items-stretch">
                            <Skeleton variant="card" lines={4} />
                            <Skeleton variant="card" lines={4} />
                            <Skeleton variant="card" lines={4} />
                        </div>
                        <Skeleton variant="block" className="h-48" />
                    </div>
                ) : (
                    <>
                        {podium.length > 0 ? <LeaderboardPodium models={podium} /> : null}

                        <LeaderboardTable
                            models={rows}
                            selectedModels={selectedIds}
                            currentPage={currentPage}
                            pageSize={LEADERBOARD_PAGE_SIZE}
                            totalCount={totalCount}
                            sortField={sortField}
                            sortOrder={sortOrder}
                            isFetching={isFetching}
                            onSortChange={handleSortChange}
                            onPageChange={setCurrentPage}
                            onToggleSelectModel={handleToggleSelectModel}
                        />

                        {modelA && modelB ? (
                            <ModelComparison
                                modelA={modelA}
                                modelB={modelB}
                                onClear={handleClearComparison}
                            />
                        ) : null}
                    </>
                )}
            </PageLayout>
        </div>
    );
}

export default LeaderboardPage;
