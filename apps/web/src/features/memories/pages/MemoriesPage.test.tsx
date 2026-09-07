import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import type * as React from 'react';
import { renderToString } from 'react-dom/server';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoriesPage } from './MemoriesPage';

// Mock TanStack Router's Link
vi.mock('@tanstack/react-router', () => ({
    Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
        <a href={to}>{children}</a>
    ),
}));

// Mock PostHog
const mockCapture = vi.fn();
vi.mock('@posthog/react', () => ({
    usePostHog: () => ({
        capture: mockCapture,
    }),
}));

const mockMemories = [
    {
        id: 'm1',
        content: 'Market event consensus description',
        created_at: '2026-05-25T12:00:00.000Z',
        metadata: { type: 'consensus_event' },
        status: 'ACTIVE',
        parent_id: null,
        relationship_type: null,
        relevance_score: null,
        memory_type: 'MARKET_EVENT',
        importance_score: null,
        target_date: null,
    },
    {
        id: 'm2',
        content: 'Post mortem audit details',
        created_at: '2026-05-24T12:00:00.000Z',
        metadata: { type: 'post_mortem' },
        status: 'RESOLVED',
        parent_id: null,
        relationship_type: null,
        relevance_score: null,
        memory_type: 'POST_MORTEM',
        importance_score: null,
        target_date: null,
    },
];

describe('MemoriesPage (SSR-First)', () => {
    let queryClient: QueryClient;

    beforeEach(() => {
        queryClient = new QueryClient({
            defaultOptions: {
                queries: {
                    retry: false,
                    gcTime: 0,
                },
            },
        });
        vi.clearAllMocks();
    });

    it('renders memories directly in the SSR HTML output without showing a loading skeleton', () => {
        const html = renderToString(
            <QueryClientProvider client={queryClient}>
                <MemoriesPage
                    initialMemories={mockMemories}
                    initialHasMore={false}
                    initialCursor={null}
                    fetchFn={vi.fn()}
                />
            </QueryClientProvider>,
        );

        // SSR should render mock memories text directly in the HTML markup
        expect(html).toContain('Market event consensus description');
        expect(html).toContain('Post mortem audit details');
        expect(html).not.toContain('No memories found in this category');
    });

    it('renders initial memories on mount', () => {
        render(
            <QueryClientProvider client={queryClient}>
                <MemoriesPage
                    initialMemories={mockMemories}
                    initialHasMore={false}
                    initialCursor={null}
                    fetchFn={vi.fn()}
                />
            </QueryClientProvider>,
        );

        expect(screen.getByText('Market event consensus description')).toBeInTheDocument();
        expect(screen.getByText('Post mortem audit details')).toBeInTheDocument();
    });

    it('filters memories 100% client-side instantly on tab click', async () => {
        render(
            <QueryClientProvider client={queryClient}>
                <MemoriesPage
                    initialMemories={mockMemories}
                    initialHasMore={false}
                    initialCursor={null}
                    fetchFn={vi.fn()}
                />
            </QueryClientProvider>,
        );

        expect(screen.getByText('Market event consensus description')).toBeInTheDocument();
        expect(screen.getByText('Post mortem audit details')).toBeInTheDocument();

        // Click "Events" filter tab
        const eventsBtn = screen.getByText('Events');
        fireEvent.click(eventsBtn);

        // Active filter should hide "Post-Mortems"
        expect(screen.getByText('Market event consensus description')).toBeInTheDocument();
        expect(screen.queryByText('Post mortem audit details')).not.toBeInTheDocument();

        // Click "Post-Mortems" filter tab
        const pmBtn = screen.getByText('Post-Mortems');
        fireEvent.click(pmBtn);

        // Active filter should hide "Events"
        expect(screen.queryByText('Market event consensus description')).not.toBeInTheDocument();
        expect(screen.getByText('Post mortem audit details')).toBeInTheDocument();

        // Click "Resolved" filter tab
        const resolvedBtn = screen.getByText('Resolved');
        fireEvent.click(resolvedBtn);

        // Active filter should show resolved memories and hide active memories
        expect(screen.getByText('Post mortem audit details')).toBeInTheDocument();
        expect(screen.queryByText('Market event consensus description')).not.toBeInTheDocument();
    });

    it('fetches subsequent pages dynamically via fetchFn when clicking load more', async () => {
        const nextPageMemory = {
            id: 'm3',
            content: 'Next page paginated detail',
            created_at: '2026-05-23T12:00:00.000Z',
            metadata: { type: 'consensus_event' },
            status: 'ACTIVE',
            parent_id: null,
            relationship_type: null,
            relevance_score: null,
            memory_type: 'MARKET_EVENT',
            importance_score: null,
            target_date: null,
        };

        const fetchFnMock = vi.fn().mockResolvedValue({
            data: [nextPageMemory],
            hasMore: false,
            nextCursor: null,
        });

        render(
            <QueryClientProvider client={queryClient}>
                <MemoriesPage
                    initialMemories={mockMemories}
                    initialHasMore={true}
                    initialCursor="cursor-123"
                    fetchFn={fetchFnMock}
                />
            </QueryClientProvider>,
        );

        // Load More button should be visible
        const loadMoreBtn = screen.getByText('Load More');
        expect(loadMoreBtn).toBeInTheDocument();

        // Click Load More
        fireEvent.click(loadMoreBtn);

        // Fetch function should be called with the correct pageParam cursor
        expect(fetchFnMock).toHaveBeenCalledWith('cursor-123', undefined);

        // Wait for the new memory to appear in the list
        await waitFor(() => {
            expect(screen.getByText('Next page paginated detail')).toBeInTheDocument();
        });

        // The initial memories should still be visible (appended/concatenated)
        expect(screen.getByText('Market event consensus description')).toBeInTheDocument();
    });

    it('handles search query submission and clears results correctly', async () => {
        const searchResultsMock = [
            {
                id: 'm3',
                content: 'Trump energy deal nuclear',
                created_at: '2026-05-23T12:00:00.000Z',
                metadata: { type: 'consensus_event' },
                status: 'ACTIVE',
                parent_id: null,
                relationship_type: null,
                relevance_score: null,
                memory_type: 'MARKET_EVENT',
                importance_score: null,
                target_date: null,
                similarity: 0.84,
            },
        ];

        const searchFnMock = vi.fn().mockResolvedValue(searchResultsMock);

        render(
            <QueryClientProvider client={queryClient}>
                <MemoriesPage
                    initialMemories={mockMemories}
                    initialHasMore={false}
                    initialCursor={null}
                    fetchFn={vi.fn()}
                    searchFn={searchFnMock}
                />
            </QueryClientProvider>,
        );

        // Standard browse mode shows initial memories
        expect(screen.getByText('Market event consensus description')).toBeInTheDocument();
        expect(screen.getByText('Post mortem audit details')).toBeInTheDocument();

        // Find input and type a query
        const searchInput = screen.getByPlaceholderText(/Search memories/i);
        fireEvent.change(searchInput, { target: { value: 'Trump energy' } });

        // Submit form
        const searchBtn = screen.getByRole('button', { name: 'Search' });
        fireEvent.click(searchBtn);

        // Assert searchFn is called with trimmed query
        expect(searchFnMock).toHaveBeenCalledWith('Trump energy');

        // Wait for results to render
        await waitFor(() => {
            expect(screen.getByText('Trump energy deal nuclear')).toBeInTheDocument();
        });

        // Similarity badge should be rendered (84%)
        expect(screen.getByText('Match: 84%')).toBeInTheDocument();

        // Initial memories should be hidden during search mode
        expect(screen.queryByText('Market event consensus description')).not.toBeInTheDocument();

        // Reset/Clear search
        const resetBtn = screen.getByText('Reset Search');
        fireEvent.click(resetBtn);

        // Standard feed is restored
        expect(screen.getByText('Market event consensus description')).toBeInTheDocument();
        expect(screen.queryByText('Trump energy deal nuclear')).not.toBeInTheDocument();
    });

    it('sorts memories by importance (highest first and lowest first)', () => {
        const scoredMemories = [
            {
                id: 's1',
                content: 'Low importance event',
                created_at: '2026-05-25T12:00:00.000Z',
                metadata: {},
                status: 'ACTIVE',
                parent_id: null,
                relationship_type: null,
                relevance_score: null,
                memory_type: 'MARKET_EVENT',
                importance_score: 3,
                target_date: null,
            },
            {
                id: 's2',
                content: 'High importance event',
                created_at: '2026-05-24T12:00:00.000Z',
                metadata: {},
                status: 'ACTIVE',
                parent_id: null,
                relationship_type: null,
                relevance_score: null,
                memory_type: 'MARKET_EVENT',
                importance_score: 9,
                target_date: null,
            },
            {
                id: 's3',
                content: 'Medium importance event',
                created_at: '2026-05-23T12:00:00.000Z',
                metadata: {},
                status: 'ACTIVE',
                parent_id: null,
                relationship_type: null,
                relevance_score: null,
                memory_type: 'MARKET_EVENT',
                importance_score: 6,
                target_date: null,
            },
        ];

        render(
            <QueryClientProvider client={queryClient}>
                <MemoriesPage
                    initialMemories={scoredMemories}
                    initialHasMore={false}
                    initialCursor={null}
                    fetchFn={vi.fn()}
                />
            </QueryClientProvider>,
        );

        const sortSelect = screen.getByLabelText(/sort by/i);

        // Change sort to 'importance_desc'
        fireEvent.change(sortSelect, { target: { value: 'importance_desc' } });

        const cardsAfterSortDesc = screen.getAllByText(/importance event/i);
        expect(cardsAfterSortDesc[0]).toHaveTextContent('High importance event');
        expect(cardsAfterSortDesc[1]).toHaveTextContent('Medium importance event');
        expect(cardsAfterSortDesc[2]).toHaveTextContent('Low importance event');

        // Check PostHog tracking
        expect(mockCapture).toHaveBeenCalledWith('memories_sort_changed', {
            sort_by: 'importance_desc',
            result_count: 3,
        });

        // Change sort to 'importance_asc'
        fireEvent.change(sortSelect, { target: { value: 'importance_asc' } });

        const cardsAfterSortAsc = screen.getAllByText(/importance event/i);
        expect(cardsAfterSortAsc[0]).toHaveTextContent('Low importance event');
        expect(cardsAfterSortAsc[1]).toHaveTextContent('Medium importance event');
        expect(cardsAfterSortAsc[2]).toHaveTextContent('High importance event');
    });

    it('filters memories by date presets (7D, 30D, 90D)', () => {
        const now = Date.now();
        const datedMemories = [
            {
                id: 'd1',
                content: 'Memory from 3 days ago',
                created_at: new Date(now - 3 * 86400000).toISOString(),
                metadata: {},
                status: 'ACTIVE',
                parent_id: null,
                relationship_type: null,
                relevance_score: null,
                memory_type: 'MARKET_EVENT',
                importance_score: 5,
                target_date: null,
            },
            {
                id: 'd2',
                content: 'Memory from 20 days ago',
                created_at: new Date(now - 20 * 86400000).toISOString(),
                metadata: {},
                status: 'ACTIVE',
                parent_id: null,
                relationship_type: null,
                relevance_score: null,
                memory_type: 'MARKET_EVENT',
                importance_score: 5,
                target_date: null,
            },
            {
                id: 'd3',
                content: 'Memory from 60 days ago',
                created_at: new Date(now - 60 * 86400000).toISOString(),
                metadata: {},
                status: 'ACTIVE',
                parent_id: null,
                relationship_type: null,
                relevance_score: null,
                memory_type: 'MARKET_EVENT',
                importance_score: 5,
                target_date: null,
            },
        ];

        render(
            <QueryClientProvider client={queryClient}>
                <MemoriesPage
                    initialMemories={datedMemories}
                    initialHasMore={false}
                    initialCursor={null}
                    fetchFn={vi.fn()}
                />
            </QueryClientProvider>,
        );

        // Click "7D" preset
        fireEvent.click(screen.getByText('7D'));
        expect(screen.getByText('Memory from 3 days ago')).toBeInTheDocument();
        expect(screen.queryByText('Memory from 20 days ago')).not.toBeInTheDocument();
        expect(screen.queryByText('Memory from 60 days ago')).not.toBeInTheDocument();

        expect(mockCapture).toHaveBeenCalledWith('memories_date_preset_changed', {
            date_preset: '7d',
            result_count: 1,
        });

        // Click "30D" preset
        fireEvent.click(screen.getByText('30D'));
        expect(screen.getByText('Memory from 3 days ago')).toBeInTheDocument();
        expect(screen.getByText('Memory from 20 days ago')).toBeInTheDocument();
        expect(screen.queryByText('Memory from 60 days ago')).not.toBeInTheDocument();

        // Click "All Time"
        fireEvent.click(screen.getByText('All Time'));
        expect(screen.getByText('Memory from 3 days ago')).toBeInTheDocument();
        expect(screen.getByText('Memory from 20 days ago')).toBeInTheDocument();
        expect(screen.getByText('Memory from 60 days ago')).toBeInTheDocument();
    });

    it('filters memories by high impact (8+) toggle and fires telemetry', () => {
        const impactMemories = [
            {
                id: 'i1',
                content: 'Standard routine memory',
                created_at: '2026-05-25T12:00:00.000Z',
                metadata: {},
                status: 'ACTIVE',
                parent_id: null,
                relationship_type: null,
                relevance_score: null,
                memory_type: 'MARKET_EVENT',
                importance_score: 6,
                target_date: null,
            },
            {
                id: 'i2',
                content: 'Crucial macro catalyst',
                created_at: '2026-05-24T12:00:00.000Z',
                metadata: {},
                status: 'ACTIVE',
                parent_id: null,
                relationship_type: null,
                relevance_score: null,
                memory_type: 'MARKET_EVENT',
                importance_score: 9,
                target_date: null,
            },
        ];

        render(
            <QueryClientProvider client={queryClient}>
                <MemoriesPage
                    initialMemories={impactMemories}
                    initialHasMore={false}
                    initialCursor={null}
                    fetchFn={vi.fn()}
                />
            </QueryClientProvider>,
        );

        expect(screen.getByText('Standard routine memory')).toBeInTheDocument();
        expect(screen.getByText('Crucial macro catalyst')).toBeInTheDocument();

        // Toggle 8+ Impact
        fireEvent.click(screen.getByText(/8\+ Impact/i));

        expect(screen.queryByText('Standard routine memory')).not.toBeInTheDocument();
        expect(screen.getByText('Crucial macro catalyst')).toBeInTheDocument();

        expect(mockCapture).toHaveBeenCalledWith('memories_high_impact_toggled', {
            enabled: true,
            result_count: 1,
        });

        // Untoggle
        fireEvent.click(screen.getByText(/8\+ Impact/i));
        expect(screen.getByText('Standard routine memory')).toBeInTheDocument();
        expect(screen.getByText('Crucial macro catalyst')).toBeInTheDocument();
    });

    it('runs delta-sync on mount and prepends newly appended memories', async () => {
        const deltaNewMemory = {
            id: 'd-new',
            content: 'Brand new morning catalyst memory',
            created_at: '2026-05-26T12:00:00.000Z',
            metadata: {},
            status: 'ACTIVE',
            parent_id: null,
            relationship_type: null,
            relevance_score: null,
            memory_type: 'MARKET_EVENT',
            importance_score: 8,
            target_date: null,
        };

        const deltaSyncFnMock = vi.fn().mockResolvedValue([deltaNewMemory]);

        render(
            <QueryClientProvider client={queryClient}>
                <MemoriesPage
                    initialMemories={mockMemories}
                    initialHasMore={false}
                    initialCursor={null}
                    fetchFn={vi.fn()}
                    deltaSyncFn={deltaSyncFnMock}
                />
            </QueryClientProvider>,
        );

        // Assert deltaSyncFn was called with the newest created_at timestamp
        expect(deltaSyncFnMock).toHaveBeenCalledWith('2026-05-25T12:00:00.000Z');

        // New memory should appear in DOM
        await waitFor(() => {
            expect(screen.getByText('Brand new morning catalyst memory')).toBeInTheDocument();
        });

        // Old memories should still be present
        expect(screen.getByText('Market event consensus description')).toBeInTheDocument();
    });
});
