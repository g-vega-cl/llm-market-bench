import type { PromptExperiment } from '@llm-market-bench/database';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { formatTrackLabel, TrackTabs } from './TrackTabs';

const mockExperiments: PromptExperiment[] = [
    {
        id: 'exp-1',
        variant_tag: 'v1',
        prompt_name: 'CORE_ANALYSIS_SYSTEM_PROMPT',
        prompt_content: 'Prompt content',
        week_start: '2026-07-20',
        week_end: '2026-07-26',
        metrics: { score: 5.2 },
        status: 'active',
        experiment_type: 'incremental',
        parent_tag: null,
        change_description: 'Initial',
        research_output: null,
        is_backtest: false,
        created_at: '2026-07-20T00:00:00Z',
        track_id: 'track_default',
    },
    {
        id: 'exp-2',
        variant_tag: 'v2',
        prompt_name: 'CORE_ANALYSIS_SYSTEM_PROMPT',
        prompt_content: 'Claude Prompt',
        week_start: '2026-07-20',
        week_end: '2026-07-26',
        metrics: { score: 8.4 },
        status: 'active',
        experiment_type: 'radical',
        parent_tag: null,
        change_description: 'Claude track',
        research_output: null,
        is_backtest: false,
        created_at: '2026-07-20T00:00:00Z',
        track_id: 'track_claude',
    },
];

describe('TrackTabs', () => {
    it('formats track labels correctly', () => {
        expect(formatTrackLabel('track_default')).toBe('Default Track (Combined)');
        expect(formatTrackLabel('track_claude')).toBe('Claude');
        expect(formatTrackLabel('track_openai_v2')).toBe('Openai v2');
    });

    it('renders track tabs with experiment counts and handles click', () => {
        const onSelect = vi.fn();

        render(
            <TrackTabs
                experiments={mockExperiments}
                activeTrack="track_default"
                onSelectTrack={onSelect}
            />,
        );

        expect(screen.getByText('Default Track (Combined)')).toBeInTheDocument();
        expect(screen.getByText('Claude')).toBeInTheDocument();

        fireEvent.click(screen.getByText('Claude'));
        expect(onSelect).toHaveBeenCalledWith('track_claude');
    });
});
