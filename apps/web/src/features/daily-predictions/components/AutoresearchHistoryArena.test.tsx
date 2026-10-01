import type { PromptExperiment } from '@llm-market-bench/database';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
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
});
