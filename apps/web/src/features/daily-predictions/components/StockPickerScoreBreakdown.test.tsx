import type { PromptExperiment } from '@llm-market-bench/database';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { clampNormalizedAlpha, StockPickerScoreBreakdown } from './StockPickerScoreBreakdown';

describe('StockPickerScoreBreakdown', () => {
    it('clampNormalizedAlpha maps percentage alpha to [0, 100] centered at 50', () => {
        expect(clampNormalizedAlpha(0)).toBe(50.0);
        expect(clampNormalizedAlpha(2.0)).toBe(70.0);
        expect(clampNormalizedAlpha(-2.0)).toBe(30.0);
        expect(clampNormalizedAlpha(8.0)).toBe(100.0);
        expect(clampNormalizedAlpha(-8.0)).toBe(0.0);
    });

    it('renders pending evaluation notice when hurdle_score is not yet calculated', () => {
        const pendingExp = {
            id: 'exp-pending',
            variant_tag: 'stock-v1-deepseek-flash',
            prompt_name: 'STOCK_PICKER_PROMPT',
            prompt_content: 'content',
            track_id: 'deepseek-flash',
            status: 'active',
            experiment_type: 'incremental',
            parent_tag: 'stock-baseline-deepseek-flash',
            week_start: '2026-11-15',
            week_end: '2026-11-22',
            change_description: 'Pending mutation',
            metrics: {},
            research_output: null,
            is_backtest: false,
            created_at: '2026-11-15T22:00:00Z',
        } satisfies PromptExperiment;

        render(<StockPickerScoreBreakdown experiment={pendingExp} />);

        expect(screen.getByText('Pending Evaluation')).toBeInTheDocument();
        expect(screen.getByText(/collecting live 3 UP \/ 3 DOWN sessions/i)).toBeInTheDocument();
    });

    it('renders formula substitution and 3-pillar breakdown for evaluated experiments', () => {
        const evaluatedExp = {
            id: 'exp-eval',
            variant_tag: 'stock-v2-deepseek-flash',
            prompt_name: 'STOCK_PICKER_PROMPT',
            prompt_content: 'content',
            track_id: 'deepseek-flash',
            status: 'baseline',
            experiment_type: 'incremental',
            parent_tag: 'stock-baseline-deepseek-flash',
            week_start: '2026-11-08',
            week_end: '2026-11-15',
            change_description: 'Evaluated mutation',
            metrics: {
                hurdle_score: 63.0,
                hit_rate_pct: 60.0,
                ls_spread_alpha_pct: 2.0,
                conviction_norm: 50.0,
                sample_baskets: 5,
            },
            research_output: null,
            is_backtest: false,
            created_at: '2026-11-08T22:00:00Z',
        } satisfies PromptExperiment;

        render(<StockPickerScoreBreakdown experiment={evaluatedExp} />);

        expect(screen.getByText('5 Sessions Evaluated')).toBeInTheDocument();
        expect(screen.getByText('Hurdle Score: 63.00')).toBeInTheDocument();
        expect(screen.getByText('60.0%')).toBeInTheDocument();
        expect(screen.getByText('+2.00%')).toBeInTheDocument();
        expect(screen.getByText('50.0')).toBeInTheDocument();
    });
});
