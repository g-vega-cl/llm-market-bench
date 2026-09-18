import type { PromptExperiment } from '@llm-market-bench/database';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { SectorPrediction } from '../api/fetch-predictions';
import { SectorScoreBreakdown } from './SectorScoreBreakdown';

describe('SectorScoreBreakdown', () => {
    const mockExperiment: PromptExperiment = {
        id: 'exp-1',
        track_id: 'deepseek-flash',
        variant_tag: 'v1.1',
        parent_tag: 'v1.0',
        prompt_content: 'Test sector prompt',
        metrics: {
            score: 74.25,
            base_percentile: 82.5,
            alpha_bonus: 3.25,
            mean_brier: 0.23,
            predictions_evaluated: 8,
        },
        change_description: 'Added volatility screening',
        experiment_type: 'mutation',
        prompt_name: 'SECTOR_PREDICTOR_PROMPT',
        is_backtest: false,
        status: 'evaluated',
        week_start: '2026-07-10',
        week_end: '2026-07-17',
        created_at: '2026-07-17T00:00:00Z',
        research_output: null,
    };

    it('renders headline score and formula substitution from experiment metrics', () => {
        render(<SectorScoreBreakdown experiment={mockExperiment} baselineScore={70.0} />);

        expect(screen.getByText('Sector Ratchet Score & Math Audit')).toBeInTheDocument();
        expect(screen.getByText('74.25')).toBeInTheDocument();
        expect(screen.getByText('v1.1')).toBeInTheDocument();
        expect(screen.getByText('+4.25 pts')).toBeInTheDocument();

        // Formula substitution
        expect(screen.getByText(/82.5%ile \(Base\)/)).toBeInTheDocument();
        expect(screen.getByText(/\+3.25% \(Alpha\)/)).toBeInTheDocument();
        expect(screen.getByText(/\(0.230 × 50.0\) \(Brier\)/)).toBeInTheDocument();

        // 3 Pillar Tiles
        expect(screen.getByText('Relative Percentile Rank')).toBeInTheDocument();
        expect(screen.getByText('82.5%')).toBeInTheDocument();
        expect(screen.getByText('S&P Alpha Bonus')).toBeInTheDocument();
        expect(screen.getByText('+3.25%')).toBeInTheDocument();
        expect(screen.getByText('Brier Calibration Penalty')).toBeInTheDocument();
        expect(screen.getByText('-11.50 pts')).toBeInTheDocument();
    });

    it('computes metrics from prediction sample when experiment.metrics is empty', () => {
        const samplePredictions: SectorPrediction[] = [
            {
                id: 'p1',
                prediction_date: '2026-07-10T00:00:00Z',
                target_date: '2026-07-17T00:00:00Z',
                timeframe: '7d',
                model_name: 'deepseek-flash',
                prompt_tag: 'v1.1',
                predicted_sector: 'XLK',
                predicted_pair: ['GLD', 'XLU'],
                reasoning: 'Tech momentum',
                sector_percentile_score: 90.0,
                worst_sector_percentile_score: 80.0,
                pair_percentile_score: 70.0,
                predicted_sector_return: 5.0,
                benchmark_spy_return: 2.0,
                sector_sp_diff: 3.0,
                brier_score: 0.1,
                status: 'evaluated',
                created_at: '2026-07-10T00:00:00Z',
            },
        ];

        const uncalculatedExperiment: PromptExperiment = {
            ...mockExperiment,
            metrics: {},
        };

        render(
            <SectorScoreBreakdown
                experiment={uncalculatedExperiment}
                predictions={samplePredictions}
            />,
        );

        // Average of (90+80+70)/3 = 80 base
        // Alpha bonus = 3.0
        // Brier penalty = 0.1 * 50 = 5.0
        // Total score = 80 + 3.0 - 5.0 = 78.0
        expect(screen.getByText('78.00')).toBeInTheDocument();
        expect(screen.getByText(/80.0%ile \(Base\)/)).toBeInTheDocument();
        expect(screen.getByText(/\+3.00% \(Alpha\)/)).toBeInTheDocument();
        expect(screen.getByText(/\(0.100 × 50.0\) \(Brier\)/)).toBeInTheDocument();
        // Sample warning for N < 5
        expect(
            screen.getByText(/Low sample window \(1 predictions evaluated\)/),
        ).toBeInTheDocument();
    });

    it('toggles collapsible methodology guide', () => {
        render(<SectorScoreBreakdown experiment={mockExperiment} />);

        expect(screen.queryByText(/Averages the percentile performance/)).not.toBeInTheDocument();

        const toggleBtn = screen.getByRole('button', { name: /How Sector Ratchet Scoring Works/i });
        fireEvent.click(toggleBtn);

        expect(screen.getByText(/Averages the percentile performance/)).toBeInTheDocument();
        expect(screen.getByText(/Awards additive bonus points/)).toBeInTheDocument();
        expect(screen.getByText(/Strictly penalizes uncalibrated confidence/)).toBeInTheDocument();

        fireEvent.click(toggleBtn);
        expect(screen.queryByText(/Averages the percentile performance/)).not.toBeInTheDocument();
    });
});
