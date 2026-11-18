import {
    Badge,
    Button,
    ErrorCard,
    LoadingBoundary,
    PageLayout,
    SectionHeading,
    Select,
    Skeleton,
} from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { useInfiniteQuery } from '@tanstack/react-query';
import * as React from 'react';
import { formatEasternDateTime, formatEasternShortTime } from '~/utils/date';
import type { PaginatedReasoningLogs } from '../api/fetch-reasoning-logs';
import { HumanFriendlyPrompt } from '../components/HumanFriendlyPrompt';
import { HumanFriendlyResponse } from '../components/HumanFriendlyResponse';
import { reasoningQueries } from '../queries/options';

interface ReasoningPageProps {
    initialData: PaginatedReasoningLogs;
    fetchFn: (cursor: string | undefined) => Promise<PaginatedReasoningLogs>;
}

export function ReasoningPage({ initialData, fetchFn }: ReasoningPageProps) {
    const posthog = usePostHog();
    const [activeTab, setActiveTab] = React.useState<string>('ALL');
    const [selectedModel, setSelectedModel] = React.useState<string>('ALL');
    const [selectedLogId, setSelectedLogId] = React.useState<string | null>(null);

    const { data, fetchNextPage, hasNextPage, isFetching, isFetchingNextPage, isPending, error } =
        useInfiniteQuery({
            ...reasoningQueries.list({ fetchFn }),
            initialData: {
                pages: [initialData],
                pageParams: [undefined],
            },
            // SSR ships a small slice; mark it stale so the full page loads on mount.
            initialDataUpdatedAt: 0,
        });

    const allLogs = React.useMemo(() => data?.pages.flatMap((page) => page.data) || [], [data]);

    const categories = ['ALL', ...new Set(allLogs?.map((l) => l.task_type) || [])];
    const availableModels = [
        { label: 'All Models', value: 'ALL' },
        ...Array.from(new Set(allLogs?.map((l) => l.model_name).filter(Boolean) || [])).map(
            (m) => ({ label: m, value: m }),
        ),
    ];

    const filteredLogs = allLogs?.filter((l) => {
        const matchesTab = activeTab === 'ALL' || l.task_type === activeTab;
        const matchesModel = selectedModel === 'ALL' || l.model_name === selectedModel;
        return matchesTab && matchesModel;
    });

    const selectedLog = allLogs?.find((l) => l.id === selectedLogId);

    if (isPending && allLogs.length === 0) {
        return (
            <LoadingBoundary isLoading={true}>
                <div />
            </LoadingBoundary>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <ErrorCard
                    title="Failed to load reasoning logs"
                    message={(error as Error).message}
                />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-voxel-canvas text-voxel-ink">
            <PageLayout>
                <header className="flex flex-col gap-2">
                    <SectionHeading>LLM Research Audit Trail</SectionHeading>
                    <p className="text-voxel-muted text-xs font-normal max-w-3xl leading-relaxed m-0">
                        The ultimate source of truth for agent cognition. Every tool call, every
                        prompt, and every internal "thought" trace is captured here for deep
                        research and auditing.
                    </p>
                </header>

                {/* Filters Row (Tabs + Model Dropdown) */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="overflow-x-auto -mx-4 px-4 md:mx-0 md:px-0 scrollbar-hide">
                        <div className="flex gap-2 p-1.5 bg-voxel-trough rounded-none w-fit border border-voxel-bevel-hi min-w-max">
                            {categories.map((cat) => (
                                <Button
                                    key={cat}
                                    variant={activeTab === cat ? 'solid' : 'outline'}
                                    size="sm"
                                    colorScheme={activeTab === cat ? 'accent' : 'neutral'}
                                    onClick={() => {
                                        setActiveTab(cat);
                                        posthog.capture('reasoning_category_filtered', {
                                            category: cat,
                                        });
                                    }}
                                    className="text-sm font-bold uppercase tracking-wider whitespace-nowrap rounded-none"
                                >
                                    {cat}
                                </Button>
                            ))}
                        </div>
                    </div>

                    {/* Model Filter */}
                    <div className="w-full md:w-64">
                        <Select
                            aria-label="Filter reasoning traces by model"
                            value={selectedModel}
                            options={availableModels}
                            onChange={(e) => {
                                const newModel = e.target.value;
                                setSelectedModel(newModel);
                                posthog.capture('reasoning_model_filtered', {
                                    model: newModel,
                                });
                            }}
                        />
                    </div>
                </div>

                {/* Content split */}
                <div className="lg:grid lg:grid-cols-12 lg:gap-8 flex flex-col">
                    {/* Mobile back button */}
                    {selectedLog && (
                        <div className="lg:hidden mb-4">
                            <Button
                                variant="outline"
                                size="md"
                                colorScheme="neutral"
                                onClick={() => setSelectedLogId(null)}
                                className="rounded-none text-sm font-bold"
                            >
                                ← Back to traces
                            </Button>
                        </div>
                    )}

                    {/* Logs list */}
                    <div
                        className={`${
                            selectedLog ? 'hidden lg:block' : 'block'
                        } lg:col-span-4 flex flex-col gap-3 max-h-[50vh] md:max-h-[75vh] overflow-y-auto pr-2 md:pr-4`}
                    >
                        {filteredLogs?.map((log) => (
                            <div
                                key={log.id}
                                onClick={() => {
                                    setSelectedLogId(log.id);
                                    posthog.capture('reasoning_trace_selected', {
                                        trace_id: log.id,
                                        task_type: log.task_type,
                                        model_provider: log.model_provider,
                                        model_name: log.model_name,
                                    });
                                }}
                                className={`p-4 rounded-none border transition-all cursor-pointer group flex flex-col gap-2 ${
                                    selectedLogId === log.id
                                        ? 'border-accent bg-voxel-elevated shadow-sm ring-1 ring-accent/50'
                                        : 'border-voxel-bevel-hi bg-voxel-surface hover:border-voxel-muted shadow-sm'
                                }`}
                            >
                                <div className="flex justify-between items-start">
                                    <Badge variant="soft" size="sm" colorScheme="neutral">
                                        {log.task_type}
                                    </Badge>
                                    <span className="text-xs font-normal text-voxel-muted font-mono italic">
                                        {log.created_at
                                            ? formatEasternShortTime(log.created_at)
                                            : '-'}
                                    </span>
                                </div>
                                <h3 className="font-bold text-voxel-ink text-sm leading-tight group-hover:text-accent transition-colors m-0">
                                    {log.metadata?.ticker || 'Global Analysis'}
                                </h3>
                                <div className="flex items-center gap-2">
                                    <div className="w-1.5 h-1.5 rounded-none bg-accent shrink-0" />
                                    <p className="text-xs font-normal text-voxel-muted tracking-wider uppercase m-0">
                                        {log.model_provider} • {log.model_name}
                                    </p>
                                </div>
                            </div>
                        ))}
                        {(!filteredLogs || filteredLogs.length === 0) && !isFetching && (
                            <div className="text-center py-8 p-6 border-2 border-dashed border-voxel-bevel-hi rounded-none text-voxel-muted italic text-xs font-normal">
                                No logs found for this category.
                            </div>
                        )}

                        {hasNextPage && (
                            <div className="pt-3 pb-1">
                                <Button
                                    variant="solid"
                                    size="md"
                                    colorScheme="accent"
                                    onClick={() => {
                                        fetchNextPage();
                                        posthog.capture('reasoning_load_more_clicked');
                                    }}
                                    isLoading={isFetchingNextPage}
                                    className="w-full rounded-none text-sm font-bold"
                                >
                                    Load More
                                </Button>
                            </div>
                        )}

                        {!hasNextPage && filteredLogs && filteredLogs.length > 0 && (
                            <div className="text-center py-3 text-voxel-muted text-sm font-bold uppercase tracking-wider">
                                • End of reasoning traces •
                            </div>
                        )}

                        {isFetching && !isFetchingNextPage && <Skeleton variant="card" lines={2} />}
                    </div>

                    {/* Trace viewer */}
                    <div
                        className={`${
                            selectedLog ? 'block' : 'hidden lg:block'
                        } lg:col-span-8 bg-voxel-surface rounded-none border border-voxel-bevel-hi p-6 shadow-sm relative overflow-hidden max-h-[80vh] md:h-[75vh] flex flex-col gap-6`}
                    >
                        {!selectedLog ? (
                            <div className="h-full flex flex-col items-center justify-center text-voxel-muted gap-4">
                                <Skeleton variant="card" lines={3} className="w-full max-w-md" />
                                <p className="italic font-normal text-xs text-center px-4 m-0">
                                    Select a reasoning trace to inspect the thinking process.
                                </p>
                            </div>
                        ) : (
                            <>
                                <div className="flex justify-between items-start pb-4 border-b border-voxel-bevel-hi sticky top-0 bg-voxel-surface z-10 -mx-6 px-6 pt-0">
                                    <div className="flex flex-col gap-2">
                                        <div className="flex items-center gap-3 flex-wrap">
                                            <h2 className="text-sm font-bold text-voxel-ink tracking-tight m-0">
                                                {selectedLog.metadata?.ticker ||
                                                    selectedLog.task_type}
                                            </h2>
                                            <Badge variant="soft" size="sm" colorScheme="accent">
                                                Audit Mode
                                            </Badge>
                                        </div>
                                        <p className="text-xs font-normal text-voxel-muted font-mono tracking-wider bg-voxel-trough px-2 py-0.5 rounded-none w-fit m-0">
                                            UUID: {selectedLog.id} •{' '}
                                            {selectedLog.created_at
                                                ? formatEasternDateTime(selectedLog.created_at)
                                                : '-'}
                                        </p>
                                    </div>
                                </div>

                                <div className="flex-1 overflow-y-auto flex flex-col gap-6 pr-3">
                                    <HumanFriendlyPrompt prompt={selectedLog.prompt} />
                                    <HumanFriendlyResponse response={selectedLog.response} />
                                </div>
                            </>
                        )}
                    </div>
                </div>
            </PageLayout>
        </div>
    );
}
