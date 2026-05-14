import { usePostHog } from '@posthog/react';
import { useInfiniteQuery } from '@tanstack/react-query';
import * as React from 'react';
import { MemoriesList } from '~/features/memories/components/MemoriesList';
import { memoriesQueries } from '~/features/memories/queries/options';

interface MemoriesPageProps {
    fetchFn: (cursor: string | undefined) => Promise<any>;
}

export function MemoriesPage({ fetchFn }: MemoriesPageProps) {
    const posthog = usePostHog();

    const { data, fetchNextPage, hasNextPage, isFetchingNextPage, status, error } =
        useInfiniteQuery({
            ...memoriesQueries.list({ fetchFn }),
        });

    const allMemories = React.useMemo(() => data?.pages.flatMap((page) => page.data) || [], [data]);

    if (status === 'pending') {
        return (
            <div className="min-h-[60vh] flex items-center justify-center">
                <div className="text-sm text-zinc-500">Loading...</div>
            </div>
        );
    }

    if (status === 'error') {
        return (
            <div className="flex justify-center mt-24 px-6">
                <div className="w-full max-w-2xl p-6 border border-red-200 dark:border-red-900 rounded-md bg-red-50 dark:bg-red-950/20">
                    <div className="flex items-start gap-3">
                        <div>
                            <h3 className="text-sm font-semibold text-red-800 dark:text-red-300 mb-1">
                                Failed to load memories
                            </h3>
                            <p className="text-sm text-red-600 dark:text-red-400">
                                {(error as Error).message}
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col min-h-screen">
            {/* Header */}
            <div className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950">
                <div className="flex flex-col px-6 md:px-12 py-8">
                    <div className="flex flex-col w-full max-w-5xl mx-auto">
                        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
                            AI Memories
                        </h1>
                        <p className="text-zinc-600 dark:text-zinc-400 text-base mt-2">
                            Market insights, strategic decisions, and post-trade analysis from AI
                            agents.
                        </p>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex flex-col flex-1 px-6 md:px-12 py-8">
                <div className="flex flex-col w-full max-w-5xl mx-auto">
                    <MemoriesList memories={allMemories || []} />

                    {/* Load More Button */}
                    {hasNextPage && (
                        <div className="mt-8 flex justify-center">
                            <button
                                type="button"
                                onClick={() => {
                                    fetchNextPage();
                                    posthog.capture('memories_load_more_clicked');
                                }}
                                disabled={isFetchingNextPage}
                                className="px-6 py-2.5 bg-zinc-900 dark:bg-zinc-100 hover:bg-zinc-800 dark:hover:bg-zinc-200 disabled:bg-zinc-400 text-white dark:text-zinc-900 text-sm font-medium rounded-md transition-colors"
                            >
                                {isFetchingNextPage ? 'Loading...' : 'Load More'}
                            </button>
                        </div>
                    )}

                    {/* No More Data Indicator */}
                    {!hasNextPage && allMemories && allMemories.length > 0 && (
                        <div className="mt-8 text-center text-sm text-zinc-500">
                            End of memories
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
