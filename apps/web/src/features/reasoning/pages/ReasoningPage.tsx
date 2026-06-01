import {
    Badge,
    Button,
    ErrorCard,
    LoadingBoundary,
    LoadingSpinner,
    PageLayout,
    SectionHeading,
} from '@llm-market-bench/ui-design-system';
import { useInfiniteQuery } from '@tanstack/react-query';
import * as React from 'react';
import { useAnalytics } from '~/lib/posthog-client';
import type { PaginatedReasoningLogs } from '../api/fetch-reasoning-logs';
import { HumanFriendlyPrompt } from '../components/HumanFriendlyPrompt';
import { HumanFriendlyResponse } from '../components/HumanFriendlyResponse';
import { reasoningQueries } from '../queries/options';

interface ReasoningPageProps {
    fetchFn: (cursor: string | undefined) => Promise<PaginatedReasoningLogs>;
}

export function ReasoningPage({ fetchFn }: ReasoningPageProps) {
    const posthog = useAnalytics();
    const [activeTab, setActiveTab] = React.useState<string>('ALL');
    const [selectedLogId, setSelectedLogId] = React.useState<string | null>(null);

    const { data, fetchNextPage, hasNextPage, isFetching, isFetchingNextPage, status, error } =
        useInfiniteQuery({
            ...reasoningQueries.list({ fetchFn }),
        });

    const allLogs = React.useMemo(() => data?.pages.flatMap((page) => page.data) || [], [data]);

    const categories = ['ALL', ...new Set(allLogs?.map((l) => l.task_type) || [])];
    const filteredLogs =
        activeTab === 'ALL' ? allLogs : allLogs?.filter((l) => l.task_type === activeTab);

    const selectedLog = allLogs?.find((l) => l.id === selectedLogId);

    if (status === 'pending') {
        return (
            <LoadingBoundary isLoading={true}>
                <div />
            </LoadingBoundary>
        );
    }

    if (status === 'error') {
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
                <header className="mb-8 md:mb-12">
                    <SectionHeading gradient="electric">LLM Research Audit Trail</SectionHeading>
                    <p className="text-zinc-500 dark:text-zinc-400 text-sm md:text-xl max-w-3xl leading-relaxed font-light mt-2">
                        The ultimate source of truth for agent cognition. Every tool call, every
                        prompt, and every internal "thought" trace is captured here for deep
                        research and auditing.
                    </p>
                </header>

                {/* Tabs */}
                <div className="mb-6 md:mb-8 overflow-x-auto -mx-4 px-4 md:mx-0 md:px-0 scrollbar-hide">
                    <div className="flex gap-2 p-1.5 bg-zinc-100 dark:bg-zinc-900/50 rounded-2xl w-fit border border-zinc-200 dark:border-zinc-800 backdrop-blur-xl min-w-max">
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
                                className="text-[10px] md:text-xs uppercase tracking-widest whitespace-nowrap min-h-[44px]"
                            >
                                {cat}
                            </Button>
                        ))}
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
                            >
                                ← Back to traces
                            </Button>
                        </div>
                    )}

                    {/* Logs list */}
                    <div
                        className={`${
                            selectedLog ? 'hidden lg:block' : 'block'
                        } lg:col-span-4 space-y-3 md:space-y-4 max-h-[50vh] md:max-h-[75vh] overflow-y-auto pr-2 md:pr-4`}
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
                                className={`p-4 md:p-5 rounded-2xl md:rounded-3xl border transition-all cursor-pointer group hover:shadow-2xl hover:-translate-y-1 ${
                                    selectedLogId === log.id
                                        ? 'border-accent bg-accent-light dark:bg-accent-dark/20 shadow-2xl ring-1 ring-accent/50'
                                        : 'border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/40 hover:border-zinc-300 dark:hover:border-zinc-700 shadow-sm'
                                }`}
                            >
                                <div className="flex justify-between items-start mb-2 md:mb-3">
                                    <Badge variant="soft" size="sm" colorScheme="neutral">
                                        {log.task_type}
                                    </Badge>
                                    <span className="text-[9px] md:text-[10px] text-zinc-400 font-mono italic">
                                        {log.created_at
                                            ? new Date(log.created_at).toLocaleTimeString()
                                            : '-'}
                                    </span>
                                </div>
                                <h3 className="font-bold text-zinc-800 dark:text-zinc-100 text-base md:text-lg leading-tight group-hover:text-accent transition-colors">
                                    {log.metadata?.ticker || 'Global Analysis'}
                                </h3>
                                <div className="flex items-center gap-2 mt-1.5 md:mt-2">
                                    <div className="w-1.5 h-1.5 rounded-full bg-accent shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
                                    <p className="text-[10px] md:text-[11px] font-medium text-zinc-500 dark:text-zinc-500 tracking-wide uppercase">
                                        {log.model_provider} • {log.model_name}
                                    </p>
                                </div>
                            </div>
                        ))}
                        {(!filteredLogs || filteredLogs.length === 0) && (
                            <div className="text-center py-8 md:py-12 p-6 md:p-8 border-2 border-dashed border-zinc-200 dark:border-zinc-800 rounded-2xl md:rounded-3xl text-zinc-400 italic">
                                No logs found for this category.
                            </div>
                        )}

                        {hasNextPage && (
                            <div className="pt-3 md:pt-4 pb-1 md:pb-2">
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
                                    className="w-full"
                                >
                                    Load More
                                </Button>
                            </div>
                        )}

                        {!hasNextPage && filteredLogs && filteredLogs.length > 0 && (
                            <div className="text-center py-3 md:py-4 text-zinc-400 dark:text-zinc-500 text-[10px] md:text-xs uppercase tracking-widest">
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
                        } lg:col-span-8 bg-white dark:bg-zinc-900/60 rounded-2xl md:rounded-[2.5rem] border border-zinc-200 dark:border-zinc-800 p-6 md:p-10 shadow-3xl backdrop-blur-3xl relative overflow-hidden max-h-[80vh] md:h-[75vh] flex flex-col`}
                    >
                        <div className="absolute top-0 right-0 w-32 md:w-64 h-32 md:h-64 bg-accent/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none" />

                        {!selectedLog ? (
                            <div className="h-full flex flex-col items-center justify-center text-zinc-400 space-y-3 md:space-y-4">
                                <div className="w-12 md:w-16 h-12 md:h-16 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center">
                                    <LoadingSpinner size="md" />
                                </div>
                                <p className="italic font-light text-sm md:text-lg text-center px-4">
                                    Select a reasoning trace to inspect the thinking process.
                                </p>
                            </div>
                        ) : (
                            <>
                                <div className="flex justify-between items-start mb-6 md:mb-8 pb-4 md:pb-8 border-b border-zinc-100 dark:border-zinc-800/50 sticky top-0 bg-white dark:bg-zinc-900/60 z-10 -mx-6 md:-mx-10 px-6 md:px-10 pt-6 md:pt-0">
                                    <div>
                                        <div className="flex items-center gap-2 md:gap-3 mb-1.5 md:mb-2 flex-wrap">
                                            <h2 className="text-xl md:text-3xl font-black text-zinc-900 dark:text-white tracking-tight">
                                                {selectedLog.metadata?.ticker ||
                                                    selectedLog.task_type}
                                            </h2>
                                            <Badge variant="soft" size="sm" colorScheme="accent">
                                                Audit Mode
                                            </Badge>
                                        </div>
                                        <p className="text-[10px] md:text-xs text-zinc-400 font-mono tracking-tighter bg-zinc-100 dark:bg-zinc-800/50 px-1.5 md:px-2 py-0.5 md:py-1 rounded-md w-fit">
                                            UUID: {selectedLog.id} •{' '}
                                            {selectedLog.created_at
                                                ? new Date(selectedLog.created_at).toLocaleString()
                                                : '-'}
                                        </p>
                                    </div>
                                </div>

                                <div className="flex-1 overflow-y-auto space-y-6 md:space-y-10 pr-3 md:pr-6">
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
