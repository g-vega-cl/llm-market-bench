import type { PromptExperiment } from '@llm-market-bench/database';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { SectorPrediction } from '../api/fetch-predictions';
import { PredictorAutoresearchTab } from './PredictorAutoresearchTab';

describe('PredictorAutoresearchTab', () => {
    const mockExperiments: PromptExperiment[] = [
        {
            id: 'exp-ds-1',
            prompt_name: 'SECTOR_PREDICTOR_PROMPT',
            variant_tag: 'sector-ds-v1.0',
            experiment_type: 'baseline',
            prompt_content: `=== CONSTRAINTS ===
Header
=== INSTRUCTIONS ===
DeepSeek strategies
=== REQUIRED OUTPUT FORMAT ===
Footer`,
            change_description: 'DeepSeek baseline',
            metrics: { score: 86.4, base_percentile: 85.0, alpha_bonus: 3.0, mean_brier: 0.05 },
            status: 'active',
            week_start: '2026-07-10',
            week_end: '2026-07-17',
            created_at: '2026-07-10T00:00:00Z',
            parent_tag: null,
            research_output: {
                research_insight: 'Tech momentum leads.',
                confidence: 0.85,
                selected_tools: ['get_historical_correlation'],
            },
            is_backtest: false,
            track_id: 'deepseek-v4-flash',
        },
        {
            id: 'exp-mm-1',
            prompt_name: 'SECTOR_PREDICTOR_PROMPT',
            variant_tag: 'sector-mm-v1.0',
            experiment_type: 'radical',
            prompt_content: `=== CONSTRAINTS ===
Header
=== INSTRUCTIONS ===
MiniMax strategies
=== REQUIRED OUTPUT FORMAT ===
Footer`,
            change_description: 'MiniMax baseline',
            metrics: { score: 79.2, base_percentile: 75.0, alpha_bonus: 5.0, mean_brier: 0.08 },
            status: 'active',
            week_start: '2026-07-10',
            week_end: '2026-07-17',
            created_at: '2026-07-10T00:00:00Z',
            parent_tag: null,
            research_output: {
                is_cold_start: true,
                research_insight: 'Energy value rotation.',
                confidence: 0.78,
            },
            is_backtest: false,
            track_id: 'MiniMax-M3',
        },
    ];

    const mockPredictions: SectorPrediction[] = [
        {
            id: 'pred-1',
            prediction_date: '2026-07-10',
            target_date: '2026-07-17',
            timeframe: '7d',
            model_name: 'deepseek-v4-flash',
            prompt_tag: 'sector-ds-v1.0',
            predicted_sector: 'XLK',
            predicted_pair: ['GLD', 'XLU'],
            reasoning: 'Tech momentum',
            sector_percentile_score: 90.0,
            pair_percentile_score: 80.0,
            status: 'evaluated',
            created_at: '2026-07-10T00:00:00Z',
        },
    ];

    it('renders multi-model overview grid and track tabs when All Models is active', () => {
        render(
            <PredictorAutoresearchTab
                experimentsList={mockExperiments}
                predictions={mockPredictions}
                initialTrack="all"
            />,
        );

        // Check Overview Grid
        expect(screen.getByText('Multi-Model Sector Autoresearch Tracks')).toBeInTheDocument();
        expect(screen.getAllByText('DeepSeek Flash').length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText('sector-ds-v1.0').length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText('86.4000')).toBeInTheDocument();

        expect(screen.getAllByText('MiniMax-M3').length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText('sector-mm-v1.0').length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText('79.2000')).toBeInTheDocument();

        // Check History table has model badges
        expect(screen.getAllByText('DeepSeek').length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText('MiniMax').length).toBeGreaterThanOrEqual(1);
    });

    it('filters view and metrics strictly to selected model track', () => {
        render(
            <PredictorAutoresearchTab
                experimentsList={mockExperiments}
                predictions={mockPredictions}
                initialTrack="all"
            />,
        );

        // Click DeepSeek Flash track tab
        const dsButtons = screen.getAllByRole('button', { name: /DeepSeek Flash/i });
        fireEvent.click(dsButtons[0]);

        // Multi-model overview grid should be hidden, model-specific cards shown
        expect(
            screen.queryByText('Multi-Model Sector Autoresearch Tracks'),
        ).not.toBeInTheDocument();
        expect(screen.getByText('DeepSeek Flash All-Time Baseline Score')).toBeInTheDocument();
        expect(screen.getByText('86.4000')).toBeInTheDocument();
        expect(screen.getByText('DeepSeek Flash Active Prompt')).toBeInTheDocument();

        // History table should show DeepSeek History
        expect(screen.getByText('DeepSeek History')).toBeInTheDocument();
        expect(screen.getAllByText('sector-ds-v1.0').length).toBeGreaterThanOrEqual(1);
        expect(screen.queryByText('sector-mm-v1.0')).not.toBeInTheDocument();
    });

    it('displays cold-start badge and research details for radical variants', () => {
        render(
            <PredictorAutoresearchTab
                experimentsList={mockExperiments}
                predictions={mockPredictions}
                initialTrack="minimax"
            />,
        );

        expect(screen.getByText('MiniMax-M3 All-Time Baseline Score')).toBeInTheDocument();
        expect(screen.getByText('79.2000')).toBeInTheDocument();
        expect(screen.getAllByText('From 0').length).toBeGreaterThanOrEqual(1);
    });
});
