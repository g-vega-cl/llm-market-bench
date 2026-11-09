import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { PaginatedReasoningLogs } from '../api/fetch-reasoning-logs';
import { ReasoningPage } from './ReasoningPage';

const mockCapture = vi.fn();
vi.mock('@posthog/react', () => ({
    usePostHog: () => ({
        capture: mockCapture,
    }),
}));

const queryOverrides: { isFetching?: boolean; hasNextPage?: boolean } = {};
const lastQueryOptions: { initialDataUpdatedAt?: number } = {};

vi.mock('@tanstack/react-query', async (importOriginal) => {
    const original = await importOriginal<typeof import('@tanstack/react-query')>();
    return {
        ...original,
        useInfiniteQuery: vi.fn().mockImplementation((opts) => {
            lastQueryOptions.initialDataUpdatedAt = opts.initialDataUpdatedAt;
            return {
                data: opts.initialData,
                fetchNextPage: vi.fn(),
                hasNextPage: queryOverrides.hasNextPage ?? false,
                isFetching: queryOverrides.isFetching ?? false,
                isFetchingNextPage: false,
                isPending: false,
                error: null,
            };
        }),
    };
});

vi.mock('../components/HumanFriendlyPrompt', () => ({
    HumanFriendlyPrompt: () => <div>Prompt Content</div>,
}));

vi.mock('../components/HumanFriendlyResponse', () => ({
    HumanFriendlyResponse: () => <div>Response Content</div>,
}));

describe('ReasoningPage Model Filter', () => {
    const mockData: PaginatedReasoningLogs = {
        data: [
            {
                id: '1',
                task_type: 'CONSENSUS',
                model_provider: 'anthropic',
                model_name: 'claude-3-5-sonnet',
                prompt: { text: 'Test prompt 1' },
                response: { text: 'Test response 1' },
                created_at: '2026-06-28T12:00:00Z',
                metadata: { ticker: 'NVDA' },
            },
            {
                id: '2',
                task_type: 'VERIFICATION',
                model_provider: 'openai',
                model_name: 'gpt-4o',
                prompt: { text: 'Test prompt 2' },
                response: { text: 'Test response 2' },
                created_at: '2026-06-28T12:05:00Z',
                metadata: { ticker: 'AAPL' },
            },
        ],
        hasMore: false,
        nextCursor: null,
    };

    it('renders model filter dropdown and filters logs by selected model', () => {
        render(<ReasoningPage initialData={mockData} fetchFn={async () => mockData} />);

        // Check both items rendered initially
        expect(screen.getByText('NVDA')).toBeInTheDocument();
        expect(screen.getByText('AAPL')).toBeInTheDocument();

        // Check dropdown options
        const select = screen.getByRole('combobox', {
            name: /filter reasoning traces by model/i,
        });
        expect(select).toBeInTheDocument();

        // Change select value to gpt-4o
        fireEvent.change(select, { target: { value: 'gpt-4o' } });

        // NVDA (claude-3-5-sonnet) should no longer be visible, AAPL (gpt-4o) should remain
        expect(screen.queryByText('NVDA')).toBeNull();
        expect(screen.getByText('AAPL')).toBeInTheDocument();

        // PostHog capture verified
        expect(mockCapture).toHaveBeenCalledWith('reasoning_model_filtered', {
            model: 'gpt-4o',
        });
    });

    it('marks the SSR slice stale so it expands on mount', () => {
        render(<ReasoningPage initialData={mockData} fetchFn={async () => mockData} />);
        expect(lastQueryOptions.initialDataUpdatedAt).toBe(0);
    });

    it('does not flash "No logs found" while the SSR slice is still expanding', () => {
        queryOverrides.isFetching = true;
        render(<ReasoningPage initialData={mockData} fetchFn={async () => mockData} />);
        fireEvent.change(screen.getByRole('combobox'), { target: { value: 'gpt-4o' } });
        // Tab filter with no match in the slice
        fireEvent.click(screen.getAllByText('CONSENSUS')[0]);
        expect(screen.queryByText('No logs found for this category.')).toBeNull();
        queryOverrides.isFetching = false;
    });
});
