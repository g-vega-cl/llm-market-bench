import {
    Badge,
    Button,
    ErrorCard,
    LoadingBoundary,
    LoadingSpinner,
    PageLayout,
    SectionHeading,
    Select,
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
        <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100">
            <PageLayout>
                <header className="flex flex-col gap-2">
                    <SectionHeading gradient="electric">LLM Research Audit Trail</SectionHeading>
                    <p className="text-boxel-muted text-xs font-normal max-w-3xl leading-relaxed m-0">
                        The ultimate source of truth for agent cognition. Every tool call, every
                        prompt, and every internal "thought" trace is captured here for deep
                        research and auditing.
                    </p>
                </header>

                {/* Filters Row (Tabs + Model Dropdown) */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="overflow-x-auto -mx-4 px-4 md:mx-0 md:px-0 scrollbar-hide">
                        <div className="flex gap-2 p-1.5 bg-zinc-100 dark:bg-zinc-900/50 rounded-none w-fit border border-zinc-200 dark:border-zinc-800 backdrop-blur-xl min-w-max">
                            {categories.map((cat) => (
                                <Button
                                    key={cat}
                                    variant={activeTab === cat ? 'solid' : 'ghost'}
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
                                variant="ghost"
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
                                        ? 'border-accent bg-accent-light dark:bg-accent-dark/20 shadow-sm ring-1 ring-accent/50'
                                        : 'border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/40 hover:border-zinc-300 dark:hover:border-zinc-700 shadow-sm'
                                }`}
                            >
                                <div className="flex justify-between items-start">
                                    <Badge
                                        variant="soft"
                                        size="sm"
                                        colorScheme="neutral"
                                        radius="none"
                                    >
                                        {log.task_type}
                                    </Badge>
                                    <span className="text-xs font-normal text-zinc-400 font-mono italic">
                                        {log.created_at
                                            ? formatEasternShortTime(log.created_at)
                                            : '-'}
                                    </span>
                                </div>
                                <h3 className="font-bold text-zinc-800 dark:text-zinc-100 text-sm leading-tight group-hover:text-accent transition-colors m-0">
                                    {log.metadata?.ticker || 'Global Analysis'}
                                </h3>
                                <div className="flex items-center gap-2">
                                    <div className="w-1.5 h-1.5 rounded-none bg-accent shrink-0" />
                                    <p className="text-xs font-normal text-zinc-500 dark:text-zinc-400 tracking-wider uppercase m-0">
                                        {log.model_provider} • {log.model_name}
                                    </p>
                                </div>
                            </div>
                        ))}
                        {(!filteredLogs || filteredLogs.length === 0) && !isFetching && (
                            <div className="text-center py-8 p-6 border-2 border-dashed border-zinc-200 dark:border-zinc-800 rounded-none text-zinc-400 italic text-xs font-normal">
                                No logs found for this category.
                            </div>
                        )}

                        {hasNextPage && (
                            <div className="pt-3 pb-1">
                                <Button
                                    variant="solid"
                                    size="lg"
                                    colorScheme="accent"
                                    gradient
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
                            <div className="text-center py-3 text-zinc-400 dark:text-zinc-500 text-xs font-bold uppercase tracking-wider">
                                • End of reasoning traces •
                            </div>
                        )}

                        {isFetching && !isFetchingNextPage && (
                            <div className="text-center py-2">
                                <LoadingSpinner size="sm" />
                            </div>
                        )}
                    </div>

                    {/* Trace viewer */}
                    <div
                        className={`${
                            selectedLog ? 'block' : 'hidden lg:block'
                        } lg:col-span-8 bg-white dark:bg-zinc-900/60 rounded-none border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm relative overflow-hidden max-h-[80vh] md:h-[75vh] flex flex-col gap-6`}
                    >
                        {!selectedLog ? (
                            <div className="h-full flex flex-col items-center justify-center text-zinc-400 gap-3">
                                <div className="w-12 h-12 rounded-none bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center">
                                    <LoadingSpinner size="md" />
                                </div>
                                <p className="italic font-normal text-xs text-center px-4 m-0">
                                    Select a reasoning trace to inspect the thinking process.
                                </p>
                            </div>
                        ) : (
                            <>
                                <div className="flex justify-between items-start pb-4 border-b border-zinc-100 dark:border-zinc-800/50 sticky top-0 bg-white dark:bg-zinc-900/60 z-10 -mx-6 px-6 pt-0">
                                    <div className="flex flex-col gap-2">
                                        <div className="flex items-center gap-3 flex-wrap">
                                            <h2 className="text-lg font-bold text-zinc-900 dark:text-white tracking-tight m-0">
                                                {selectedLog.metadata?.ticker ||
                                                    selectedLog.task_type}
                                            </h2>
                                            <Badge
                                                variant="soft"
                                                size="sm"
                                                colorScheme="accent"
                                                radius="none"
                                            >
                                                Audit Mode
                                            </Badge>
                                        </div>
                                        <p className="text-xs font-normal text-zinc-400 font-mono tracking-wider bg-zinc-100 dark:bg-zinc-800/50 px-2 py-0.5 rounded-none w-fit m-0">
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
