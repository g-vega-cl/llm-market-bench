import type { LeaderboardPagePayload, LLMLeaderboardRow } from '@llm-market-bench/database';
import { useQuery } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import type * as React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { LeaderboardPage } from './LeaderboardPage';

beforeEach(() => {
    Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation((query: string) => ({
            matches: false,
            media: query,
            onchange: null,
            addListener: vi.fn(),
            removeListener: vi.fn(),
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
            dispatchEvent: vi.fn(),
        })),
    });
});

vi.mock('@tanstack/react-router', () => ({
    Link: ({
        children,
        to,
        params,
        className,
    }: {
        children: React.ReactNode;
        to: string;
        params?: Record<string, string>;
        className?: string;
    }) => {
        let href = to;
        if (params) {
            for (const [k, v] of Object.entries(params)) {
                href = href.replace(`$${k}`, v);
            }
        }
        return (
            <a href={href} className={className}>
                {children}
            </a>
        );
    },
}));

vi.mock('@tanstack/react-query', async (importOriginal) => {
    const original = await importOriginal<typeof import('@tanstack/react-query')>();
    return {
        ...original,
        useQuery: vi.fn().mockImplementation(({ initialData }) => ({
            data: initialData,
            isLoading: false,
            isFetching: false,
        })),
    };
});

vi.mock('@tanstack/react-start', () => ({
    createServerFn: () => ({
        validator: () => ({
            handler: (fn: unknown) => fn,
        }),
        inputValidator: () => ({
            handler: (fn: unknown) => fn,
        }),
    }),
}));

const mockRows: LLMLeaderboardRow[] = [
    {
        model_name: 'deepseek-flash',
        display_name: 'deepseek-flash',
        entity_type: 'llm',
        portfolio_id: 'port-deepseek',
        recipe_id: null,
        is_live: true,
        total_equity: 10820,
        return_pct: 8.2,
        realized_pnl: 820,
        win_rate: 68.2,
        total_trades: 15,
        average_confidence: 85.0,
        conviction_score: 62.5,
        api_success_rate: 100.0,
        trading_activity_rate: 90.0,
        trading_performance_score: 85.2,
        reasoning_quality_score: 62.5,
        consistency_score: 64.0,
        up_days: 7,
        active_days: 10,
        composite_score: 89.5,
        rank: 1,
    },
    {
        model_name: 'MiniMax-M3.1-Flash',
        display_name: 'MiniMax-M3.1-Flash',
        entity_type: 'llm',
        portfolio_id: 'port-minimax',
        recipe_id: null,
        is_live: true,
        total_equity: 10600,
        return_pct: 6.0,
        realized_pnl: 600,
        win_rate: null,
        total_trades: 0,
        average_confidence: 80.0,
        conviction_score: 51.0,
        api_success_rate: 100.0,
        trading_activity_rate: 85.0,
        trading_performance_score: 80.0,
        reasoning_quality_score: 51.0,
        consistency_score: 58.0,
        up_days: 6,
        active_days: 10,
        composite_score: 85.0,
        rank: 2,
    },
    {
        model_name: 'sys-pead-drift',
        display_name: 'sys-pead-drift',
        entity_type: 'system',
        portfolio_id: 'port-pead',
        recipe_id: null,
        is_live: true,
        total_equity: 10480,
        return_pct: 4.8,
        realized_pnl: 480,
        win_rate: 62.5,
        total_trades: 12,
        average_confidence: null,
        conviction_score: null,
        api_success_rate: 100.0,
        trading_activity_rate: 85.0,
        trading_performance_score: 79.5,
        reasoning_quality_score: null,
        consistency_score: 55.5,
        up_days: 6,
        active_days: 10,
        composite_score: 84.2,
        rank: 3,
    },
    {
        model_name: 'user-bot:rec-1',
        display_name: 'Momentum Alpha Bot',
        entity_type: 'user_bot',
        portfolio_id: null,
        recipe_id: 'rec-1',
        is_live: true,
        total_equity: 10310,
        return_pct: 3.1,
        realized_pnl: 310,
        win_rate: 60.0,
        total_trades: 5,
        average_confidence: null,
        conviction_score: null,
        api_success_rate: 100.0,
        trading_activity_rate: 70.0,
        trading_performance_score: 65.0,
        reasoning_quality_score: null,
        consistency_score: 54.0,
        up_days: 6,
        active_days: 10,
        composite_score: 72.1,
        rank: 4,
    },
];

function makeInitialPage(
    rows: LLMLeaderboardRow[],
    totalCount = rows.length,
    counts = { all: totalCount, llm: 2, system: 1, user_bot: Math.max(0, totalCount - 3) },
): LeaderboardPagePayload {
    return {
        rows,
        podium: rows.slice(0, 3),
        totalCount,
        counts,
    };
}

function makeManyRows(count: number): LLMLeaderboardRow[] {
    return Array.from({ length: count }, (_, idx) => ({
        model_name: `user-bot:rec-${idx + 1}`,
        display_name: `User Bot ${idx + 1}`,
        entity_type: idx < 3 ? 'llm' : idx < 6 ? 'system' : 'user_bot',
        portfolio_id: idx < 6 ? `port-${idx + 1}` : null,
        recipe_id: idx >= 6 ? `rec-${idx + 1}` : null,
        is_live: true,
        total_equity: 11000 - idx * 50,
        return_pct: 10 - idx * 0.5,
        realized_pnl: 1000 - idx * 50,
        win_rate: 65 - idx,
        total_trades: 10,
        average_confidence: idx < 3 ? 70 : null,
        conviction_score: idx < 3 ? 55 : null,
        api_success_rate: 100,
        trading_activity_rate: 80,
        trading_performance_score: 75 - idx,
        reasoning_quality_score: idx < 3 ? 55 : null,
        consistency_score: 60 - idx,
        up_days: 6,
        active_days: 10,
        composite_score: 90 - idx,
        rank: idx + 1,
    }));
}

describe('LeaderboardPage', () => {
    it('renders unified leaderboard with podium, table, sys portfolios, user bots, living backdrop, and zero Approval column', () => {
        const { container } = render(
            <LeaderboardPage initialData={makeInitialPage(mockRows)} initialAtmosphere="dusk" />,
        );

        expect(container.querySelector('[data-slot="scene-stage"]')).toHaveAttribute(
            'data-backdrop-mode',
            'page',
        );
        expect(screen.getByTestId('cedar-ridge-backdrop')).toBeInTheDocument();
        expect(screen.getByTestId('atmosphere-switcher')).toBeInTheDocument();
        expect(screen.getByTestId('motion-toggle')).toBeInTheDocument();

        expect(screen.getByRole('heading', { name: 'Leaderboard' })).toBeDefined();
        expect(screen.getByText('Place #1')).toBeDefined();
        expect(screen.getByText('Place #2')).toBeDefined();
        expect(screen.getByText('Place #3')).toBeDefined();

        expect(screen.getAllByText('DeepSeek (flash)').length).toBeGreaterThan(0);
        expect(screen.getAllByText('MiniMax (M3.1)').length).toBeGreaterThan(0);
        expect(screen.getAllByText('Sys Pead Drift').length).toBeGreaterThan(0);
        expect(screen.getAllByText('Momentum Alpha Bot').length).toBeGreaterThan(0);

        expect(screen.queryByText(/Approval/i)).toBeNull();
        expect(screen.getAllByText('—').length).toBeGreaterThan(0);

        // Consistency is surfaced as up-days out of active sessions, not a bare percentage.
        expect(screen.getAllByText('Up Days').length).toBeGreaterThan(0);
        expect(screen.getAllByText('7/10 · 64.0%').length).toBeGreaterThan(0);
        expect(screen.queryByText('Consistency')).toBeNull();
        expect(screen.getByText(/flat days are dropped/i)).toBeDefined();

        const checkbox = screen.getByRole('checkbox', {
            name: /select deepseek \(flash\) for comparison/i,
        });
        expect(checkbox).toBeInTheDocument();
    });

    it('requests server-side pagination (page=2) when Next is clicked and updates query key', () => {
        const useQueryMock = useQuery as unknown as {
            mockClear: () => void;
            mock: { calls: { queryKey: unknown[] }[][] };
        };
        useQueryMock.mockClear();

        const first10 = makeManyRows(10);
        render(
            <LeaderboardPage
                initialData={makeInitialPage(first10, 14, {
                    all: 14,
                    llm: 3,
                    system: 3,
                    user_bot: 8,
                })}
                initialAtmosphere="dusk"
            />,
        );

        expect(screen.getByText('Showing 1–10 of 14')).toBeInTheDocument();
        expect(screen.getByText('Page 1 of 2')).toBeInTheDocument();
        expect(screen.getAllByRole('checkbox')).toHaveLength(10);

        fireEvent.click(screen.getByRole('button', { name: /Next/i }));

        const calls = useQueryMock.mock.calls;
        const lastCall = calls[calls.length - 1][0];
        expect(lastCall.queryKey).toEqual(['leaderboard', 30, 'all', 'composite_score', 'desc', 2]);
    });

    it('requests category filter and resets page to 1 when switching category tabs', () => {
        const useQueryMock = useQuery as unknown as {
            mockClear: () => void;
            mock: { calls: { queryKey: unknown[] }[][] };
        };
        useQueryMock.mockClear();

        const first10 = makeManyRows(10);
        render(
            <LeaderboardPage
                initialData={makeInitialPage(first10, 14, {
                    all: 14,
                    llm: 3,
                    system: 3,
                    user_bot: 8,
                })}
                initialAtmosphere="dusk"
            />,
        );

        fireEvent.click(screen.getByRole('button', { name: /Next/i }));
        fireEvent.click(screen.getByRole('button', { name: /User Bots/i }));

        const calls = useQueryMock.mock.calls;
        const lastCall = calls[calls.length - 1][0];
        expect(lastCall.queryKey).toEqual([
            'leaderboard',
            30,
            'user_bot',
            'composite_score',
            'desc',
            1,
        ]);
    });

    it('renders em-dash without false WIN badge when comparing LLM vs non-LLM null conviction/confidence', () => {
        render(
            <LeaderboardPage initialData={makeInitialPage(mockRows)} initialAtmosphere="dusk" />,
        );

        const checkboxes = screen.getAllByRole('checkbox') as HTMLInputElement[];
        // DeepSeek (index 0, llm with conviction 62.5) vs Sys Pead Drift (index 2, system with conviction null)
        fireEvent.click(checkboxes[0]);
        fireEvent.click(checkboxes[2]);

        expect(screen.getByText('Comparative Diagnostics')).toBeDefined();
        expect(screen.getAllByText('Conviction Score')).toHaveLength(2);
        // Sys card displays '—' for Conviction Score and Average Confidence
        expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(2);
    });

    it('switches timeframe and triggers a query update when timeframe buttons are clicked', () => {
        const useQueryMock = useQuery as unknown as {
            mockClear: () => void;
            mock: { calls: { queryKey: unknown[] }[][] };
        };
        useQueryMock.mockClear();

        render(
            <LeaderboardPage initialData={makeInitialPage(mockRows)} initialAtmosphere="dusk" />,
        );

        fireEvent.click(screen.getByText('7 Days'));

        const calls = useQueryMock.mock.calls;
        const lastCall = calls[calls.length - 1][0];
        expect(lastCall.queryKey).toEqual(['leaderboard', 7, 'all', 'composite_score', 'desc', 1]);
    });

    it('sizes its root wrapper with min-h-svh, never dynamic viewport units, so the mobile background bottom does not jump', () => {
        const { container } = render(
            <LeaderboardPage initialData={makeInitialPage(mockRows)} initialAtmosphere="dusk" />,
        );

        const root = container.firstElementChild as HTMLElement;
        expect(root.tagName).toBe('DIV');
        expect(root.className).toContain('min-h-svh');
        expect(root.className).not.toContain('min-h-screen');
        expect(root.className).not.toContain('h-screen');
        expect(root.className).not.toContain('w-screen');
        expect(root.className).not.toContain('100vh');
        expect(root.className).not.toContain('dvh');
    });
});
