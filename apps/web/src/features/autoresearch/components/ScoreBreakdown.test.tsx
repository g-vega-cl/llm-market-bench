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
                excess_return: 3.5,
                opportunity_cost_penalty: 0,
                max_drawdown: 10,
                drawdown_penalty: 3.0,
                score: 0.5,
            },
        } as unknown as PromptExperiment;

        render(<ScoreBreakdown experiment={mockExperiment} />);

        // Check if the title is there
        expect(screen.getByText('Score Breakdown')).toBeInTheDocument();

        // Check if values are correctly rendered
        expect(screen.getByText('(5.50% - 2.00%)')).toBeInTheDocument();
        expect(screen.getByText('+3.5000')).toBeInTheDocument();
        expect(screen.getByText('- 0.0000')).toBeInTheDocument();
        expect(screen.getByText('(10.00% × 0.3)')).toBeInTheDocument();
        expect(screen.getByText('- 3.0000')).toBeInTheDocument();
        expect(screen.getByText('0.5000')).toBeInTheDocument();
    });

    it('renders with negative excess return and score', () => {
        const mockExperiment = {
            metrics: {
                portfolio_return_pct: -1.0,
                spy_return_pct: 2.0,
                excess_return: -3.0,
                opportunity_cost_penalty: 5.5,
                max_drawdown: 5,
                drawdown_penalty: 1.5,
                score: -10.0,
            },
        } as unknown as PromptExperiment;

        render(<ScoreBreakdown experiment={mockExperiment} />);

        // Check if values are correctly rendered for negatives
        expect(screen.getByText('(-1.00% - 2.00%)')).toBeInTheDocument();
        expect(screen.getByText('-3.0000')).toBeInTheDocument();
        expect(screen.getByText('- 5.5000')).toBeInTheDocument();
        expect(screen.getByText('(5.00% × 0.3)')).toBeInTheDocument();
        expect(screen.getByText('- 1.5000')).toBeInTheDocument();
        expect(screen.getByText('-10.0000')).toBeInTheDocument();
    });

    it('handles empty or missing metrics', () => {
        const mockExperiment = {} as PromptExperiment;

        render(<ScoreBreakdown experiment={mockExperiment} />);

        expect(screen.getByText('(0.00% - 0.00%)')).toBeInTheDocument();
        expect(screen.getByText('+0.0000')).toBeInTheDocument(); // excess_return
        expect(screen.getByText('0.0000')).toBeInTheDocument(); // score
    });
});
