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
vi.mock('@posthog/react', () => ({
    usePostHog: () => ({
        capture: vi.fn(),
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
});
