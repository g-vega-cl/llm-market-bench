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
        expect(
            screen.getByText(/score = Composite Excess Return - Drawdown Penalty/i),
        ).toBeInTheDocument();
        expect(screen.getByText(/score = \+?5\.0000% - 3\.0000%/i)).toBeInTheDocument();
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

    it('renders audited settlement timestamp and 100% cash badge for empty starting positions', () => {
        const mockExperiment = {
            created_at: '2026-06-07T20:00:00Z',
            metrics: {
                portfolio_return_pct: 2.0,
                spy_return_pct: 1.0,
                do_nothing_return_pct: 0.0,
                excess_return: 1.0,
                opportunity_cost_penalty: 0.1,
                max_drawdown: 1.0,
                drawdown_penalty: 0.3,
                score: 0.7,
                evaluated_at: '2026-06-07T20:00:00Z',
                portfolio_details: {
                    'claude-portfolio-id': {
                        owner_id: 'claude-haiku-4-5',
                        initial_equity: 10000,
                        initial_cash: 10000,
                        end_equity: 10000,
                        do_nothing_return_pct: 0.0,
                        positions: {},
                    },
                },
            },
        } as unknown as PromptExperiment;

        render(<ScoreBreakdown experiment={mockExperiment} />);

        // Check if settlement timestamp is displayed
        expect(screen.getAllByText(/Audited Settlement:/i).length).toBeGreaterThan(0);

        // Check if 100% cash at week start indicator is displayed
        expect(screen.getByText(/100% Cash at Week Start/i)).toBeInTheDocument();
    });
});
