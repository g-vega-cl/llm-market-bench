import type { PromptExperiment } from '@llm-market-bench/database';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BacktestTradesAudit } from './BacktestTradesAudit';

describe('BacktestTradesAudit', () => {
    it('renders empty notice when no trades exist in metrics', () => {
        const mockExperiment = {
            id: 'exp-1',
            prompt_name: 'CORE_ANALYSIS_SYSTEM_PROMPT',
            variant_tag: 'backtest-v1',
            prompt_content: 'test prompt',
            metrics: {},
            created_at: new Date().toISOString(),
            is_backtest: true,
            status: 'COMPLETED',
            change_description: 'Initial prompt',
            experiment_type: 'BASELINE',
            parent_tag: null,
            research_output: {},
            week_start: '2026-04-27',
            week_end: '2026-05-02',
        } as unknown as PromptExperiment;

        render(<BacktestTradesAudit experiment={mockExperiment} />);
        expect(screen.getByText(/No Detailed Trade Ledger Recorded/i)).toBeInTheDocument();
    });

    it('renders executed trade table when trades are present in metrics', () => {
        const mockExperiment = {
            id: 'exp-2',
            prompt_name: 'CORE_ANALYSIS_SYSTEM_PROMPT',
            variant_tag: 'backtest-v2',
            prompt_content: 'test prompt',
            metrics: {
                trades: [
                    {
                        id: 't-1',
                        portfolio_id: 'p-1',
                        model_name: 'gemini-3.5-flash-lite',
                        ticker: 'AAPL',
                        signal: 'BUY',
                        quantity: 50,
                        price: 180.0,
                        total_cost: 9000.0,
                        executed_at: '2026-04-27T11:00:00Z',
                        reasoning: 'Strong fundamentals',
                    },
                ],
            },
            created_at: new Date().toISOString(),
            is_backtest: true,
            status: 'COMPLETED',
            change_description: 'Mutation prompt',
            experiment_type: 'MUTATION',
            parent_tag: 'backtest-v1',
            research_output: {},
            week_start: '2026-04-27',
            week_end: '2026-05-02',
        } as unknown as PromptExperiment;

        render(<BacktestTradesAudit experiment={mockExperiment} />);
        expect(screen.getByText(/Backtest Executed Trades Audit/i)).toBeInTheDocument();
        expect(screen.getByText('AAPL')).toBeInTheDocument();
        expect(screen.getAllByText('BUY').length).toBeGreaterThan(0);
        expect(screen.getByText('gemini-3.5-flash-lite')).toBeInTheDocument();
    });
});
