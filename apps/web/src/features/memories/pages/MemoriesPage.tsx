import {
    Button,
    ErrorCard,
    LoadingBoundary,
    SectionHeading,
} from '@llm-market-bench/ui-design-system';
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
            <LoadingBoundary isLoading={true}>
                <div />
            </LoadingBoundary>
        );
    }

    if (status === 'error') {
        return <ErrorCard title="Failed to load memories" message={(error as Error).message} />;
    }

    return (
        <div className="flex flex-col min-h-screen">
            {/* Header */}
            <div className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950">
                <div className="flex flex-col px-6 md:px-12 py-8">
                    <div className="flex flex-col w-full max-w-5xl mx-auto">
                        <SectionHeading gradient="electric">AI Memories</SectionHeading>
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
                            <Button
                                variant="solid"
                                size="lg"
                                colorScheme="neutral"
                                onClick={() => {
                                    fetchNextPage();
                                    posthog.capture('memories_load_more_clicked');
                                }}
                                isLoading={isFetchingNextPage}
                            >
                                Load More
                            </Button>
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
