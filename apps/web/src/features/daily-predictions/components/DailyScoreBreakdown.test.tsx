import type { PromptExperiment } from '@llm-market-bench/database';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { DailyPrediction } from '../api/fetch-daily-predictions';
import {
    calculateMagnitudeCapture,
    DailyScoreBreakdown,
    resolveRatchetMetrics,
} from './DailyScoreBreakdown';

describe('DailyScoreBreakdown', () => {
    it('renders with enriched metrics and displays the formula substitution and 4 pillars', () => {
        const mockExperiment = {
            id: 'exp-1',
            variant_tag: 'daily-pred-seeded-deepseek-v4-flash',
            week_start: '2026-08-20',
            week_end: '2026-08-24',
            metrics: {
                score: 14.8,
                close_accuracy_pct: 33.33,
                intraday_hit_pct: 33.33,
                magnitude_capture_pct: 0.0,
                mean_brier: 0.304,
                predictions_evaluated: 3,
                correct_count: 1,
                intraday_hit_count: 1,
            },
        } as unknown as PromptExperiment;

        render(<DailyScoreBreakdown experiment={mockExperiment} />);

        // Header and title
        expect(screen.getByText('Daily Ratchet Score Calculation & Breakdown')).toBeInTheDocument();
        expect(screen.getByText('14.80')).toBeInTheDocument();
        expect(
            screen.getByText('Evaluated across 3 predictions (2026-08-20 → 2026-08-24)'),
        ).toBeInTheDocument();

        // 4 Pillars
        expect(screen.getByText('EOD Directional Acc (55%)')).toBeInTheDocument();
        expect(screen.getAllByText('33.3%')).toHaveLength(2); // Directional Acc & Intraday Hit
        expect(screen.getByText('+18.33 pts')).toBeInTheDocument();
        expect(screen.getByText('1 / 3 correct')).toBeInTheDocument();

        expect(screen.getByText('Intraday Target Hit (35%)')).toBeInTheDocument();
        expect(screen.getByText('+11.67 pts')).toBeInTheDocument();
        expect(screen.getByText('1 / 3 targets hit')).toBeInTheDocument();

        expect(screen.getByText('Magnitude Capture (10%)')).toBeInTheDocument();
        expect(screen.getByText('+0.00 pts')).toBeInTheDocument();

        expect(screen.getByText('Brier Penalty (50.0×)')).toBeInTheDocument();
        expect(screen.getByText('0.3040')).toBeInTheDocument();
        expect(screen.getByText('−15.20 pts')).toBeInTheDocument();

        // Low Sample Notice
        expect(screen.getByText(/Low Sample Window Notice \(N = 3\)/)).toBeInTheDocument();
    });

    it('toggles collapsible scoring guide on button click', () => {
        const mockExperiment = {
            id: 'exp-1',
            variant_tag: 'daily-pred-benchmark-1',
            metrics: {
                score: 62.38,
                close_accuracy_pct: 75.0,
                intraday_hit_pct: 75.0,
                magnitude_capture_pct: 50.0,
                mean_brier: 0.2025,
                predictions_evaluated: 10,
                correct_count: 8,
                intraday_hit_count: 8,
            },
        } as unknown as PromptExperiment;

        render(<DailyScoreBreakdown experiment={mockExperiment} />);

        // Guide initially closed
        expect(
            screen.queryByText('How the Daily Ratchet Score is Computed:'),
        ).not.toBeInTheDocument();

        // Click to open guide
        const guideBtn = screen.getByText(/View Scoring Formula & Weights Guide/i);
        fireEvent.click(guideBtn);

        expect(screen.getByText('How the Daily Ratchet Score is Computed:')).toBeInTheDocument();
        expect(screen.getByText(/Close Directional Accuracy \(55%\):/)).toBeInTheDocument();
        expect(screen.getByText(/Intraday Target Hit Rate \(35%\):/)).toBeInTheDocument();
        expect(screen.getByText(/Magnitude Capture Ratio \(10%\):/)).toBeInTheDocument();
        expect(screen.getByText(/Brier Calibration Penalty \(50.0×\):/)).toBeInTheDocument();

        // Click to close guide
        fireEvent.click(screen.getByText(/Hide Scoring Formula & Weights Guide/i));
        expect(
            screen.queryByText('How the Daily Ratchet Score is Computed:'),
        ).not.toBeInTheDocument();
    });

    it('computes fallback metrics from predictions if experiment has legacy metrics', () => {
        const mockExperiment = {
            id: 'exp-legacy',
            variant_tag: 'daily-pred-legacy-tag',
            metrics: {
                score: 62.38,
            },
        } as unknown as PromptExperiment;

        const mockPredictions: DailyPrediction[] = [
            {
                id: 'p1',
                status: 'evaluated',
                prompt_variant_tag: 'daily-pred-legacy-tag',
                predicted_direction: 'UP',
                expected_return_pct: 0.2,
                open_price: 500,
                high_price: 505,
                close_price: 504,
                is_correct: true,
                intraday_hit: true,
                brier_score: 0.04,
            } as unknown as DailyPrediction,
            {
                id: 'p2',
                status: 'evaluated',
                prompt_variant_tag: 'daily-pred-legacy-tag',
                predicted_direction: 'UP',
                expected_return_pct: 0.8,
                open_price: 500,
                high_price: 505,
                close_price: 504,
                is_correct: true,
                intraday_hit: true,
                brier_score: 0.09,
            } as unknown as DailyPrediction,
            {
                id: 'p3',
                status: 'evaluated',
                prompt_variant_tag: 'daily-pred-legacy-tag',
                predicted_direction: 'UP',
                expected_return_pct: 0.5,
                open_price: 500,
                high_price: 501,
                close_price: 498,
                is_correct: false,
                intraday_hit: false,
                brier_score: 0.64,
            } as unknown as DailyPrediction,
            {
                id: 'p4',
                status: 'evaluated',
                prompt_variant_tag: 'daily-pred-legacy-tag',
                predicted_direction: 'UP',
                expected_return_pct: 0.4,
                open_price: 500,
                high_price: 502,
                close_price: 502,
                is_correct: true,
                intraday_hit: true,
                brier_score: 0.04,
            } as unknown as DailyPrediction,
        ];

        render(<DailyScoreBreakdown experiment={mockExperiment} predictions={mockPredictions} />);

        expect(screen.getAllByText('75.0%')).toHaveLength(2); // Directional Acc & Intraday Hit
        expect(screen.getByText('3 / 4 correct')).toBeInTheDocument();
        expect(screen.getByText('3 / 4 targets hit')).toBeInTheDocument();
        expect(screen.getByText('50.0%')).toBeInTheDocument();
    });

    it('calculates magnitude capture correctly for various scenarios', () => {
        // Missed prediction -> 0.0
        expect(
            calculateMagnitudeCapture({
                is_correct: false,
                intraday_hit: false,
            } as DailyPrediction),
        ).toBe(0.0);

        // Correct UP with 0.5% expected and +1.0% actual move -> 50.0%
        expect(
            calculateMagnitudeCapture({
                is_correct: true,
                intraday_hit: true,
                predicted_direction: 'UP',
                expected_return_pct: 0.5,
                open_price: 100.0,
                high_price: 101.0,
                close_price: 100.5,
            } as DailyPrediction),
        ).toBe(50.0);
    });

    it('returns null from resolveRatchetMetrics if no metrics or predictions exist', () => {
        const exp = { id: 'empty' } as PromptExperiment;
        expect(resolveRatchetMetrics(exp)).toBeNull();
    });
});
