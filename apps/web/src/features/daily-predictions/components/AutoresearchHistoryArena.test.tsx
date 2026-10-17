import type { PromptExperiment } from '@llm-market-bench/database';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { DailyPrediction } from '../api/fetch-daily-predictions';
import { AutoresearchHistoryArena } from './AutoresearchHistoryArena';

describe('AutoresearchHistoryArena', () => {
    const mockExperiment: PromptExperiment = {
        id: 'exp-arena-1',
        prompt_name: 'DAILY_PREDICTOR_PROMPT',
        variant_tag: 'daily-active-1',
        experiment_type: 'baseline',
        prompt_content: 'Test content.',
        change_description: 'Arena test description.',
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

    it('renders heading, active runtime badge, and sub-components', () => {
        render(
            <AutoresearchHistoryArena
                experiments={[mockExperiment]}
                selectedExpId="exp-arena-1"
                activePromptTag="daily-active-1"
                onSelectExp={vi.fn()}
            />,
        );

        expect(screen.getByText('Autoresearch Prompt Lineage & Benchmarks')).toBeInTheDocument();
        expect(screen.getByText('🟢 Active Runtime:')).toBeInTheDocument();
        expect(screen.getByText('🟢 CURRENT ACTIVE')).toBeInTheDocument();
        expect(screen.getByText('The Predictor Prompt')).toBeInTheDocument();
    });

    it('renders empty state when no experiments exist', () => {
        render(
            <AutoresearchHistoryArena
                experiments={[]}
                selectedExpId={null}
                onSelectExp={vi.fn()}
            />,
        );

        expect(
            screen.getByText(
                /No prompt experiments or autoresearch runs recorded for this model track yet/i,
            ),
        ).toBeInTheDocument();
    });

    it('renders resolved score when selected experiment has empty metrics but evaluated predictions exist', () => {
        const emptyMetricsExp: PromptExperiment = {
            id: 'exp-baseline',
            prompt_name: 'DAILY_PREDICTOR_PROMPT',
            variant_tag: 'daily-pred-baseline',
            experiment_type: 'baseline',
            prompt_content: 'Test content.',
            change_description: 'Arena test description.',
            metrics: {},
            status: 'baseline',
            created_at: '2026-08-04T00:00:00Z',
            parent_tag: null,
            research_output: null,
            is_backtest: false,
            track_id: 'deepseek-v4-flash',
            week_start: '2026-08-04',
            week_end: '2026-08-11',
        };

        const mockPredictions = [
            {
                id: 'pred-1',
                prediction_date: '2026-08-04',
                target_date: '2026-08-04',
                ticker: 'SPY',
                model_name: 'deepseek-v4-flash',
                prompt_variant_tag: 'daily-pred-baseline',
                status: 'evaluated',
                predicted_direction: 'UP',
                confidence: 70,
                expected_return_pct: 0.1,
                open_price: 760.63,
                close_price: 771.33,
                actual_direction: 'UP',
                is_correct: true,
                intraday_hit: true,
                brier_score: 0.2025,
            },
        ];

        render(
            <AutoresearchHistoryArena
                experiments={[emptyMetricsExp]}
                predictions={mockPredictions as unknown as DailyPrediction[]}
                selectedExpId="exp-baseline"
                activePromptTag="daily-pred-baseline"
                onSelectExp={vi.fn()}
            />,
        );

        expect(screen.getAllByText('daily-pred-baseline').length).toBeGreaterThan(0);
        expect(screen.getAllByText('80.59').length).toBeGreaterThanOrEqual(2);
        expect(screen.queryByText(/Pending/i)).not.toBeInTheDocument();
    });
});
