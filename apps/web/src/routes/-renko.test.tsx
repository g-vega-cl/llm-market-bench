import type {
    Portfolio,
    PortfolioPerformance,
    PositionWithReasoning,
    TradeWithReasoning,
} from '@llm-market-bench/database';
import { render, screen } from '@testing-library/react';
import type * as React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { RenkoAgentPageView } from './renko';

// Mock Tanstack Query's useSuspenseQuery
vi.mock('@tanstack/react-query', async (importOriginal) => {
    const original = await importOriginal<typeof import('@tanstack/react-query')>();
    return {
        ...original,
        useSuspenseQuery: vi.fn().mockImplementation(({ initialData }) => ({
            data: initialData,
        })),
        useQuery: vi.fn().mockImplementation(({ initialData }) => ({
            data: initialData,
        })),
        keepPreviousData: original.keepPreviousData,
    };
});

// Mock PostHog
vi.mock('@posthog/react', () => ({
    usePostHog: () => ({
        capture: vi.fn(),
    }),
}));

// Mock Tanstack Router Link
vi.mock('@tanstack/react-router', () => ({
    createFileRoute: () => () => ({
        component: () => null,
    }),
    Link: ({
        children,
        to,
        className,
    }: {
        children: React.ReactNode;
        to: string;
        className?: string;
    }) => (
        <a href={to} className={className}>
            {children}
        </a>
    ),
}));

describe('/renko route with LIN Renko Portfolio', () => {
    const mockPortfolio: Portfolio = {
        id: 'portfolio-lin-123',
        owner_id: 'lin-renko-agent-deepseek-flash',
        cash_balance: 5000,
        total_equity: 10450,
        buying_power: 5000,
        excess_liquidity: 5000,
        maintenance_margin: 0,
        realized: 0,
        sma: 5000,
        last_updated_at: '2026-08-18T00:00:00.000Z',
    };

    const mockPositions: PositionWithReasoning[] = [
        {
            position_id: 'pos-1',
            portfolio_id: 'portfolio-lin-123',
            owner_id: 'lin-renko-agent-deepseek-flash',
            ticker: 'LIN',
            quantity: 11,
            average_cost_basis: 485.74,
            current_price: 495.45,
            price_fetched_at: '2026-08-18T00:00:00.000Z',
            unrealized_pnl_usd: 106.86,
            unrealized_pnl_pct: 2.0,
            reasoning: 'Bullish reversal confirmed at 2 UP bricks.',
        },
    ];

    const mockHistory: PortfolioPerformance[] = [
        {
            id: 'perf-1',
            portfolio_id: 'portfolio-lin-123',
            date: '2026-08-01',
            cash_balance: 10000,
            total_equity: 10000,
            buying_power: 10000,
            available_funds: 10000,
            excess_liquidity: 10000,
            initial_margin_req: 0,
            maintenance_margin_req: 0,
            realized: 0,
            sma: 10000,
            created_at: '2026-08-01T00:00:00.000Z',
        },
        {
            id: 'perf-2',
            portfolio_id: 'portfolio-lin-123',
            date: '2026-08-18',
            cash_balance: 5000,
            total_equity: 10450,
            buying_power: 5000,
            available_funds: 5000,
            excess_liquidity: 5000,
            initial_margin_req: 0,
            maintenance_margin_req: 0,
            realized: 0,
            sma: 5000,
            created_at: '2026-08-18T00:00:00.000Z',
        },
    ];

    const mockTrades: TradeWithReasoning[] = [
        {
            id: 'trade-1',
            portfolio_id: 'portfolio-lin-123',
            ticker: 'LIN',
            signal: 'BUY',
            quantity: 11,
            price: 485.74,
            total_cost: 5343.14,
            executed_at: '2026-08-05T14:30:00.000Z',
            alpaca_status: 'FILLED',
            alpaca_order_id: 'order-1',
            alpaca_submitted_at: '2026-08-05T14:30:00.000Z',
            alpaca_filled_at: '2026-08-05T14:30:00.000Z',
            realized_pnl: null,
            realized_pnl_pct: null,
            decision_id: 'dec-1',
            reasoning: 'Entered position on bullish Renko breakout.',
        },
    ];

    it('renders the LIN Renko Portfolio section with metrics, performance chart, positions, and trades', () => {
        render(
            <RenkoAgentPageView
                initialData={{
                    portfolio: mockPortfolio,
                    positions: mockPositions,
                    history: mockHistory,
                    trades: mockTrades,
                }}
                fetchFn={vi.fn().mockResolvedValue({
                    portfolio: mockPortfolio,
                    positions: mockPositions,
                    history: mockHistory,
                    trades: mockTrades,
                })}
                benchmarkFetchFn={vi.fn().mockResolvedValue({})}
            />,
        );

        // Check header and Renko chart
        expect(screen.getByText(/Linde plc \(LIN\) — Hyper-Focused Renko Agent/i)).toBeDefined();
        expect(screen.getByText(/Authentic Renko Price Chart/i)).toBeDefined();

        // Check Portfolio Section Heading
        expect(screen.getByText(/LIN Renko Portfolio & Execution Ledger/i)).toBeDefined();

        // Check Metrics
        expect(screen.getByText(/Total Equity/i)).toBeDefined();
        expect(screen.getAllByText(/\$10,450\.00/i).length).toBeGreaterThan(0);
        expect(screen.getByText(/Cash Balance/i)).toBeDefined();
        expect(screen.getByText(/\$5,000\.00/i)).toBeDefined();

        // Check Positions & Trades tables
        expect(screen.getByText(/Active Positions/i)).toBeDefined();
        expect(screen.getByText(/Recent Trades/i)).toBeDefined();
    });

    it('renders gracefully with default empty portfolio when no DB records exist yet', () => {
        const emptyPortfolio: Portfolio = {
            id: 'lin-renko-agent-deepseek-flash',
            owner_id: 'lin-renko-agent-deepseek-flash',
            cash_balance: 10000,
            total_equity: 10000,
            buying_power: 10000,
            excess_liquidity: 10000,
            maintenance_margin: 0,
            realized: 0,
            sma: 10000,
            last_updated_at: new Date().toISOString(),
        };

        render(
            <RenkoAgentPageView
                initialData={{
                    portfolio: emptyPortfolio,
                    positions: [],
                    history: [],
                    trades: [],
                }}
                fetchFn={vi.fn().mockResolvedValue({
                    portfolio: emptyPortfolio,
                    positions: [],
                    history: [],
                    trades: [],
                })}
                benchmarkFetchFn={vi.fn().mockResolvedValue({})}
            />,
        );

        expect(screen.getByText(/LIN Renko Portfolio & Execution Ledger/i)).toBeDefined();
        expect(screen.getAllByText(/\$10,000\.00/i).length).toBeGreaterThan(0);
        expect(screen.getByText(/No active positions/i)).toBeDefined();
    });
});
