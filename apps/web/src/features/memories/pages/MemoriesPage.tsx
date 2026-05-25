import {
    Button,
    ErrorCard,
    LoadingBoundary,
    PageLayout,
    SectionHeading,
} from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { useInfiniteQuery } from '@tanstack/react-query';
import * as React from 'react';
import { MemoriesList } from '~/features/memories/components/MemoriesList';
import { memoriesQueries } from '~/features/memories/queries/options';
import type { PaginatedMemories } from '../api/fetch-memories';

interface MemoriesPageProps {
    fetchFn: (cursor: string | undefined, category?: string) => Promise<PaginatedMemories>;
}

export function MemoriesPage({ fetchFn }: MemoriesPageProps) {
    const posthog = usePostHog();
    const [filter, setFilter] = React.useState<string>('all');

    const { data, fetchNextPage, hasNextPage, isFetchingNextPage, status, error } =
        useInfiniteQuery({
            ...memoriesQueries.list({
                filters: { category: filter },
                fetchFn: (cursor) => fetchFn(cursor, filter),
            }),
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
        <div className="min-h-screen">
            {/* Header */}
            <div className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950">
                <PageLayout maxWidth="md" className="py-8">
                    <SectionHeading gradient="electric">AI Memories</SectionHeading>
                    <p className="text-zinc-600 dark:text-zinc-400 text-base mt-2">
                        Market insights, strategic decisions, and post-trade analysis from AI
                        agents.
                    </p>
                </PageLayout>
            </div>

            {/* Main Content */}
            <PageLayout maxWidth="md" className="py-8">
                <MemoriesList
                    memories={allMemories || []}
                    filter={filter}
                    onFilterChange={setFilter}
                />

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
                    <div className="mt-8 text-center text-sm text-zinc-500">End of memories</div>
                )}
            </PageLayout>
        </div>
    );
}
