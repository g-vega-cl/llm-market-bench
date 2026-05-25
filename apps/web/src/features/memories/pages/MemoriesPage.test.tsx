import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import type * as React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchNewMemories } from '../api/fetch-memories';
import { MemoriesPage } from './MemoriesPage';

// Robust mock for localStorage in test environments
class LocalStorageMock implements Storage {
    private store: Record<string, string> = {};

    get length() {
        return Object.keys(this.store).length;
    }

    clear() {
        this.store = {};
    }

    getItem(key: string) {
        return this.store[key] || null;
    }

    setItem(key: string, value: string) {
        this.store[key] = String(value);
    }

    removeItem(key: string) {
        delete this.store[key];
    }

    key(index: number) {
        return Object.keys(this.store)[index] || null;
    }
}

global.localStorage = new LocalStorageMock();

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

// Mock API functions
vi.mock('../api/fetch-memories', () => ({
    fetchMemories: vi.fn(),
    fetchNewMemories: vi.fn(),
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

describe('MemoriesPage (Solution B Cache + Delta Sync)', () => {
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
        localStorage.clear();
    });

    it('renders with initialData from localStorage and does not show loader', async () => {
        // Seed localStorage
        localStorage.setItem('benchify_memories_v1', JSON.stringify(mockMemories));

        // Mock fetchNewMemories to return empty array (no new deltas)
        vi.mocked(fetchNewMemories).mockResolvedValue([]);

        render(
            <QueryClientProvider client={queryClient}>
                <MemoriesPage fetchFn={vi.fn()} />
            </QueryClientProvider>,
        );

        // Page should render mock memories instantly
        expect(screen.getByText('Market event consensus description')).toBeInTheDocument();
        expect(screen.getByText('Post mortem audit details')).toBeInTheDocument();

        // fetchNewMemories should be called in background on mount with the latest memory's timestamp
        expect(fetchNewMemories).toHaveBeenCalledWith('2026-05-25T12:00:00.000Z');
    });

    it('filters memories 100% client-side without making new fetch calls', async () => {
        localStorage.setItem('benchify_memories_v1', JSON.stringify(mockMemories));
        vi.mocked(fetchNewMemories).mockResolvedValue([]);

        render(
            <QueryClientProvider client={queryClient}>
                <MemoriesPage fetchFn={vi.fn()} />
            </QueryClientProvider>,
        );

        // Initial render lists all
        expect(screen.getByText('Market event consensus description')).toBeInTheDocument();
        expect(screen.getByText('Post mortem audit details')).toBeInTheDocument();

        // Clear mock calls to verify tab changes trigger NO requests
        vi.mocked(fetchNewMemories).mockClear();
        const fetchFnMock = vi.fn();

        // Click "Events" tab
        const eventsBtn = screen.getByText('Events');
        fireEvent.click(eventsBtn);

        // Events filter should be active, hiding the Post Mortem
        expect(screen.getByText('Market event consensus description')).toBeInTheDocument();
        expect(screen.queryByText('Post mortem audit details')).not.toBeInTheDocument();

        // Click "Post-Mortems" tab
        const pmBtn = screen.getByText('Post-Mortems');
        fireEvent.click(pmBtn);

        // Post-Mortems filter should be active, hiding the Event
        expect(screen.queryByText('Market event consensus description')).not.toBeInTheDocument();
        expect(screen.getByText('Post mortem audit details')).toBeInTheDocument();

        // Assert 0 network/fetch requests were triggered by these tab changes!
        expect(fetchNewMemories).not.toHaveBeenCalled();
        expect(fetchFnMock).not.toHaveBeenCalled();
    });
});
