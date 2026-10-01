import type { PromptExperiment } from '@llm-market-bench/database';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { VariantSidebar } from './VariantSidebar';

describe('VariantSidebar', () => {
    const mockExperiments: PromptExperiment[] = [
        {
            id: 'exp-1',
            prompt_name: 'DAILY_PREDICTOR_PROMPT',
            variant_tag: 'daily-active-1',
            experiment_type: 'baseline',
            prompt_content: 'Prompt content 1',
            change_description: 'Initial baseline',
            metrics: { score: 75.0 },
            status: 'active',
            week_start: '2026-08-03',
            week_end: '2026-08-10',
            created_at: '2026-08-03T00:00:00Z',
            parent_tag: null,
            research_output: null,
            is_backtest: false,
            track_id: 'deepseek-v4-flash',
        },
        {
            id: 'exp-2',
            prompt_name: 'DAILY_PREDICTOR_PROMPT',
            variant_tag: 'daily-variant-2',
            experiment_type: 'incremental',
            prompt_content: 'Prompt content 2',
            change_description: 'Cold start variant',
            metrics: { score: 62.0 },
            status: 'baseline',
            week_start: '2026-08-04',
            week_end: '2026-08-11',
            created_at: '2026-08-04T00:00:00Z',
            parent_tag: null,
            research_output: { is_cold_start: true },
            is_backtest: false,
            track_id: 'deepseek-v4-flash',
        },
    ];

    it('renders lineage list with scores and badges', () => {
        const onSelect = vi.fn();
        render(
            <VariantSidebar
                experiments={mockExperiments}
                selectedExpId="exp-1"
                activePromptTag="daily-active-1"
                onSelectExp={onSelect}
            />,
        );

        expect(screen.getByText('Experiment Lineage')).toBeInTheDocument();
        expect(screen.getByText('daily-active-1')).toBeInTheDocument();
        expect(screen.getByText('75.0')).toBeInTheDocument();
        expect(screen.getByText('🟢 ACTIVE')).toBeInTheDocument();

        expect(screen.getByText('daily-variant-2')).toBeInTheDocument();
        expect(screen.getByText('62.0')).toBeInTheDocument();
        expect(screen.getByText('🏆 BASELINE')).toBeInTheDocument();
        expect(screen.getByText('From 0')).toBeInTheDocument();
    });

    it('calls onSelectExp when clicked', () => {
        const onSelect = vi.fn();
        render(
            <VariantSidebar
                experiments={mockExperiments}
                selectedExpId="exp-1"
                activePromptTag="daily-active-1"
                onSelectExp={onSelect}
            />,
        );

        fireEvent.click(screen.getByText('daily-variant-2'));
        expect(onSelect).toHaveBeenCalledWith('exp-2');
    });
});
