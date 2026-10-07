import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { EarningsPrediction } from '../api/fetch-earnings-predictions';
import { EarningsArenaTab } from './EarningsArenaTab';

const mockPredictions: EarningsPrediction[] = [
    {
        id: 'pred-1',
        prediction_date: '2026-10-07',
        target_date: '2026-10-07',
        ticker: 'NVDA',
        model_name: 'gpt-5.6-luna',
        prompt_variant_tag: 'earnings-pred-gpt-5.6-luna',
        predicted_direction: 'UP',
        confidence: 85.0,
        expected_return_pct: 2.8,
        rationale: 'GPT Luna: SUE beat.',
        catalysts: ['SUE 3.4'],
        report_timing: 'BMO',
        actual_eps: 1.25,
        estimated_eps: 1.1,
        eps_surprise: 0.15,
        revenue_surprise_pct: 5.26,
        sue_score: 3.4,
        open_price: 128.4,
        close_price: 132.1,
        actual_direction: 'UP',
        is_correct: true,
        brier_score: 0.0225,
        status: 'evaluated',
        created_at: '2026-10-07T13:00:00Z',
    },
    {
        id: 'pred-2',
        prediction_date: '2026-10-07',
        target_date: '2026-10-07',
        ticker: 'NVDA',
        model_name: '~typesafe/jev-latest',
        prompt_variant_tag: 'earnings-pred-~typesafe/jev-latest',
        predicted_direction: 'UP',
        confidence: 78.0,
        expected_return_pct: 0.0,
        rationale: 'Jev System One: UP',
        catalysts: [],
        report_timing: 'BMO',
        actual_eps: 1.25,
        estimated_eps: 1.1,
        eps_surprise: 0.15,
        revenue_surprise_pct: 5.26,
        sue_score: 3.4,
        open_price: 128.4,
        close_price: 132.1,
        actual_direction: 'UP',
        is_correct: true,
        brier_score: 0.0484,
        status: 'evaluated',
        created_at: '2026-10-07T13:00:00Z',
    },
    {
        id: 'pred-3',
        prediction_date: '2026-10-07',
        target_date: '2026-10-07',
        ticker: 'ADBE',
        model_name: 'deepseek-chat',
        prompt_variant_tag: 'earnings-pred-deepseek-chat',
        predicted_direction: 'DOWN',
        confidence: 65.0,
        expected_return_pct: -1.5,
        rationale: 'DeepSeek: Fade',
        catalysts: [],
        report_timing: 'AMC',
        actual_eps: 4.8,
        estimated_eps: 4.75,
        eps_surprise: 0.05,
        revenue_surprise_pct: 0.2,
        sue_score: 0.8,
        open_price: 512.0,
        close_price: 520.0,
        actual_direction: 'UP',
        is_correct: false,
        brier_score: 0.4225,
        status: 'evaluated',
        created_at: '2026-10-07T13:00:00Z',
    },
];

describe('EarningsArenaTab', () => {
    it('renders the triad model leaderboard and calculates hit rates', () => {
        render(<EarningsArenaTab predictions={mockPredictions} />);

        // Header and description
        expect(screen.getByText('Day-1 Earnings Movement Arena')).toBeInTheDocument();

        // Model names in cards / filters / table
        expect(screen.getAllByText('GPT Luna').length).toBeGreaterThan(0);
        expect(screen.getAllByText('DeepSeek Flash').length).toBeGreaterThan(0);
        expect(screen.getAllByText('TypeSafe Jev').length).toBeGreaterThan(0);

        // Luna hit rate is 100% (1/1)
        expect(screen.getAllByText('100%').length).toBeGreaterThan(0);
        // DeepSeek hit rate is 0% (0/1)
        expect(screen.getByText('0%')).toBeInTheDocument();
    });

    it('renders table rows and allows filtering by direction', () => {
        render(<EarningsArenaTab predictions={mockPredictions} />);

        // Check tickers present
        expect(screen.getAllByText('NVDA').length).toBe(2);
        expect(screen.getByText('ADBE')).toBeInTheDocument();

        // Check outcome badges
        expect(screen.getAllByText('HIT').length).toBe(2);
        expect(screen.getByText('MISS')).toBeInTheDocument();

        // Filter by DOWN direction
        const downFilterBtn = screen.getByRole('button', { name: 'DOWN' });
        fireEvent.click(downFilterBtn);

        // ADBE should still be visible, NVDA should be filtered out
        expect(screen.getByText('ADBE')).toBeInTheDocument();
        expect(screen.queryByText('NVDA')).not.toBeInTheDocument();
    });
});
