import type { PromptExperiment } from '@llm-market-bench/database';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { StockPickerAutoresearchPanel } from './StockPickerAutoresearchPanel';

const mockExperiments: PromptExperiment[] = [
    {
        id: 'exp-ds-active',
        variant_tag: 'stock-v2-deepseek-flash',
        prompt_name: 'STOCK_PICKER_PROMPT',
        prompt_content:
            'Header\n=== LONG/SHORT RELATIVE SELECTION STRATEGY ===\nDeepSeek mutated strategy\n=== REQUIRED OUTPUT FORMAT ===\nFooter',
        track_id: 'deepseek-flash',
        status: 'active',
        experiment_type: 'incremental',
        parent_tag: 'stock-baseline-deepseek-flash',
        week_start: '2026-11-15',
        week_end: '2026-11-22',
        change_description: 'DeepSeek mutation',
        metrics: {
            hurdle_score: 64.0,
            hit_rate_pct: 60.0,
            ls_spread_alpha_pct: 2.2,
            conviction_norm: 52.0,
            sample_baskets: 5,
        },
        research_output: {
            research_insight: 'DeepSeek durable insight',
            is_cold_start: false,
        },
        is_backtest: false,
        created_at: '2026-11-15T22:00:00Z',
    },
    {
        id: 'exp-ds-base',
        variant_tag: 'stock-baseline-deepseek-flash',
        prompt_name: 'STOCK_PICKER_PROMPT',
        prompt_content:
            'Header\n=== LONG/SHORT RELATIVE SELECTION STRATEGY ===\nDeepSeek baseline strategy\n=== REQUIRED OUTPUT FORMAT ===\nFooter',
        track_id: 'deepseek-flash',
        status: 'baseline',
        experiment_type: 'baseline',
        parent_tag: null,
        week_start: '2026-11-08',
        week_end: '2026-11-15',
        change_description: 'Seeded baseline',
        metrics: {
            hurdle_score: 50.0,
            hit_rate_pct: 50.0,
            ls_spread_alpha_pct: 0.0,
            conviction_norm: 50.0,
            sample_baskets: 5,
        },
        research_output: null,
        is_backtest: false,
        created_at: '2026-11-08T22:00:00Z',
    },
];

describe('StockPickerAutoresearchPanel', () => {
    it('shows Consensus RRF explanation banner when selectedModel is consensus and allows switching tracks and variants', () => {
        const onSelectModel = vi.fn();
        render(
            <StockPickerAutoresearchPanel
                experiments={mockExperiments}
                selectedModel="consensus"
                onSelectModel={onSelectModel}
            />,
        );

        expect(
            screen.getByText(/Consensus RRF Aggregates 3 Independent Autoresearch Tracks/i),
        ).toBeInTheDocument();
        expect(screen.getAllByText(/DeepSeek mutated strategy/i).length).toBeGreaterThanOrEqual(1);

        // Click baseline variant in sidebar
        const baselineBtn = screen.getByRole('button', {
            name: /stock-baseline-deepseek-flash/i,
        });
        fireEvent.click(baselineBtn);
        expect(screen.getAllByText(/DeepSeek baseline strategy/i).length).toBeGreaterThanOrEqual(1);

        // Click MiniMax track card
        const minimaxTrackBtn = screen.getByRole('button', {
            name: /MiniMax-M3\.1-Flash/i,
        });
        fireEvent.click(minimaxTrackBtn);
        expect(onSelectModel).toHaveBeenCalledWith('MiniMax-M3.1-Flash');
    });

    it('renders empty state when selected track has no recorded experiments', () => {
        render(
            <StockPickerAutoresearchPanel
                experiments={mockExperiments}
                selectedModel="MiniMax-M3.1-Flash"
                onSelectModel={vi.fn()}
            />,
        );

        expect(
            screen.getByText(
                /No stock picker prompt experiments recorded for MiniMax-M3\.1-Flash/i,
            ),
        ).toBeInTheDocument();
    });
});
