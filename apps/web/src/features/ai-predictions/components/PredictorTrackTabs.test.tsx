import type { PromptExperiment } from '@llm-market-bench/database';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SECTOR_MODEL_TRACKS } from '../lib/sector-tracks';
import { PredictorTrackTabs } from './PredictorTrackTabs';

describe('PredictorTrackTabs', () => {
    const mockExperiments: PromptExperiment[] = [
        {
            id: 'exp-ds-1',
            prompt_name: 'SECTOR_PREDICTOR_PROMPT',
            variant_tag: 'sector-ds-v1.0',
            experiment_type: 'baseline',
            prompt_content: 'p1',
            change_description: 'd1',
            metrics: { score: 85.0 },
            status: 'active',
            week_start: '2026-07-10',
            week_end: '2026-07-17',
            created_at: '2026-07-10T00:00:00Z',
            parent_tag: null,
            research_output: null,
            is_backtest: false,
            track_id: 'deepseek-v4-flash',
        },
        {
            id: 'exp-mm-1',
            prompt_name: 'SECTOR_PREDICTOR_PROMPT',
            variant_tag: 'sector-mm-v1.0',
            experiment_type: 'radical',
            prompt_content: 'p2',
            change_description: 'd2',
            metrics: { score: 78.0 },
            status: 'active',
            week_start: '2026-07-10',
            week_end: '2026-07-17',
            created_at: '2026-07-10T00:00:00Z',
            parent_tag: null,
            research_output: { is_cold_start: true },
            is_backtest: false,
            track_id: 'MiniMax-M3',
        },
    ];

    it('renders All Models tab and individual model tracks with counts', () => {
        const onSelect = vi.fn();
        render(
            <PredictorTrackTabs
                tracks={SECTOR_MODEL_TRACKS}
                activeTrack="all"
                onSelectTrack={onSelect}
                experiments={mockExperiments}
            />,
        );

        expect(screen.getByRole('button', { name: /All Models/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /DeepSeek Flash/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /MiniMax-M3/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Gemini 3.5/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /OpenAI GPT-5.6/i })).toBeInTheDocument();
    });

    it('triggers onSelectTrack callback when a track tab is clicked', () => {
        const onSelect = vi.fn();
        render(
            <PredictorTrackTabs
                tracks={SECTOR_MODEL_TRACKS}
                activeTrack="all"
                onSelectTrack={onSelect}
                experiments={mockExperiments}
            />,
        );

        fireEvent.click(screen.getByRole('button', { name: /DeepSeek Flash/i }));
        expect(onSelect).toHaveBeenCalledWith('deepseek');
    });

    it('renders "From 0" badge for cold-start tracks', () => {
        render(
            <PredictorTrackTabs
                tracks={SECTOR_MODEL_TRACKS}
                activeTrack="all"
                onSelectTrack={vi.fn()}
                experiments={mockExperiments}
            />,
        );

        expect(screen.getByText('From 0')).toBeInTheDocument();
    });
});
