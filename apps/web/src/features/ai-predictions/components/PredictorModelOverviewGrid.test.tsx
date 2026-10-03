import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { ModelTrackSummary } from '../lib/sector-tracks';
import { SECTOR_MODEL_TRACKS } from '../lib/sector-tracks';
import { PredictorModelOverviewGrid } from './PredictorModelOverviewGrid';

describe('PredictorModelOverviewGrid', () => {
    const mockSummaries: ModelTrackSummary[] = [
        {
            track: SECTOR_MODEL_TRACKS[0], // DeepSeek
            activeVariant: 'sector-ds-v1.4',
            baselineScore: '86.4000',
            numericBaselineScore: 86.4,
            experimentCount: 6,
            isColdStart: false,
            status: 'active',
        },
        {
            track: SECTOR_MODEL_TRACKS[1], // MiniMax
            activeVariant: 'sector-mm-v1.1',
            baselineScore: '79.2000',
            numericBaselineScore: 79.2,
            experimentCount: 4,
            isColdStart: true,
            status: 'active',
        },
    ];

    it('renders cards for each model summary with active variant and baseline score', () => {
        render(<PredictorModelOverviewGrid summaries={mockSummaries} onSelectTrack={vi.fn()} />);

        expect(screen.getByText('DeepSeek Flash')).toBeInTheDocument();
        expect(screen.getByText('sector-ds-v1.4')).toBeInTheDocument();
        expect(screen.getByText('86.4000')).toBeInTheDocument();

        expect(screen.getByText('MiniMax-M3')).toBeInTheDocument();
        expect(screen.getByText('sector-mm-v1.1')).toBeInTheDocument();
        expect(screen.getByText('79.2000')).toBeInTheDocument();
        expect(screen.getByText('From 0')).toBeInTheDocument();
    });

    it('invokes onSelectTrack when clicking a model card', () => {
        const onSelect = vi.fn();
        render(<PredictorModelOverviewGrid summaries={mockSummaries} onSelectTrack={onSelect} />);

        fireEvent.click(screen.getByText('DeepSeek Flash'));
        expect(onSelect).toHaveBeenCalledWith('deepseek');
    });
});
