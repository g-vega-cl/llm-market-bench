import type { PromptExperiment } from '@llm-market-bench/database';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AutoresearchMilestoneCards } from './AutoresearchMilestoneCards';

describe('AutoresearchMilestoneCards', () => {
    it('renders evaluated milestone metrics properly', () => {
        const experiments: PromptExperiment[] = [
            {
                id: 'exp-1',
                prompt_name: 'DAILY_PREDICTOR_PROMPT',
                variant_tag: 'daily-active-1',
                experiment_type: 'incremental',
                prompt_content: 'Test prompt.',
                change_description: 'Test change.',
                metrics: { score: 75.0 },
                status: 'active',
                week_start: '2026-08-03',
                week_end: '2026-08-10',
                created_at: '2026-08-03T00:00:00Z',
                parent_tag: 'daily-parent-1',
                research_output: null,
                is_backtest: false,
                track_id: 'deepseek-v4-flash',
            },
            {
                id: 'exp-parent',
                prompt_name: 'DAILY_PREDICTOR_PROMPT',
                variant_tag: 'daily-parent-1',
                experiment_type: 'baseline',
                prompt_content: 'Parent prompt.',
                change_description: 'Parent baseline.',
                metrics: { score: 70.0 },
                status: 'baseline',
                week_start: '2026-07-27',
                week_end: '2026-08-03',
                created_at: '2026-07-27T00:00:00Z',
                parent_tag: null,
                research_output: null,
                is_backtest: false,
                track_id: 'deepseek-v4-flash',
            },
        ];

        render(<AutoresearchMilestoneCards experiments={experiments} />);

        expect(screen.getByText('Current Active Prompt')).toBeInTheDocument();
        expect(screen.getByText('daily-active-1')).toBeInTheDocument();
        expect(screen.getByText('🟢 ACTIVE')).toBeInTheDocument();

        expect(screen.getByText('Active Ratchet Score')).toBeInTheDocument();
        expect(screen.getAllByText('75.00').length).toBe(2);

        expect(screen.getByText('All-Time Best Baseline')).toBeInTheDocument();
        expect(screen.getByText('Score Progression')).toBeInTheDocument();
        expect(screen.getByText('▲ +5.00 vs Parent')).toBeInTheDocument();

        expect(screen.getByText('Mutated Variants Tracked')).toBeInTheDocument();
        expect(screen.getByText('2')).toBeInTheDocument();
    });

    it('renders pending state when active variant has no score yet', () => {
        const pendingExperiments: PromptExperiment[] = [
            {
                id: 'exp-pending',
                prompt_name: 'DAILY_PREDICTOR_PROMPT',
                variant_tag: 'daily-pending-1',
                experiment_type: 'incremental',
                prompt_content: 'Pending prompt.',
                change_description: 'Pending change.',
                metrics: null,
                status: 'active',
                week_start: '2026-09-01',
                week_end: '2026-09-08',
                created_at: '2026-09-01T00:00:00Z',
                parent_tag: null,
                research_output: null,
                is_backtest: false,
                track_id: 'deepseek-v4-flash',
            },
        ];

        render(<AutoresearchMilestoneCards experiments={pendingExperiments} />);

        expect(screen.getByText('Pending')).toBeInTheDocument();
        expect(screen.getByText('Pending Evaluation')).toBeInTheDocument();
    });
});
