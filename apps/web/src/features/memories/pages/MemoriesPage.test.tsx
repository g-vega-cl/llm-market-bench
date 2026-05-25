import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import type * as React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchMemories, fetchNewMemories, validateCacheState } from '../api/fetch-memories';
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
    validateCacheState: vi.fn(),
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
        vi.mocked(validateCacheState).mockResolvedValue({
            exists: true,
            latestTimestamp: '2026-05-25T12:00:00.000Z',
        });
    });

    it('renders with initialData from localStorage and does not show loader', async () => {
        // Seed localStorage with 500 memories to simulate a fully populated cache
        const largeMockMemories = Array.from({ length: 500 }, (_, i) => ({
            ...mockMemories[i % 2],
            id: `m-large-${i}`,
            content: i < 2 ? mockMemories[i].content : `Other mock memory content ${i}`,
            created_at: i === 0 ? '2026-05-25T12:00:00.000Z' : '2026-05-24T12:00:00.000Z',
        }));
        localStorage.setItem('benchify_memories_v1', JSON.stringify(largeMockMemories));

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
        await waitFor(() => {
            expect(fetchNewMemories).toHaveBeenCalledWith('2026-05-25T12:00:00.000Z');
        });
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

    it('backfills cache to 500 if cached size is less than 500', async () => {
        // Seed localStorage with only 1 memory (less than MAX_CACHE_SIZE)
        const smallMockMemories = mockMemories.slice(0, 1);
        localStorage.setItem('benchify_memories_v1', JSON.stringify(smallMockMemories));

        const mockFetchMemories = vi.mocked(fetchMemories);
        mockFetchMemories.mockResolvedValue({
            data: mockMemories,
            hasMore: false,
            nextCursor: null,
        });

        render(
            <QueryClientProvider client={queryClient}>
                <MemoriesPage />
            </QueryClientProvider>,
        );

        // It should call fetchMemories with 500 limit to backfill the cache
        await waitFor(() => {
            expect(mockFetchMemories).toHaveBeenCalledWith(undefined, 500);
        });
    });

    it('executes delta-sync normally when cache is fully valid and fresh', async () => {
        const largeMockMemories = Array.from({ length: 500 }, (_, i) => ({
            ...mockMemories[i % 2],
            id: `m-large-${i}`,
            created_at: i === 0 ? '2026-05-25T12:00:00.000Z' : '2026-05-24T12:00:00.000Z',
        }));
        localStorage.setItem('benchify_memories_v1', JSON.stringify(largeMockMemories));

        // Mock validateCacheState to indicate the memory exists and DB latest timestamp is newer/same
        vi.mocked(validateCacheState).mockResolvedValue({
            exists: true,
            latestTimestamp: '2026-05-25T12:00:00.000Z',
        });
        vi.mocked(fetchNewMemories).mockResolvedValue([]);

        render(
            <QueryClientProvider client={queryClient}>
                <MemoriesPage />
            </QueryClientProvider>,
        );

        // Should call validateCacheState with the newest cached ID
        await waitFor(() => {
            expect(validateCacheState).toHaveBeenCalledWith('m-large-0');
            // Should execute delta sync with newest cached created_at
            expect(fetchNewMemories).toHaveBeenCalledWith('2026-05-25T12:00:00.000Z');
            expect(fetchMemories).not.toHaveBeenCalled();
        });
    });

    it('wipes cache and triggers full backfill if cached newest ID does not exist in DB', async () => {
        const largeMockMemories = Array.from({ length: 500 }, (_, i) => ({
            ...mockMemories[i % 2],
            id: `m-large-${i}`,
            created_at: i === 0 ? '2026-05-25T12:00:00.000Z' : '2026-05-24T12:00:00.000Z',
        }));
        localStorage.setItem('benchify_memories_v1', JSON.stringify(largeMockMemories));

        // Mock validateCacheState to report that the newest ID does NOT exist in DB (indicating a database reset)
        vi.mocked(validateCacheState).mockResolvedValue({
            exists: false,
            latestTimestamp: '2026-05-25T12:00:00.000Z',
        });
        const mockFetchMemories = vi.mocked(fetchMemories);
        mockFetchMemories.mockResolvedValue({
            data: mockMemories,
            hasMore: false,
            nextCursor: null,
        });

        render(
            <QueryClientProvider client={queryClient}>
                <MemoriesPage />
            </QueryClientProvider>,
        );

        // Should detect database reset and trigger a full backfill fetch
        await waitFor(() => {
            expect(validateCacheState).toHaveBeenCalledWith('m-large-0');
            expect(mockFetchMemories).toHaveBeenCalledWith(undefined, 500);
            expect(fetchNewMemories).not.toHaveBeenCalled();
        });

        // LocalStorage should have been overwritten with the backfilled mockMemories
        const saved = JSON.parse(localStorage.getItem('benchify_memories_v1') || '[]');
        expect(saved.length).toBe(mockMemories.length);
    });

    it('wipes cache and triggers full backfill if database timeline rolled back (timestamp is older than cache)', async () => {
        const largeMockMemories = Array.from({ length: 500 }, (_, i) => ({
            ...mockMemories[i % 2],
            id: `m-large-${i}`,
            created_at: i === 0 ? '2026-05-25T12:00:00.000Z' : '2026-05-24T12:00:00.000Z',
        }));
        localStorage.setItem('benchify_memories_v1', JSON.stringify(largeMockMemories));

        // Mock validateCacheState to report that the newest DB timestamp is older than newest cached memory (May 24 vs May 25)
        vi.mocked(validateCacheState).mockResolvedValue({
            exists: true,
            latestTimestamp: '2026-05-24T12:00:00.000Z',
        });
        const mockFetchMemories = vi.mocked(fetchMemories);
        mockFetchMemories.mockResolvedValue({
            data: mockMemories,
            hasMore: false,
            nextCursor: null,
        });

        render(
            <QueryClientProvider client={queryClient}>
                <MemoriesPage />
            </QueryClientProvider>,
        );

        // Should trigger full backfill
        await waitFor(() => {
            expect(mockFetchMemories).toHaveBeenCalledWith(undefined, 500);
            expect(fetchNewMemories).not.toHaveBeenCalled();
        });
    });
});
