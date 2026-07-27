import type { PromptExperiment } from '@llm-market-bench/database';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ScoreBreakdown } from './ScoreBreakdown';

describe('ScoreBreakdown', () => {
    it('renders with positive excess return and score', () => {
        const mockExperiment = {
            metrics: {
                portfolio_return_pct: 5.5,
                spy_return_pct: 2.0,
                do_nothing_return_pct: 4.0,
                excess_return: 5.0,
                opportunity_cost_penalty: 0.1234,
                max_drawdown: 10,
                drawdown_penalty: 3.0,
                score: 1.8766,
                bond_return_pct: 0.08,
                dollar_return_pct: -0.12,
            },
        } as unknown as PromptExperiment;

        render(<ScoreBreakdown experiment={mockExperiment} />);

        // Check if the title is there
        expect(screen.getByText('Score Audit & Step-by-Step Math')).toBeInTheDocument();

        // Check if values are correctly rendered
        expect(screen.getByText('5.5000% - 2.0000%')).toBeInTheDocument();
        expect(screen.getByText('5.5000% - 4.0000%')).toBeInTheDocument();
        expect(screen.getByText('5.5000% - 0.0800%')).toBeInTheDocument();
        expect(screen.getByText('+5.0000%')).toBeInTheDocument();
        expect(screen.getByText('+0.1234%')).toBeInTheDocument();
        expect(screen.getByText('10.0000%')).toBeInTheDocument();
        expect(screen.getByText('-3.0000%')).toBeInTheDocument();
        expect(screen.getByText('10.0000% × 0.3 = 3.0000%')).toBeInTheDocument();
    });

    it('renders with negative excess return and score', () => {
        const mockExperiment = {
            metrics: {
                portfolio_return_pct: -1.0,
                spy_return_pct: 2.0,
                do_nothing_return_pct: -0.5,
                excess_return: -3.5,
                opportunity_cost_penalty: -5.5,
                max_drawdown: 5,
                drawdown_penalty: 1.5,
                score: -10.5,
                bond_return_pct: 0.08,
                dollar_return_pct: -0.12,
            },
        } as unknown as PromptExperiment;

        render(<ScoreBreakdown experiment={mockExperiment} />);

        // Check if values are correctly rendered for negatives
        expect(screen.getByText('-1.0000% - 2.0000%')).toBeInTheDocument();
        expect(screen.getByText('-1.0000% - -0.5000%')).toBeInTheDocument();
        expect(screen.getByText('-1.0000% - 0.0800%')).toBeInTheDocument();
        expect(screen.getAllByText('-3.5000%').length).toBeGreaterThan(0);
        expect(screen.getAllByText('-5.5000%').length).toBeGreaterThan(0);
        expect(screen.getByText('5.0000%')).toBeInTheDocument();
        expect(screen.getByText('-1.5000%')).toBeInTheDocument();
        expect(screen.getByText('5.0000% × 0.3 = 1.5000%')).toBeInTheDocument();
    });

    it('handles empty or missing metrics', () => {
        const mockExperiment = {} as PromptExperiment;

        render(<ScoreBreakdown experiment={mockExperiment} />);

        expect(screen.getByText('Score Breakdown')).toBeInTheDocument();
        expect(
            screen.getByText(/This experiment variant is currently active/i),
        ).toBeInTheDocument();
    });
});
