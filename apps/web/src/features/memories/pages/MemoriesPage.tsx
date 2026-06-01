import {
    Button,
    ErrorCard,
    LoadingBoundary,
    PageLayout,
    SectionHeading,
} from '@llm-market-bench/ui-design-system';
import { useInfiniteQuery } from '@tanstack/react-query';
import * as React from 'react';
import {
    getMemoryCategory,
    MemoriesList,
    type Memory,
} from '~/features/memories/components/MemoriesList';
import { useAnalytics } from '~/lib/posthog-client';
import type { PaginatedMemories } from '../api/fetch-memories';

interface MemoriesPageProps {
    initialMemories: Memory[];
    initialHasMore: boolean;
    initialCursor: string | null;
    fetchFn: (
        cursor: string | undefined,
        category: string | undefined,
    ) => Promise<PaginatedMemories>;
}

const PAGE_SIZE = 50;

export function MemoriesPage({
    initialMemories,
    initialHasMore,
    initialCursor,
    fetchFn,
}: MemoriesPageProps) {
    const posthog = useAnalytics();
    const [filter, setFilter] = React.useState<string>('all');
    const [displayLimit, setDisplayLimit] = React.useState<number>(PAGE_SIZE);

    const handleFilterChange = (newFilter: string) => {
        setFilter(newFilter);
        setDisplayLimit(PAGE_SIZE);
    };

    // Standard infinite query for paginated scroll/fetch
    const { data, error, fetchNextPage, hasNextPage, isFetchingNextPage, isPending } =
        useInfiniteQuery({
            queryKey: ['benchify', 'memories', 'list'],
            queryFn: async ({ pageParam }) => {
                const res = await fetchFn(pageParam, undefined);
                return res;
            },
            initialPageParam: undefined as string | undefined,
            getNextPageParam: (lastPage) =>
                lastPage.hasMore ? (lastPage.nextCursor ?? undefined) : undefined,
            initialData: {
                pages: [
                    {
                        data: initialMemories,
                        hasMore: initialHasMore,
                        nextCursor: initialCursor,
                    },
                ],
                pageParams: [undefined],
            },
            staleTime: 1000 * 30, // 30 seconds
            refetchOnWindowFocus: false,
        });

    // Flatten all fetched pages into a single memories list
    const memories = React.useMemo(() => {
        return data ? data.pages.flatMap((page) => page.data || []) : [];
    }, [data]);

    // 100% Instantaneous Client-Side Filtering
    const filteredMemories = React.useMemo(() => {
        if (filter === 'all') return memories;
        return memories.filter((m) => getMemoryCategory(m) === filter);
    }, [memories, filter]);

    // Client-Side Pagination (limits rendered memories for DOM performance)
    const displayedMemories = React.useMemo(() => {
        return filteredMemories.slice(0, displayLimit);
    }, [filteredMemories, displayLimit]);

    // We can load more if we haven't displayed all memories loaded client-side,
    // or if the server still has subsequent pages we can fetch in the background.
    const hasMoreClient = filteredMemories.length > displayLimit;
    const canLoadMore = hasMoreClient || (hasNextPage && !isFetchingNextPage);

    const handleLoadMore = async () => {
        posthog.capture('memories_load_more_clicked');
        if (hasMoreClient) {
            // Simply increase client-side display limit
            setDisplayLimit((prev) => prev + PAGE_SIZE);
        } else if (hasNextPage) {
            // Fetch next page from server
            const res = await fetchNextPage();
            // Once fetched, expand the display limit to show the newly arrived data
            if (res.data) {
                setDisplayLimit((prev) => prev + PAGE_SIZE);
            }
        }
    };

    if (isPending && memories.length === 0) {
        return (
            <LoadingBoundary isLoading={true}>
                <div />
            </LoadingBoundary>
        );
    }

    if (error) {
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
                    memories={displayedMemories}
                    filter={filter}
                    onFilterChange={handleFilterChange}
                />

                {/* Load More Button */}
                {canLoadMore && (
                    <div className="mt-8 flex justify-center">
                        <Button
                            variant="solid"
                            size="lg"
                            colorScheme="neutral"
                            onClick={handleLoadMore}
                            isLoading={isFetchingNextPage}
                        >
                            Load More
                        </Button>
                    </div>
                )}

                {/* No More Data Indicator */}
                {!canLoadMore && displayedMemories.length > 0 && (
                    <div className="mt-8 text-center text-sm text-zinc-500">End of memories</div>
                )}
            </PageLayout>
        </div>
    );
}
