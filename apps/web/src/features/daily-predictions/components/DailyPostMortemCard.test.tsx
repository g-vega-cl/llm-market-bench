import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { DailyPrediction } from '../api/fetch-daily-predictions';
import { DailyPostMortemCard } from './DailyPostMortemCard';

describe('DailyPostMortemCard', () => {
    const basePrediction: DailyPrediction = {
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
        created_at: '2026-09-28T09:15:00Z',
        updated_at: '2026-09-28T16:15:00Z',
    };

    it('renders null when no post-mortem data is present', () => {
        const { container } = render(<DailyPostMortemCard prediction={basePrediction} />);
        expect(container.firstChild).toBeNull();
    });

    it('renders diagnosis category and actionable lesson when post-mortem is available', () => {
        const postMortemPrediction: DailyPrediction = {
            ...basePrediction,
            postmortem_category: 'ACCURATE_CAPTURE',
            postmortem_flawed_assumption: 'None',
            postmortem_lesson:
                'When broad market weakness aligns with higher yields, retain directional signal.',
            was_predictable: true,
            postmortem_evaluated_at: '2026-09-28T17:15:00Z',
        };

        render(<DailyPostMortemCard prediction={postMortemPrediction} />);

        expect(screen.getByText('Post-Market Evaluation (GPT-5.6 Luna)')).toBeInTheDocument();
        expect(screen.getByText('ACCURATE CAPTURE')).toBeInTheDocument();
        expect(screen.getByText('PREDICTABLE PRE-MARKET')).toBeInTheDocument();
        expect(
            screen.getByText(
                'When broad market weakness aligns with higher yields, retain directional signal.',
            ),
        ).toBeInTheDocument();
        expect(screen.queryByText(/Flawed Morning Assumption/i)).toBeNull();
    });

    it('renders flawed assumption when present and not "None"', () => {
        const failedPrediction: DailyPrediction = {
            ...basePrediction,
            is_correct: false,
            postmortem_category: 'INTRADAY_REVERSAL',
            postmortem_flawed_assumption:
                'Assumed bond rout and credit stress would force the pre-market gap to fade.',
            postmortem_lesson:
                'When a major risk-relief catalyst lifts pre-market prices, do not fade on yields alone.',
            was_predictable: true,
            postmortem_evaluated_at: '2026-09-25T17:15:00Z',
        };

        render(<DailyPostMortemCard prediction={failedPrediction} />);

        expect(screen.getByText('INTRADAY REVERSAL')).toBeInTheDocument();
        expect(screen.getByText('Flawed Morning Assumption')).toBeInTheDocument();
        expect(
            screen.getByText(
                'Assumed bond rout and credit stress would force the pre-market gap to fade.',
            ),
        ).toBeInTheDocument();
        expect(
            screen.getByText(
                'When a major risk-relief catalyst lifts pre-market prices, do not fade on yields alone.',
            ),
        ).toBeInTheDocument();
    });

    it('renders noise badge when was_predictable is false', () => {
        const shockPrediction: DailyPrediction = {
            ...basePrediction,
            is_correct: false,
            postmortem_category: 'UNFORESEEN_SHOCK',
            postmortem_flawed_assumption: 'None',
            postmortem_lesson: 'Mid-day headline caused unexpected flash move.',
            was_predictable: false,
            postmortem_evaluated_at: '2026-09-24T17:15:00Z',
        };

        render(<DailyPostMortemCard prediction={shockPrediction} />);

        expect(screen.getByText('UNFORESEEN SHOCK')).toBeInTheDocument();
        expect(screen.getByText('UNFORESEEN / NOISE')).toBeInTheDocument();
    });
});
