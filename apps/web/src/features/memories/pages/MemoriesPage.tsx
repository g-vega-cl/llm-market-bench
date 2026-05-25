import {
    Button,
    ErrorCard,
    LoadingBoundary,
    PageLayout,
    SectionHeading,
} from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { useQuery } from '@tanstack/react-query';
import * as React from 'react';
import {
    getMemoryCategory,
    MemoriesList,
    type Memory,
} from '~/features/memories/components/MemoriesList';
import {
    fetchMemories,
    fetchNewMemories,
    type PaginatedMemories,
    validateCacheState,
} from '../api/fetch-memories';
import {
    getCachedMemories,
    MAX_CACHE_SIZE,
    mergeAndDeduplicate,
    saveCachedMemories,
} from '../lib/cache';

async function performFullBackfill(
    fetchFn?: (cursor: string | undefined, category?: string) => Promise<PaginatedMemories>,
): Promise<Memory[]> {
    const res = fetchFn
        ? await fetchFn(undefined, undefined)
        : await fetchMemories(undefined, MAX_CACHE_SIZE);
    const merged = mergeAndDeduplicate(res?.data || [], []);
    saveCachedMemories(merged);
    return merged;
}

async function fetchDeltaOrBackfill(
    cached: Memory[],
    latestCachedTimestamp: string,
    fetchFn?: (cursor: string | undefined, category?: string) => Promise<PaginatedMemories>,
): Promise<Memory[]> {
    if (cached.length >= MAX_CACHE_SIZE) {
        return fetchNewMemories(latestCachedTimestamp);
    }
    const res = fetchFn
        ? await fetchFn(undefined, undefined)
        : await fetchMemories(undefined, MAX_CACHE_SIZE);
    return res?.data || [];
}

async function syncMemoriesCache(
    cached: Memory[],
    fetchFn?: (cursor: string | undefined, category?: string) => Promise<PaginatedMemories>,
): Promise<Memory[]> {
    const latestCachedTimestamp = cached.length > 0 ? cached[0].created_at : null;
    const latestCachedId = cached.length > 0 ? cached[0].id : null;

    if (!latestCachedTimestamp || !latestCachedId) {
        return performFullBackfill(fetchFn);
    }

    try {
        const validation = await validateCacheState(latestCachedId);

        const dbTime = validation.latestTimestamp
            ? new Date(validation.latestTimestamp).getTime()
            : 0;
        const cachedTime = new Date(latestCachedTimestamp).getTime();

        const isReset = !validation.exists || dbTime < cachedTime || !validation.latestTimestamp;
        if (isReset) {
            return performFullBackfill(fetchFn);
        }

        const newMemories = await fetchDeltaOrBackfill(cached, latestCachedTimestamp, fetchFn);
        const merged = mergeAndDeduplicate(newMemories, cached);
        saveCachedMemories(merged);
        return merged;
    } catch (e) {
        console.error('Failed cache validation, falling back to safe delta/full fetch:', e);
        const newMemories = await fetchDeltaOrBackfill(cached, latestCachedTimestamp, fetchFn);
        const merged = mergeAndDeduplicate(newMemories, cached);
        saveCachedMemories(merged);
        return merged;
    }
}

interface MemoriesPageProps {
    fetchFn?: (cursor: string | undefined, category?: string) => Promise<PaginatedMemories>;
}

const PAGE_SIZE = 50;

export function MemoriesPage({ fetchFn }: MemoriesPageProps) {
    const posthog = usePostHog();
    const [filter, setFilter] = React.useState<string>('all');
    const [displayLimit, setDisplayLimit] = React.useState<number>(PAGE_SIZE);

    const handleFilterChange = (newFilter: string) => {
        setFilter(newFilter);
        setDisplayLimit(PAGE_SIZE);
    };

    const {
        data: memories = [],
        error,
        isPending,
    } = useQuery({
        queryKey: ['benchify', 'memories', 'list'],
        queryFn: async () => {
            const cached = getCachedMemories();
            return syncMemoriesCache(cached, fetchFn);
        },
        initialData: () => {
            return getCachedMemories();
        },
        initialDataUpdatedAt: 1, // Treat initial data as immediately stale so background delta sync runs on mount
        staleTime: 1000 * 30, // 30 seconds
        refetchOnWindowFocus: false,
    });

    // 100% Instantaneous Client-Side Filtering
    const filteredMemories = React.useMemo(() => {
        if (filter === 'all') return memories;
        return memories.filter((m) => getMemoryCategory(m) === filter);
    }, [memories, filter]);

    // Client-Side Pagination
    const displayedMemories = React.useMemo(() => {
        return filteredMemories.slice(0, displayLimit);
    }, [filteredMemories, displayLimit]);

    const hasMore = filteredMemories.length > displayLimit;

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
                {hasMore && (
                    <div className="mt-8 flex justify-center">
                        <Button
                            variant="solid"
                            size="lg"
                            colorScheme="neutral"
                            onClick={() => {
                                setDisplayLimit((prev) => prev + PAGE_SIZE);
                                posthog.capture('memories_load_more_clicked');
                            }}
                        >
                            Load More
                        </Button>
                    </div>
                )}

                {/* No More Data Indicator */}
                {!hasMore && displayedMemories.length > 0 && (
                    <div className="mt-8 text-center text-sm text-zinc-500">End of memories</div>
                )}
            </PageLayout>
        </div>
    );
}
