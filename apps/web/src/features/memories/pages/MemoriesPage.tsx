import {
    Button,
    ErrorCard,
    LoadingBoundary,
    PageLayout,
    SectionHeading,
} from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
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

/**
 * Fetches the first page of memories immediately for display.
 * Returns the first page and a cursor the caller can use to continue
 * fetching subsequent pages in the background.
 *
 * Production path (fetchFn provided): uses the server function wrapper,
 * which returns 50 items per page — cursor-based pagination handles the rest.
 *
 * Test/fallback path (no fetchFn): fetches up to MAX_CACHE_SIZE in one shot.
 */
async function performFullBackfill(
    fetchFn?: (cursor: string | undefined, category?: string) => Promise<PaginatedMemories>,
): Promise<{ memories: Memory[]; nextCursor: string | null }> {
    if (fetchFn) {
        const res = await fetchFn(undefined, undefined);
        const merged = mergeAndDeduplicate(res?.data || [], []);
        saveCachedMemories(merged);
        return { memories: merged, nextCursor: res?.nextCursor ?? null };
    }

    // Fallback when no fetchFn — used in unit tests that bypass the server fn
    const res = await fetchMemories(undefined, MAX_CACHE_SIZE);
    const merged = mergeAndDeduplicate(res?.data || [], []);
    saveCachedMemories(merged);
    return { memories: merged, nextCursor: null };
}

/**
 * Walks cursor pages via fetchFn until the cache is full or there are no more pages.
 * Saves each merged page to localStorage and updates the live React Query cache
 * silently — no loading state is shown to the user.
 */
async function runProgressiveFill(
    startCursor: string,
    fetchFn: (cursor: string | undefined, category?: string) => Promise<PaginatedMemories>,
    setQueryData: (data: Memory[]) => void,
): Promise<void> {
    let currentCursor: string | null = startCursor;

    while (currentCursor) {
        const accumulated = getCachedMemories();
        if (accumulated.length >= MAX_CACHE_SIZE) break;

        const res = await fetchFn(currentCursor, undefined);
        if (!res?.data?.length) break;

        const merged = mergeAndDeduplicate(res.data, accumulated);
        saveCachedMemories(merged);
        setQueryData(merged);

        currentCursor = res.hasMore ? (res.nextCursor ?? null) : null;
    }
}

/**
 * Decides whether to run a full backfill or an incremental delta-sync.
 *
 * - Empty cache or partial cache (< MAX_CACHE_SIZE): always backfill.
 *   The first page is returned immediately; the caller is responsible for
 *   fetching subsequent pages in the background via the returned nextCursor.
 *
 * - Full cache (>= MAX_CACHE_SIZE): validate the cache head against the DB,
 *   then delta-sync only the new records since the last cached timestamp.
 *   A cache-bust (missing ID or DB rollback) triggers a fresh backfill.
 */
async function syncMemoriesCache(
    cached: Memory[],
    fetchFn?: (cursor: string | undefined, category?: string) => Promise<PaginatedMemories>,
): Promise<{ memories: Memory[]; nextCursor: string | null }> {
    const latestCachedTimestamp = cached.length > 0 ? cached[0].created_at : null;
    const latestCachedId = cached.length > 0 ? cached[0].id : null;

    // No cache or partial cache — run a full backfill
    if (!latestCachedTimestamp || !latestCachedId || cached.length < MAX_CACHE_SIZE) {
        return performFullBackfill(fetchFn);
    }

    // Full cache — validate and delta-sync
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

        const newMemories = await fetchNewMemories(latestCachedTimestamp);
        const merged = mergeAndDeduplicate(newMemories, cached);
        saveCachedMemories(merged);
        return { memories: merged, nextCursor: null };
    } catch (e) {
        console.error('Failed cache validation, falling back to safe delta fetch:', e);
        const newMemories = await fetchNewMemories(latestCachedTimestamp);
        const merged = mergeAndDeduplicate(newMemories, cached);
        saveCachedMemories(merged);
        return { memories: merged, nextCursor: null };
    }
}

interface MemoriesPageProps {
    fetchFn?: (cursor: string | undefined, category?: string) => Promise<PaginatedMemories>;
}

const PAGE_SIZE = 50;

export function MemoriesPage({ fetchFn }: MemoriesPageProps) {
    const queryClient = useQueryClient();
    const posthog = usePostHog();
    const [filter, setFilter] = React.useState<string>('all');
    const [displayLimit, setDisplayLimit] = React.useState<number>(PAGE_SIZE);

    // Cursor to continue a progressive backfill after the first page loads.
    // Set by the queryFn; consumed and cleared by the fill effect.
    const [pendingCursor, setPendingCursor] = React.useState<string | null>(null);
    // Prevents multiple concurrent background fill loops
    const isFillingRef = React.useRef(false);

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
            const { memories: firstPage, nextCursor } = await syncMemoriesCache(cached, fetchFn);
            // Signal the fill effect with the cursor (or clear it if no fill needed)
            setPendingCursor(nextCursor);
            return firstPage;
        },
        initialData: () => {
            return getCachedMemories();
        },
        initialDataUpdatedAt: 1, // Treat initial data as immediately stale so background delta sync runs on mount
        staleTime: 1000 * 30, // 30 seconds
        refetchOnWindowFocus: false,
    });

    // Invisible background progressive fill
    // Fires when the queryFn sets a pendingCursor after the first page loads.
    // Continues paging through remaining records and silently updates the displayed list.
    // No loading state is shown to the user.
    React.useEffect(() => {
        if (!pendingCursor || isFillingRef.current || !fetchFn) return;

        isFillingRef.current = true;
        // Clear immediately to prevent re-entrancy if the component re-renders
        setPendingCursor(null);

        runProgressiveFill(pendingCursor, fetchFn, (data) =>
            queryClient.setQueryData<Memory[]>(['benchify', 'memories', 'list'], data),
        )
            .catch((e) => console.error('Background progressive fill failed:', e))
            .finally(() => {
                isFillingRef.current = false;
            });
    }, [pendingCursor, fetchFn, queryClient]);

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
