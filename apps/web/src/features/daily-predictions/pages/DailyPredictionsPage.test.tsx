import type { PromptExperiment } from '@llm-market-bench/database';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { DailyPrediction } from '../api/fetch-daily-predictions';
import { DailyPredictionsPage } from './DailyPredictionsPage';

vi.mock('@tanstack/react-router', () => ({
    Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
        <a href={to}>{children}</a>
    ),
}));

describe('DailyPredictionsPage', () => {
    const mockPredictions: DailyPrediction[] = [
        {
            id: 'daily-pred-1',
            prediction_date: '2026-08-03',
            target_date: '2026-08-03',
            ticker: 'SPY',
            model_name: 'deepseek-v4-flash',
            prompt_variant_tag: 'daily-active-1',
            predicted_direction: 'UP',
            confidence: 80.0,
            expected_return_pct: 0.45,
            rationale: 'Overnight futures momentum and strong earnings catalysts.',
            catalysts: ['Tech Earnings', 'Fed Stance'],
            open_price: 450.0,
            high_price: 456.0,
            low_price: 449.0,
            close_price: 455.0,
            actual_direction: 'UP',
            is_correct: true,
            intraday_hit: true,
            intraday_direction_hit: true,
            brier_score: 0.04,
            status: 'evaluated',
            created_at: '2026-08-03T08:00:00Z',
            updated_at: '2026-08-03T16:15:00Z',
        },
    ];

    const mockExperiments: PromptExperiment[] = [
        {
            id: 'exp-daily-1',
            prompt_name: 'DAILY_PREDICTOR_PROMPT',
            variant_tag: 'daily-active-1',
            experiment_type: 'baseline',
            prompt_content: 'Analyze intraday S&P price action.',
            change_description: 'Initial daily predictor baseline.',
            metrics: { score: 75.0 },
            status: 'active',
            week_start: '2026-08-03',
            week_end: '2026-08-10',
            created_at: '2026-08-03T00:00:00Z',
            parent_tag: null,
            research_output: null,
            is_backtest: false,
            track_id: null,
        },
    ];

    const refreshFn = vi.fn().mockResolvedValue({
        predictions: mockPredictions,
        experiments: mockExperiments,
    });

    it('renders top metrics dashboard and hero prediction card', () => {
        render(
            <DailyPredictionsPage
                initialPredictions={mockPredictions}
                experiments={mockExperiments}
                refreshFn={refreshFn}
            />,
        );

        expect(screen.getByText('Daily S&P Market Predictor')).toBeInTheDocument();
        expect(screen.getByText('Directional Accuracy')).toBeInTheDocument();
        expect(screen.getByText('Intraday Target Hit (30%)')).toBeInTheDocument();
        expect(screen.getAllByText('100.0%').length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText('▲ UP')).toBeInTheDocument();
        expect(screen.getByText('80% Confidence')).toBeInTheDocument();
    });

    it('switches tabs between predictions log and autoresearch arena', () => {
        render(
            <DailyPredictionsPage
                initialPredictions={mockPredictions}
                experiments={mockExperiments}
                refreshFn={refreshFn}
            />,
        );

        const autoresearchTabBtn = screen.getByRole('button', {
            name: /Autoresearch & Prompt Evolution/i,
        });
        fireEvent.click(autoresearchTabBtn);

        expect(screen.getAllByText('daily-active-1').length).toBeGreaterThan(0);
        expect(screen.getByText('"Initial daily predictor baseline."')).toBeInTheDocument();
    });
});
