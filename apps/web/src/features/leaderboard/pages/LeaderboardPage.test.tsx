import type { LLMLeaderboardRow } from '@llm-market-bench/database';
import { useQuery } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { LeaderboardPage } from './LeaderboardPage';

// Mock Tanstack Query's useQuery
vi.mock('@tanstack/react-query', async (importOriginal) => {
    const original = await importOriginal<typeof import('@tanstack/react-query')>();
    return {
        ...original,
        useQuery: vi.fn().mockImplementation(({ initialData }) => ({
            data: initialData || [],
            isLoading: false,
            isFetching: false,
        })),
    };
});

// Mock Server Fn
vi.mock('@tanstack/react-start', () => ({
    createServerFn: () => ({
        inputValidator: () => ({
            handler: (fn: unknown) => fn,
        }),
    }),
}));

const mockLeaderboardData: LLMLeaderboardRow[] = [
    {
        model_name: 'deepseek-v4-pro',
        total_equity: 10820,
        return_pct: 8.2,
        realized_pnl: 820,
        win_rate: 68.2,
        total_trades: 15,
        verifier_approval_rate: 95.4,
        average_confidence: 85.0,
        api_success_rate: 100.0,
        trading_activity_rate: 90.0,
        trading_performance_score: 85.2,
        reasoning_quality_score: 92.3,
        consistency_score: 97.0,
        composite_score: 89.5,
    },
    {
        model_name: 'MiniMax-M3',
        total_equity: 10600,
        return_pct: 6.0,
        realized_pnl: 600,
        win_rate: 60.0,
        total_trades: 10,
        verifier_approval_rate: null, // ignored verifier score
        average_confidence: 80.0,
        api_success_rate: 100.0,
        trading_activity_rate: 85.0,
        trading_performance_score: 80.0,
        reasoning_quality_score: 80.0,
        consistency_score: 95.0,
        composite_score: 85.0,
    },
    {
        model_name: 'gpt-5.4-nano',
        total_equity: 10480,
        return_pct: 4.8,
        realized_pnl: 480,
        win_rate: 62.5,
        total_trades: 12,
        verifier_approval_rate: 91.2,
        average_confidence: 80.0,
        api_success_rate: 100.0,
        trading_activity_rate: 85.0,
        trading_performance_score: 79.5,
        reasoning_quality_score: 87.8,
        consistency_score: 95.5,
        composite_score: 84.2,
    },
];

describe('LeaderboardPage', () => {
    it('renders the leaderboard correctly with podium and table', () => {
        render(<LeaderboardPage initialData={mockLeaderboardData} />);

        // Should render main headings
        expect(screen.getByText('LLM Leaderboard')).toBeDefined();

        // Should render podium placements
        expect(screen.getByText('Place #1')).toBeDefined();
        expect(screen.getByText('Place #2')).toBeDefined();
        expect(screen.getByText('Place #3')).toBeDefined();

        // Should render model display names from config or fallback
        expect(screen.getAllByText('DeepSeek (v4-pro)').length).toBeGreaterThan(0);
        expect(screen.getAllByText('MiniMax (M3)').length).toBeGreaterThan(0);
        expect(screen.getAllByText('OpenAI (gpt-5.4-nano)').length).toBeGreaterThan(0);

        // Should render score percentages
        expect(screen.getAllByText('89.5%').length).toBeGreaterThan(0);
        expect(screen.getAllByText('85.0%').length).toBeGreaterThan(0);
        expect(screen.getAllByText('84.2%').length).toBeGreaterThan(0);

        // Should render em-dash (—) for MiniMax verifier rate
        expect(screen.getAllByText('—').length).toBeGreaterThan(0);
    });

    it('enables comparing two selected models side-by-side', () => {
        render(<LeaderboardPage initialData={mockLeaderboardData} />);

        // Get compare checkboxes
        const checkboxes = screen.getAllByRole('checkbox') as HTMLInputElement[];
        expect(checkboxes.length).toBe(3);

        // Check first two checkboxes to trigger comparison
        fireEvent.click(checkboxes[0]);
        fireEvent.click(checkboxes[1]);

        // Comparison header should be visible
        expect(screen.getByText('Comparative Diagnostics')).toBeDefined();

        // "Clear Selection" button should clear comparison
        const clearBtn = screen.getByText('Clear Selection');
        expect(clearBtn).toBeDefined();

        fireEvent.click(clearBtn);

        // Comparison details should disappear
        expect(screen.queryByText('Comparative Diagnostics')).toBeNull();
    });

    it('switches timeframe and triggers a query update when timeframe buttons are clicked', () => {
        const useQueryMock = useQuery as unknown as {
            mockClear: () => void;
            mock: {
                calls: { queryKey: (string | number | null)[] }[][];
            };
        };
        useQueryMock.mockClear();

        render(<LeaderboardPage initialData={mockLeaderboardData} />);

        // Click the '7 Days' button
        const sevenDaysBtn = screen.getByText('7 Days');
        expect(sevenDaysBtn).toBeDefined();
        fireEvent.click(sevenDaysBtn);

        // Check if useQuery was called with timeframe 7
        const calls = useQueryMock.mock.calls;
        const lastCallArgs = calls[calls.length - 1][0];
        expect(lastCallArgs.queryKey).toEqual(['leaderboard', 7]);
    });
});
