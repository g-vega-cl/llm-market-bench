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
import {
    getMemoryCategory,
    MemoriesList,
    type Memory,
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
}

const PAGE_SIZE = 50;

export function MemoriesPage({
    initialMemories,
    initialHasMore,
    initialCursor,
    fetchFn,
    searchFn,
}: MemoriesPageProps) {
    const posthog = usePostHog();
    const [filter, setFilter] = React.useState<string>('all');
    const [displayLimit, setDisplayLimit] = React.useState<number>(PAGE_SIZE);

    const [searchQuery, setSearchQuery] = React.useState('');
    const [activeSearchQuery, setActiveSearchQuery] = React.useState('');
    const [searchResults, setSearchResults] = React.useState<Memory[] | null>(null);
    const [isSearching, setIsSearching] = React.useState(false);

    const handleFilterChange = (newFilter: string) => {
        setFilter(newFilter);
        setDisplayLimit(PAGE_SIZE);
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
        const sourceList = searchResults !== null ? searchResults : memories;
        if (filter === 'all') return sourceList;
        if (filter === 'RESOLVED') {
            return sourceList.filter((m) => m.status === 'RESOLVED');
        }
        return sourceList.filter((m) => getMemoryCategory(m) === filter);
    }, [memories, searchResults, filter]);

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
