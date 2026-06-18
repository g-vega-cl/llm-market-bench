import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import type * as React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { EventChainPage } from './EventChainPage';

// Mock TanStack Router's Link
vi.mock('@tanstack/react-router', () => ({
    Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
        <a href={to}>{children}</a>
    ),
}));

const mockFocusMemory = {
    id: 'm1',
    content: 'Focus memory content',
    created_at: '2026-05-25T12:00:00.000Z',
    formattedDate: 'May 25, 2026, 12:00 PM ET',
    metadata: { type: 'consensus_event' },
};

const mockFullChain = {
    chain: [
        {
            id: 'm1',
            content: 'Focus memory content',
            created_at: '2026-05-25T12:00:00.000Z',
            formattedDate: 'May 25, 2026, 12:00 PM ET',
            metadata: { type: 'consensus_event' },
        },
        {
            id: 'm2',
            content: 'Next memory content',
            created_at: '2026-05-26T12:00:00.000Z',
            formattedDate: 'May 26, 2026, 12:00 PM ET',
            metadata: { type: 'post_mortem' },
        },
    ],
    targetMemory: mockFocusMemory,
};

describe('EventChainPage - Loading Indicator', () => {
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

    it('should show loading indicator while fetching other memories, and hide it when finished', async () => {
        const resolveFetchRef = { current: null as ((value: typeof mockFullChain) => void) | null };
        const fetchPromise = new Promise<typeof mockFullChain>((resolve) => {
            resolveFetchRef.current = resolve;
        });

        const fetchFn = vi.fn().mockImplementation(() => fetchPromise);

        const initialData = {
            chain: [mockFocusMemory],
            targetMemory: mockFocusMemory,
        };

        render(
            <QueryClientProvider client={queryClient}>
                <EventChainPage memoryId="m1" initialData={initialData} fetchFn={fetchFn} />
            </QueryClientProvider>,
        );

        // 1. Initial render with target memory only
        expect(screen.getByText('Focus memory content')).toBeInTheDocument();
        expect(screen.queryByText('Next memory content')).not.toBeInTheDocument();

        // 2. Loading indicator is visible
        await waitFor(() => {
            expect(screen.getByText(/Loading other memories in this chain/i)).toBeInTheDocument();
            expect(screen.getByText(/Loading chain/i)).toBeInTheDocument();
        });

        // 3. Resolve fetch
        resolveFetchRef.current?.(mockFullChain);

        // 4. Wait for query to update
        await waitFor(() => {
            expect(screen.getByText('Next memory content')).toBeInTheDocument();
        });

        // 5. Loading indicator should be gone
        expect(screen.queryByText(/Loading other memories in this chain/i)).not.toBeInTheDocument();
        expect(screen.queryByText(/Loading chain/i)).not.toBeInTheDocument();
    });
});
