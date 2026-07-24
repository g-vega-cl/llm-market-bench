import type { PromptExperiment } from '@llm-market-bench/database';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { DailyScoreDisplay } from './DailyScoreDisplay';

let lastTable = '';
const mockSupabaseClient = {
    from: vi.fn().mockImplementation((table) => {
        lastTable = table;
        return mockSupabaseClient;
    }),
    select: vi.fn().mockReturnThis(),
    eq: vi.fn().mockReturnThis(),
    in: vi.fn().mockReturnThis(),
    gte: vi.fn().mockReturnThis(),
    lte: vi.fn().mockReturnThis(),
    order: vi.fn().mockImplementation(() => {
        if (lastTable === 'price_history') {
            return Promise.resolve({
                data: [
                    { fetched_at: '2026-06-01T00:00:00Z', price: 100.0 },
                    { fetched_at: '2026-06-05T00:00:00Z', price: 105.0 },
                ],
                error: null,
            });
        }
        return Promise.resolve({
            data: [
                {
                    portfolio_id: 'gemini-portfolio-id',
                    total_equity: 10000,
                    date: '2026-06-01',
                    portfolios: { owner_id: 'gemini-3.1-flash-lite' },
                },
                {
                    portfolio_id: 'gemini-portfolio-id',
                    total_equity: 10200,
                    date: '2026-06-05',
                    portfolios: { owner_id: 'gemini-3.1-flash-lite' },
                },
                {
                    portfolio_id: 'deepseek-portfolio-id',
                    total_equity: 10000,
                    date: '2026-06-01',
                    portfolios: { owner_id: 'deepseek-v4-pro' },
                },
                {
                    portfolio_id: 'deepseek-portfolio-id',
                    total_equity: 9800,
                    date: '2026-06-05',
                    portfolios: { owner_id: 'deepseek-v4-pro' },
                },
            ],
            error: null,
        });
    }),
};

vi.mock('~/lib/supabase-client', () => ({
    getSupabaseBrowserClient: () => mockSupabaseClient,
}));

describe('DailyScoreDisplay', () => {
    it('renders live status and daily tracking score when experiment is active', () => {
        const mockExperiment = {
            variant_tag: 'V1.0',
            metrics: {
                portfolio_return_pct: null,
                spy_return_pct: null,
                do_nothing_return_pct: null,
                excess_return: null,
                opportunity_cost_penalty: null,
                max_drawdown: null,
                drawdown_penalty: null,
                score: null,
            },
        } as unknown as PromptExperiment;

        render(<DailyScoreDisplay experiment={mockExperiment} />);

        // Should display the Daily Autoresearch Score section
        expect(screen.getByText('Daily Autoresearch Score')).toBeInTheDocument();
        expect(screen.getByText('LIVE TRACKING')).toBeInTheDocument();
        // Since it's active/display-only, we should see a simulated or active score
        expect(screen.getByText(/Daily Excess/)).toBeInTheDocument();
    });

    it('renders daily score progression details when experiment is completed', () => {
        const mockExperiment = {
            variant_tag: 'V1.1',
            metrics: {
                portfolio_return_pct: 3.5,
                spy_return_pct: 1.0,
                do_nothing_return_pct: 2.0,
                excess_return: 3.0,
                opportunity_cost_penalty: 0,
                max_drawdown: 5,
                drawdown_penalty: 1.5,
                score: 1.5,
            },
        } as unknown as PromptExperiment;

        render(<DailyScoreDisplay experiment={mockExperiment} />);

        // Should display the Daily Autoresearch Score section
        expect(screen.getByText('Daily Autoresearch Score')).toBeInTheDocument();
        expect(screen.getByText('COMPLETED WEEK')).toBeInTheDocument();
        expect(screen.getByText(/Mon/)).toBeInTheDocument();
        expect(screen.getByText(/Fri/)).toBeInTheDocument();
    });

    it('only renders progression for days up to the current day when experiment is active', () => {
        // Mock system time to Wednesday, June 3rd, 2026
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2026-06-03T12:00:00Z'));

        const mockExperiment = {
            variant_tag: 'V1.0',
            week_start: '2026-06-01',
            metrics: {
                portfolio_return_pct: null,
                spy_return_pct: null,
                do_nothing_return_pct: null,
                excess_return: null,
                opportunity_cost_penalty: null,
                max_drawdown: null,
                drawdown_penalty: null,
                score: null,
            },
        } as unknown as PromptExperiment;

        render(<DailyScoreDisplay experiment={mockExperiment} />);

        // Mon, Tue, Wed should be shown (and have scores/returns formatted)
        // Thu and Fri are future days and should show "N/A" for score and portfolio return

        // Since we are mocking Wednesday, June 3rd:
        // Mon (June 1st) and Tue (June 2nd) and Wed (June 3rd) are current/past, they display scores.
        // Let's assert that "THU" shows "N/A" instead of simulated scores.

        // We find the elements by querying the text.
        // The score element is exactly "N/A" and the portfolio element is "P: N/A"
        const naElements = screen.getAllByText('N/A');
        expect(naElements.length).toBe(2); // Thu, Fri scores

        const naPortfolioElements = screen.getAllByText('P: N/A');
        expect(naPortfolioElements.length).toBe(2); // Thu, Fri portfolio returns

        vi.useRealTimers();
    });

    it('displays dates next to weekdays on the cards', () => {
        const mockExperiment = {
            variant_tag: 'V1.1',
            week_start: '2026-06-01',
            metrics: {
                portfolio_return_pct: 3.5,
                spy_return_pct: 1.0,
                do_nothing_return_pct: 2.0,
                excess_return: 3.0,
                opportunity_cost_penalty: 0,
                max_drawdown: 5,
                drawdown_penalty: 1.5,
                score: 1.5,
            },
        } as unknown as PromptExperiment;

        render(<DailyScoreDisplay experiment={mockExperiment} />);

        // Verify dates are on the cards
        expect(screen.getByText('6/1')).toBeInTheDocument(); // Mon
        expect(screen.getByText('6/2')).toBeInTheDocument(); // Tue
        expect(screen.getByText('6/3')).toBeInTheDocument(); // Wed
        expect(screen.getByText('6/4')).toBeInTheDocument(); // Thu
        expect(screen.getByText('6/5')).toBeInTheDocument(); // Fri
    });

    it('allows day inspection by clicking on a non-future card to see constituents', () => {
        // Mock system time to Wednesday, June 3rd, 2026
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2026-06-03T12:00:00Z'));

        const mockExperiment = {
            variant_tag: 'V1.0',
            week_start: '2026-06-01',
            metrics: {
                portfolio_return_pct: 2.0,
                spy_return_pct: 1.0,
                do_nothing_return_pct: 1.5,
                excess_return: 1.0,
                opportunity_cost_penalty: 0.1,
                max_drawdown: 1.0,
                drawdown_penalty: 0.3,
                score: 0.6,
            },
        } as unknown as PromptExperiment;

        render(<DailyScoreDisplay experiment={mockExperiment} />);

        // By default, the details panel is not shown
        expect(screen.queryByText(/Score Constituents/)).not.toBeInTheDocument();

        // Click Wednesday card (June 3rd)
        const wedCard = screen.getByText('6/3').closest('button');
        expect(wedCard).toBeInTheDocument();
        if (wedCard) {
            fireEvent.click(wedCard);
        }

        // Wednesday is selected. It should render details panel showing constituents.
        expect(screen.getByText(/Score Constituents — Wednesday/)).toBeInTheDocument();
        expect(screen.getByText(/Excess Return \(Scaled\)/)).toBeInTheDocument();
        expect(screen.getByText(/Opportunity Cost \(Scaled\)/)).toBeInTheDocument();
        expect(screen.getByText(/Risk Penalty \(Scaled\)/)).toBeInTheDocument();

        // Click again to toggle/close
        if (wedCard) {
            fireEvent.click(wedCard);
        }
        expect(screen.queryByText(/Score Constituents/)).not.toBeInTheDocument();

        vi.useRealTimers();
    });

    it('does not allow inspecting future days', () => {
        // Mock system time to Wednesday, June 3rd, 2026
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2026-06-03T12:00:00Z'));

        const mockExperiment = {
            variant_tag: 'V1.0',
            week_start: '2026-06-01',
            metrics: {
                portfolio_return_pct: 2.0,
                spy_return_pct: 1.0,
                do_nothing_return_pct: 1.5,
                excess_return: 1.0,
                opportunity_cost_penalty: 0.1,
                max_drawdown: 1.0,
                drawdown_penalty: 0.3,
                score: null,
            },
        } as unknown as PromptExperiment;

        render(<DailyScoreDisplay experiment={mockExperiment} />);

        // Thursday (June 4th) is a future day
        const thuCard = screen.getByText('6/4').closest('button');
        expect(thuCard).toBeInTheDocument();
        if (thuCard) {
            fireEvent.click(thuCard);
        }

        // It should NOT render the details panel
        expect(screen.queryByText(/Score Constituents/)).not.toBeInTheDocument();

        vi.useRealTimers();
    });

    it('displays detailed audit formulas and portfolio constituents', async () => {
        const mockExperiment = {
            variant_tag: 'V1.0',
            week_start: '2026-06-01',
            week_end: '2026-06-05',
            metrics: {
                portfolio_return_pct: 2.0,
                spy_return_pct: 1.0,
                do_nothing_return_pct: 1.5,
                excess_return: 1.0,
                opportunity_cost_penalty: 0.1,
                max_drawdown: 1.0,
                drawdown_penalty: 0.3,
                score: 0.6,
                portfolio_details: {
                    'gemini-portfolio-id': {
                        owner_id: 'gemini-3.1-flash-lite',
                        do_nothing_return_pct: 1.2,
                    },
                    'deepseek-portfolio-id': {
                        owner_id: 'deepseek-v4-pro',
                        do_nothing_return_pct: 1.8,
                    },
                },
            },
        } as unknown as PromptExperiment;

        render(<DailyScoreDisplay experiment={mockExperiment} />);

        // Click Wednesday card (June 3rd)
        const wedCard = screen.getByText('6/3').closest('button');
        expect(wedCard).toBeInTheDocument();
        if (wedCard) {
            fireEvent.click(wedCard);
        }

        // Check that the detailed breakdown and formulas are visible
        expect(screen.getByText(/^1. Excess Return Calculation:$/)).toBeInTheDocument();
        expect(screen.getByText(/Formula: Portfolio - S&P 500/)).toBeInTheDocument();
        expect(screen.getByText(/^Base Excess Return Calculation:$/)).toBeInTheDocument();
        expect(screen.getByText(/^Base Calculation:$/)).toBeInTheDocument();

        // Check constituent display for Do-Nothing Return
        expect(screen.getByText(/Gemini 3.1 Flash Lite/)).toBeInTheDocument();
        expect(screen.getByText(/DeepSeek V4 Pro/)).toBeInTheDocument();

        // Check constituent display for Portfolio Return
        // Wait for async actual returns query to resolve
        const actualReturnsTexts = await screen.findAllByText(/1.1000%/); // 2.0% * 0.55 = 1.1000%
        expect(actualReturnsTexts.length).toBeGreaterThan(0);
    });

    it('dynamically computes SPY and portfolio returns from DB for active experiments', async () => {
        const mockExperiment = {
            variant_tag: 'V1.0-active',
            week_start: '2026-06-01',
            week_end: '2026-06-05',
            metrics: {
                portfolio_return_pct: null,
                spy_return_pct: null,
                do_nothing_return_pct: null,
                excess_return: null,
                opportunity_cost_penalty: 0.1,
                max_drawdown: 1.0,
                drawdown_penalty: 0.3,
                score: null,
                portfolio_details: {
                    'gemini-portfolio-id': {
                        owner_id: 'gemini-3.1-flash-lite',
                        do_nothing_return_pct: 1.0,
                    },
                    'deepseek-portfolio-id': {
                        owner_id: 'deepseek-v4-pro',
                        do_nothing_return_pct: 2.0,
                    },
                },
            },
        } as unknown as PromptExperiment;

        render(<DailyScoreDisplay experiment={mockExperiment} />);

        // Click Wednesday card (June 3rd)
        const wedCard = screen.getByText('6/3').closest('button');
        expect(wedCard).toBeInTheDocument();
        if (wedCard) {
            fireEvent.click(wedCard);
        }

        // 1. Portfolio Return: average of gemini (2.0%) and deepseek (-2.0%) is 0.0%
        // Under Wednesday (multiplier 0.55), scaled portfolio return should be 0.0000%
        // Base portfolio return should be 0.0000%
        const basePortfolioText = await screen.findByText(/Base: 0.0000%/);
        expect(basePortfolioText).toBeInTheDocument();

        // 2. SPY return: from 100 to 105 is 5.0%
        // Scaled SPY return for Wednesday (multiplier 0.55): 5.0% * 0.55 = 2.7500%
        // Base SPY return: 5.0000%
        const spyReturnText = await screen.findByText(/5.0000%/);
        expect(spyReturnText).toBeInTheDocument();
    });
});
