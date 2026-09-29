import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { DailyPrediction } from '../api/fetch-daily-predictions';
import { DailyLessonsLedgerCard } from './DailyLessonsLedgerCard';

describe('DailyLessonsLedgerCard', () => {
    const mockPredictions: DailyPrediction[] = [
        {
            id: 'pred-1',
            prediction_date: '2026-09-28',
            target_date: '2026-09-28',
            ticker: 'SPY',
            model_name: 'deepseek-v4-flash',
            prompt_variant_tag: 'daily-active-1',
            predicted_direction: 'UP',
            confidence: 75.0,
            expected_return_pct: 0.35,
            rationale: 'Positive momentum.',
            catalysts: ['Earnings'],
            open_price: 500.0,
            close_price: 502.0,
            actual_direction: 'UP',
            is_correct: true,
            brier_score: 0.0625,
            status: 'evaluated',
            postmortem_category: 'ACCURATE_CAPTURE',
            postmortem_flawed_assumption: 'None',
            postmortem_lesson:
                'Retain directional signal when broad market weakness aligns with higher yields.',
            was_predictable: true,
            postmortem_evaluated_at: '2026-09-28T17:15:00Z',
            created_at: '2026-09-28T09:15:00Z',
            updated_at: '2026-09-28T16:15:00Z',
        },
        {
            id: 'pred-2',
            prediction_date: '2026-09-25',
            target_date: '2026-09-25',
            ticker: 'SPY',
            model_name: 'deepseek-v4-flash',
            prompt_variant_tag: 'daily-active-1',
            predicted_direction: 'DOWN',
            confidence: 65.0,
            expected_return_pct: -0.4,
            rationale: 'Rate headwind.',
            catalysts: ['Rates'],
            open_price: 500.0,
            close_price: 504.0,
            actual_direction: 'UP',
            is_correct: false,
            brier_score: 0.4225,
            status: 'evaluated',
            postmortem_category: 'INTRADAY_REVERSAL',
            postmortem_flawed_assumption: 'Assumed geopolitical relief would fade immediately.',
            postmortem_lesson:
                'Do not fade positive morning gaps purely on rate headwinds without opening-range failure.',
            was_predictable: true,
            postmortem_evaluated_at: '2026-09-25T17:15:00Z',
            created_at: '2026-09-25T09:15:00Z',
            updated_at: '2026-09-25T16:15:00Z',
        },
    ];

    it('renders empty message when predictions have no post-mortems', () => {
        const withoutLessons: DailyPrediction[] = [
            {
                ...mockPredictions[0],
                postmortem_lesson: null,
                postmortem_category: null,
                postmortem_evaluated_at: null,
            },
        ];

        render(<DailyLessonsLedgerCard predictions={withoutLessons} />);
        expect(
            screen.getByText(/No daily post-mortem lessons recorded for this track yet/i),
        ).toBeInTheDocument();
    });

    it('renders list of post-mortem lessons with categories and dates', () => {
        render(<DailyLessonsLedgerCard predictions={mockPredictions} />);

        expect(screen.getByText('Daily Causal Lessons & Post-Mortems')).toBeInTheDocument();
        expect(screen.getByText('2026-09-28')).toBeInTheDocument();
        expect(screen.getByText('2026-09-25')).toBeInTheDocument();
        expect(screen.getByText('ACCURATE CAPTURE')).toBeInTheDocument();
        expect(screen.getByText('INTRADAY REVERSAL')).toBeInTheDocument();
        expect(
            screen.getByText(
                'Retain directional signal when broad market weakness aligns with higher yields.',
            ),
        ).toBeInTheDocument();
        expect(
            screen.getByText(
                'Do not fade positive morning gaps purely on rate headwinds without opening-range failure.',
            ),
        ).toBeInTheDocument();
        expect(
            screen.getByText('Assumed geopolitical relief would fade immediately.'),
        ).toBeInTheDocument();
    });
});
