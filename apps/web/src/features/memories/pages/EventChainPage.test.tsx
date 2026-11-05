import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import type * as React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { EventChainPage } from './EventChainPage';

// Mock TanStack Router's Link and useNavigate
vi.mock('@tanstack/react-router', () => ({
    Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
        <a href={to}>{children}</a>
    ),
    useNavigate: () => vi.fn(),
}));

const mockFocusMemory = {
    id: 'm1',
    content: 'Focus memory content',
    created_at: '2026-05-25T12:00:00.000Z',
    formattedDate: 'May 25, 2026, 12:00 PM ET',
    elapsedFromRoot: 'Origin Catalyst',
    elapsedFromPreceding: 'Origin',
    isRoot: true,
    modelsInvolved: ['Claude-3-5-Sonnet', 'Gemini-1-5-Pro'],
    metadata: {
        type: 'consensus_event',
        ticker: 'TSLA',
        impact: 'BULLISH',
    },
};

const mockFullChain = {
    chain: [
        mockFocusMemory,
        {
            id: 'm2',
            content: 'Next memory content',
            created_at: '2026-05-26T14:30:00.000Z',
            formattedDate: 'May 26, 2026, 02:30 PM ET',
            elapsedFromRoot: '+1d 2h later',
            elapsedFromPreceding: '+1d 2h later',
            isRoot: false,
            relationship_type: 'UPDATE',
            modelsInvolved: ['DeepSeek-V3'],
            metadata: {
                type: 'post_mortem',
                debate: {
                    adversary_model: 'Claude-3-5-Haiku',
                    counter_thesis: 'Supply chain headwinds persist.',
                },
            },
        },
    ],
    targetMemory: mockFocusMemory,
};

describe('EventChainPage', () => {
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

    it('should render thought journey timeline with model badges, dates, and directional relationship connector', async () => {
        const fetchFn = vi.fn().mockResolvedValue(mockFullChain);

        render(
            <QueryClientProvider client={queryClient}>
                <EventChainPage memoryId="m1" initialData={mockFullChain} fetchFn={fetchFn} />
            </QueryClientProvider>,
        );

        // Step headers
        expect(screen.getByText(/STEP 1 • CATALYST ORIGIN/i)).toBeInTheDocument();
        expect(screen.getByText(/STEP 2/i)).toBeInTheDocument();

        // Focus indicator
        expect(screen.getByText(/You selected this event/i)).toBeInTheDocument();

        // Model Badges
        expect(screen.getByText(/🤖 Claude-3-5-Sonnet/i)).toBeInTheDocument();
        expect(screen.getByText(/🤖 Gemini-1-5-Pro/i)).toBeInTheDocument();
        expect(screen.getByText(/🤖 DeepSeek-V3/i)).toBeInTheDocument();

        // Directional relationship badge
        expect(screen.getByText('UPDATE')).toBeInTheDocument();
        expect(screen.getByText('+1d 2h later')).toBeInTheDocument();

        // Debate details
        expect(screen.getByText(/Challenger: Claude-3-5-Haiku/i)).toBeInTheDocument();
        expect(screen.getByText(/Supply chain headwinds persist/i)).toBeInTheDocument();

        // Chat interrogation button
        expect(screen.getByText(/Interrogate Chain in AI Chat →/i)).toBeInTheDocument();
    });
});
