import {
    Button,
    ErrorCard,
    LoadingBoundary,
    PageLayout,
    SectionHeading,
} from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { type InfiniteData, useInfiniteQuery, useQueryClient } from '@tanstack/react-query';
import * as React from 'react';
import {
    type DatePresetOption,
    getMemoryCategory,
    MemoriesList,
    type Memory,
    type MemorySortOption,
} from '~/features/memories/components/MemoriesList';
import type { PaginatedMemories } from '../api/fetch-memories';

interface MemoriesPageProps {
    initialMemories: Memory[];
    initialHasMore: boolean;
    initialCursor: string | null;
    fetchFn: (
        cursor: string | undefined,
        category: string | undefined,
    ) => Promise<PaginatedMemories>;
    searchFn?: (query: string) => Promise<Memory[]>;
    deltaSyncFn?: (since: string) => Promise<Memory[]>;
}

const PAGE_SIZE = 50;

function computeFilteredMemories(
    sourceList: Memory[],
    filter: string,
    onlyHighImpact: boolean,
    datePreset: DatePresetOption,
    sortBy: MemorySortOption,
): Memory[] {
    // 1. Category / Status Filter
    let list = sourceList;
    if (filter === 'RESOLVED') {
        list = list.filter((m) => m.status === 'RESOLVED');
    } else if (filter !== 'all') {
        list = list.filter((m) => getMemoryCategory(m) === filter);
    }

    // 2. High Impact Filter (importance_score >= 8)
    if (onlyHighImpact) {
        list = list.filter((m) => (m.importance_score ?? 5) >= 8);
    }

    // 3. Date Preset Filter (based on created_at)
    if (datePreset !== 'all') {
        const now = Date.now();
        const daysMap: Record<string, number> = {
            '7d': 7,
            '30d': 30,
            '90d': 90,
        };
        const maxDays = daysMap[datePreset] ?? 0;
        if (maxDays > 0) {
            const cutoffMs = now - maxDays * 24 * 60 * 60 * 1000;
            list = list.filter((m) => {
                if (!m.created_at) return false;
                const memTime = new Date(m.created_at).getTime();
                return memTime >= cutoffMs;
            });
        }
    }

    // 4. Sorting
    const sorted = [...list];
    sorted.sort((a, b) => {
        const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
        const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
        const scoreA = a.importance_score ?? 5;
        const scoreB = b.importance_score ?? 5;

        switch (sortBy) {
            case 'importance_desc':
                if (scoreB !== scoreA) {
                    return scoreB - scoreA;
                }
                return dateB - dateA;
            case 'importance_asc':
                if (scoreA !== scoreB) {
                    return scoreA - scoreB;
                }
                return dateB - dateA;
            case 'oldest':
                return dateA - dateB;
            default:
                return dateB - dateA;
        }
    });

    return sorted;
}

export function MemoriesPage({
    initialMemories,
    initialHasMore,
    initialCursor,
    fetchFn,
    searchFn,
    deltaSyncFn,
}: MemoriesPageProps) {
    const posthog = usePostHog();
    const queryClient = useQueryClient();
    const [filter, setFilter] = React.useState<string>('all');
    const [sortBy, setSortBy] = React.useState<MemorySortOption>('newest');
    const [datePreset, setDatePreset] = React.useState<DatePresetOption>('all');
    const [onlyHighImpact, setOnlyHighImpact] = React.useState<boolean>(false);
    const [displayLimit, setDisplayLimit] = React.useState<number>(PAGE_SIZE);

    const [searchQuery, setSearchQuery] = React.useState('');
    const [activeSearchQuery, setActiveSearchQuery] = React.useState('');
    const [searchResults, setSearchResults] = React.useState<Memory[] | null>(null);
    const [isSearching, setIsSearching] = React.useState(false);

    // Standard infinite query for paginated scroll/fetch with 4-hour cache
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
            staleTime: 1000 * 60 * 60 * 4, // 4 hours
            refetchOnWindowFocus: false,
        });

    // Flatten all fetched pages into a single memories list
    const memories = React.useMemo(() => {
        return data ? data.pages.flatMap((page) => page.data || []) : [];
    }, [data]);

    // Delta-sync check on mount: check if newer memories arrived and prepend them
    const hasCheckedDeltaSync = React.useRef(false);
    React.useEffect(() => {
        if (!deltaSyncFn || hasCheckedDeltaSync.current || memories.length === 0) return;
        const newestCreatedAt = memories[0]?.created_at;
        if (!newestCreatedAt) return;

        hasCheckedDeltaSync.current = true;
        deltaSyncFn(newestCreatedAt)
            .then((newRecords) => {
                if (newRecords && newRecords.length > 0) {
                    queryClient.setQueryData(
                        ['benchify', 'memories', 'list'],
                        (old: InfiniteData<PaginatedMemories> | undefined) => {
                            if (!old?.pages || old.pages.length === 0) return old;
                            const firstPage = old.pages[0];
                            return {
                                ...old,
                                pages: [
                                    {
                                        ...firstPage,
                                        data: [...newRecords, ...(firstPage.data || [])],
                                    },
                                    ...old.pages.slice(1),
                                ],
                            };
                        },
                    );
                }
            })
            .catch((err) => {
                console.error('Delta-sync check failed:', err);
            });
    }, [deltaSyncFn, memories, queryClient]);

    const handleFilterChange = (newFilter: string) => {
        setFilter(newFilter);
        setDisplayLimit(PAGE_SIZE);
    };

    const handleSortChange = (newSort: MemorySortOption) => {
        const sourceList = searchResults !== null ? searchResults : memories;
        const nextFiltered = computeFilteredMemories(
            sourceList,
            filter,
            onlyHighImpact,
            datePreset,
            newSort,
        );
        setSortBy(newSort);
        setDisplayLimit(PAGE_SIZE);
        posthog.capture('memories_sort_changed', {
            sort_by: newSort,
            result_count: nextFiltered.length,
        });
    };

    const handleDatePresetChange = (newPreset: DatePresetOption) => {
        const sourceList = searchResults !== null ? searchResults : memories;
        const nextFiltered = computeFilteredMemories(
            sourceList,
            filter,
            onlyHighImpact,
            newPreset,
            sortBy,
        );
        setDatePreset(newPreset);
        setDisplayLimit(PAGE_SIZE);
        posthog.capture('memories_date_preset_changed', {
            date_preset: newPreset,
            result_count: nextFiltered.length,
        });
    };

    const handleHighImpactToggle = () => {
        const nextImpact = !onlyHighImpact;
        const sourceList = searchResults !== null ? searchResults : memories;
        const nextFiltered = computeFilteredMemories(
            sourceList,
            filter,
            nextImpact,
            datePreset,
            sortBy,
        );
        setOnlyHighImpact(nextImpact);
        setDisplayLimit(PAGE_SIZE);
        posthog.capture('memories_high_impact_toggled', {
            enabled: nextImpact,
            result_count: nextFiltered.length,
        });
    };

    const handleSearchSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        const trimmed = searchQuery.trim();
        if (!trimmed) {
            handleSearchClear();
            return;
        }

        if (searchFn) {
            setIsSearching(true);
            try {
                const results = await searchFn(trimmed);
                setSearchResults(results);
                setActiveSearchQuery(trimmed);
                posthog.capture('memories_search_completed', { query: trimmed });
            } catch (err) {
                console.error('Error searching memories:', err);
            } finally {
                setIsSearching(false);
            }
        }
    };

    const handleSearchClear = () => {
        setSearchQuery('');
        setActiveSearchQuery('');
        setSearchResults(null);
        posthog.capture('memories_search_cleared');
    };

    // 100% Instantaneous Client-Side Filtering and Sorting
    const filteredMemories = React.useMemo(() => {
        const sourceList = searchResults !== null ? searchResults : memories;
        return computeFilteredMemories(sourceList, filter, onlyHighImpact, datePreset, sortBy);
    }, [memories, searchResults, filter, onlyHighImpact, datePreset, sortBy]);

    // Client-Side Pagination (limits rendered memories for DOM performance)
    const displayedMemories = React.useMemo(() => {
        return filteredMemories.slice(0, displayLimit);
    }, [filteredMemories, displayLimit]);

    // We can load more if we haven't displayed all memories loaded client-side,
    // or if the server still has subsequent pages we can fetch in the background.
    const hasMoreClient = filteredMemories.length > displayLimit;
    const canLoadMore =
        searchResults === null && (hasMoreClient || (hasNextPage && !isFetchingNextPage));

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
            <div className="border-b border-zinc-200 dark:border-white/10">
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
                {/* Search Bar */}
                <form onSubmit={handleSearchSubmit} className="mb-6 flex gap-2">
                    <div className="relative flex-1">
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Search memories (e.g., energy deal Trump, S&P 500 drop)..."
                            className="w-full bg-zinc-55 dark:bg-zinc-900 border border-zinc-200 dark:border-white/10 rounded-md px-4 py-2.5 pl-10 pr-10 text-sm text-zinc-905 dark:text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-400 dark:focus:ring-white/20 transition-all font-sans"
                        />
                        <span className="absolute left-3.5 top-3.5 text-zinc-400 dark:text-zinc-500">
                            <svg
                                className="w-4 h-4"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <title>Search Icon</title>
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                                />
                            </svg>
                        </span>
                        {searchQuery && (
                            <button
                                type="button"
                                onClick={handleSearchClear}
                                className="absolute right-3.5 top-3.5 text-zinc-400 dark:text-zinc-500 hover:text-zinc-600 dark:hover:text-zinc-300"
                            >
                                <svg
                                    className="w-4 h-4"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <title>Clear Icon</title>
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M6 18L18 6M6 6l12 12"
                                    />
                                </svg>
                            </button>
                        )}
                    </div>
                    <Button
                        type="submit"
                        variant="solid"
                        colorScheme="accent"
                        size="md"
                        isLoading={isSearching}
                    >
                        Search
                    </Button>
                </form>

                {activeSearchQuery && (
                    <div className="mb-6 flex items-center justify-between text-sm text-zinc-600 dark:text-zinc-400 bg-zinc-50 dark:bg-zinc-900/40 border border-zinc-200 dark:border-white/5 rounded-md px-4 py-2.5">
                        <div>
                            Showing matches for{' '}
                            <span className="font-semibold text-zinc-900 dark:text-zinc-250">
                                "{activeSearchQuery}"
                            </span>
                            <span className="ml-1 text-xs text-zinc-400">
                                ({filteredMemories.length} results)
                            </span>
                        </div>
                        <button
                            type="button"
                            onClick={handleSearchClear}
                            className="text-xs text-blue-500 hover:text-blue-600 dark:hover:text-blue-400 font-medium cursor-pointer"
                        >
                            Reset Search
                        </button>
                    </div>
                )}

                <MemoriesList
                    memories={displayedMemories}
                    filter={filter}
                    onFilterChange={handleFilterChange}
                    sortBy={sortBy}
                    onSortChange={handleSortChange}
                    datePreset={datePreset}
                    onDatePresetChange={handleDatePresetChange}
                    onlyHighImpact={onlyHighImpact}
                    onHighImpactToggle={handleHighImpactToggle}
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
