import type { PromptExperiment } from '@llm-market-bench/database';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { DailyPrediction } from '../api/fetch-daily-predictions';
import { DailyPredictionsBacktestPage } from './DailyPredictionsBacktestPage';

// Mock @tanstack/react-router Link
vi.mock('@tanstack/react-router', () => ({
    Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
        <a href={to}>{children}</a>
    ),
}));

describe('DailyPredictionsBacktestPage', () => {
    const mockPredictions: DailyPrediction[] = [
        {
            id: 'backtest-pred-1',
            prediction_date: '2026-04-27',
            target_date: '2026-04-27',
            ticker: 'SPY',
            model_name: 'deepseek-v4-flash',
            prompt_variant_tag: 'daily-pred-backtest-base',
            predicted_direction: 'UP',
            confidence: 75.0,
            expected_return_pct: 0.5,
            rationale: 'Backtest bullish reasoning.',
            catalysts: ['Backtest Catalyst'],
            open_price: 500.0,
            close_price: 505.0,
            actual_direction: 'UP',
            is_correct: true,
            brier_score: 0.0625,
            status: 'evaluated',
            created_at: '2026-04-27T09:00:00Z',
            updated_at: '2026-04-27T17:15:00Z',
        },
    ];

    const mockExperiments: PromptExperiment[] = [
        {
            id: 'exp-backtest-1',
            prompt_name: 'DAILY_PREDICTOR_PROMPT',
            variant_tag: 'daily-pred-backtest-base',
            experiment_type: 'baseline',
            prompt_content: 'Backtest strategy instructions.',
            change_description: 'Initial backtest daily prompt.',
            metrics: { score: 80.0 },
            status: 'active',
            week_start: '2026-04-27',
            week_end: '2026-05-02',
            created_at: '2026-04-27T00:00:00Z',
            parent_tag: null,
            research_output: null,
            is_backtest: true,
            track_id: null,
        },
    ];

    it('renders header, metrics overview, predictions log, and prompt arena', () => {
        render(
            <DailyPredictionsBacktestPage
                initialPredictions={mockPredictions}
                experiments={mockExperiments}
            />,
        );

        expect(screen.getByText('S&P Daily Predictor Backtest Arena')).toBeInTheDocument();
        expect(screen.getByText('Backtest Directional Accuracy')).toBeInTheDocument();
        expect(screen.getByText('100.0%')).toBeInTheDocument();
        expect(screen.getAllByText('0.0625').length).toBeGreaterThan(0);
        expect(screen.getByText('Historical Backtest Predictions Log')).toBeInTheDocument();
        expect(screen.getByText('Backtest Prompt Experiments Arena')).toBeInTheDocument();
        expect(screen.getAllByText('daily-pred-backtest-base').length).toBeGreaterThan(0);
    });
});
