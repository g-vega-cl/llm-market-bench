import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { DailyPrediction } from '../api/fetch-daily-predictions';
import { HeroPredictionCard } from './HeroPredictionCard';

describe('HeroPredictionCard', () => {
    const mockPrediction: DailyPrediction = {
        id: 'pred-1',
        prediction_date: '2026-08-03',
        target_date: '2026-08-03',
        ticker: 'SPY',
        model_name: 'deepseek-v4-flash',
        prompt_variant_tag: 'daily-active-1',
        predicted_direction: 'UP',
        confidence: 85.0,
        expected_return_pct: 0.65,
        rationale: 'Strong momentum and bullish moving average cross.',
        catalysts: ['CPI Beat', 'Tech Surge'],
        open_price: 450.0,
        close_price: 455.0,
        actual_direction: 'UP',
        is_correct: true,
        intraday_hit: true,
        brier_score: 0.0225,
        status: 'evaluated',
        created_at: '2026-08-03T08:00:00Z',
        updated_at: '2026-08-03T16:00:00Z',
    };

    it('renders direction, confidence, expected return, and catalysts', () => {
        render(<HeroPredictionCard prediction={mockPrediction} />);

        expect(screen.getByText('▲ UP')).toBeInTheDocument();
        expect(screen.getByText('85% Confidence')).toBeInTheDocument();
        expect(screen.getByText(/Expected Return: \+0.65%/)).toBeInTheDocument();
        expect(
            screen.getByText(/Strong momentum and bullish moving average cross/),
        ).toBeInTheDocument();
        expect(screen.getByText('EVALUATED')).toBeInTheDocument();
        expect(screen.getByText('CPI Beat')).toBeInTheDocument();
        expect(screen.getByText('Tech Surge')).toBeInTheDocument();
    });

    it('renders DOWN direction correctly', () => {
        const downPred: DailyPrediction = {
            ...mockPrediction,
            predicted_direction: 'DOWN',
            expected_return_pct: -0.4,
            status: 'pending',
        };
        render(<HeroPredictionCard prediction={downPred} />);

        expect(screen.getByText('▼ DOWN')).toBeInTheDocument();
        expect(screen.getByText(/Expected Return: -0.4%/)).toBeInTheDocument();
        expect(screen.getByText('PENDING')).toBeInTheDocument();
    });
});
