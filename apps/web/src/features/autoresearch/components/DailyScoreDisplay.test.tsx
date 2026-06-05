import type { PromptExperiment } from '@llm-market-bench/database';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { DailyScoreDisplay } from './DailyScoreDisplay';

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
});
