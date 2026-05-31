import type { PromptExperiment } from '@llm-market-bench/database';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
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
});
