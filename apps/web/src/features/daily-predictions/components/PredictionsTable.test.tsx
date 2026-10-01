import type { PromptExperiment } from '@llm-market-bench/database';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { DailyPrediction } from '../api/fetch-daily-predictions';
import { PredictionsTable } from './PredictionsTable';

describe('PredictionsTable', () => {
    const mockPrediction: DailyPrediction = {
        id: 'pred-row-1',
        prediction_date: '2026-08-03',
        target_date: '2026-08-03',
        ticker: 'SPY',
        model_name: 'deepseek-v4-flash',
        prompt_variant_tag: 'daily-active-1',
        predicted_direction: 'UP',
        confidence: 80.0,
        expected_return_pct: 0.45,
        rationale: 'Overnight futures momentum.',
        catalysts: ['Tech Earnings'],
        open_price: 450.0,
        high_price: 456.0,
        low_price: 449.0,
        close_price: 455.0,
        actual_direction: 'UP',
        is_correct: true,
        intraday_hit: true,
        brier_score: 0.04,
        status: 'evaluated',
        created_at: '2026-08-03T08:00:00Z',
        updated_at: '2026-08-03T16:00:00Z',
    };

    const mockExperiment: PromptExperiment = {
        id: 'exp-1',
        prompt_name: 'DAILY_PREDICTOR_PROMPT',
        variant_tag: 'daily-active-1',
        experiment_type: 'baseline',
        prompt_content: 'Analyze intraday S&P price action for DeepSeek.',
        change_description: 'Initial daily predictor baseline.',
        metrics: { score: 75.0 },
        status: 'active',
        created_at: '2026-08-03T00:00:00Z',
        parent_tag: null,
        research_output: null,
        is_backtest: false,
        track_id: 'deepseek-v4-flash',
        week_start: '2026-08-03',
        week_end: '2026-08-10',
    };

    it('renders predictions rows and column headers', () => {
        render(<PredictionsTable predictions={[mockPrediction]} experiments={[mockExperiment]} />);

        expect(screen.getByText('Date')).toBeInTheDocument();
        expect(screen.getByText('Ticker')).toBeInTheDocument();
        expect(screen.getByText('Prediction')).toBeInTheDocument();
        expect(screen.getByText('2026-08-03')).toBeInTheDocument();
        expect(screen.getByText('SPY')).toBeInTheDocument();
        expect(screen.getAllByText('UP').length).toBe(2);
        expect(screen.getByText('80%')).toBeInTheDocument();
        expect(screen.getByText('$450.00')).toBeInTheDocument();
        expect(screen.getByText('$455.00')).toBeInTheDocument();
        expect(screen.getByText('HIT')).toBeInTheDocument();
        expect(screen.getByText('PASS')).toBeInTheDocument();
        expect(screen.getByText('0.0400')).toBeInTheDocument();
    });

    it('toggles row expansion to display prompt and details', () => {
        render(<PredictionsTable predictions={[mockPrediction]} experiments={[mockExperiment]} />);

        const expandBtn = screen.getByRole('button', { name: /View Details & Prompt/i });
        fireEvent.click(expandBtn);

        expect(
            screen.getByText(/Analyze intraday S&P price action for DeepSeek/i),
        ).toBeInTheDocument();
        expect(screen.getByText('Hide Details')).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: /Hide Details/i }));
        expect(
            screen.queryByText(/Analyze intraday S&P price action for DeepSeek/i),
        ).not.toBeInTheDocument();
    });

    it('renders empty message when no predictions exist', () => {
        render(<PredictionsTable predictions={[]} experiments={[]} />);
        expect(screen.getByText(/No daily predictions logged yet/i)).toBeInTheDocument();
    });
});
