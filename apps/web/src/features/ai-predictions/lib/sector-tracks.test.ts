import type { PromptExperiment } from '@llm-market-bench/database';
import { describe, expect, it } from 'vitest';
import type { SectorPrediction } from '../api/fetch-predictions';
import {
    calculateTrackBaselineScore,
    computeModelTrackSummaries,
    filterExperimentsByTrack,
    filterPredictionsByTrack,
    findTrackActiveVariant,
    getAvailableTracks,
    getExperimentTrackInfo,
    LEGACY_TRACK_CONFIG,
    SECTOR_MODEL_TRACKS,
} from './sector-tracks';

describe('sector-tracks domain logic', () => {
    const mockExperiments: PromptExperiment[] = [
        {
            id: 'exp-ds-1',
            prompt_name: 'SECTOR_PREDICTOR_PROMPT',
            variant_tag: 'sector-ds-v1.0',
            experiment_type: 'baseline',
            prompt_content: 'DeepSeek prompt',
            change_description: 'Initial DeepSeek',
            metrics: { score: 82.5 },
            status: 'saved',
            week_start: '2026-07-10',
            week_end: '2026-07-17',
            created_at: '2026-07-10T00:00:00Z',
            parent_tag: null,
            research_output: null,
            is_backtest: false,
            track_id: 'deepseek-v4-flash',
        },
        {
            id: 'exp-ds-2',
            prompt_name: 'SECTOR_PREDICTOR_PROMPT',
            variant_tag: 'sector-ds-v1.1',
            experiment_type: 'incremental',
            prompt_content: 'DeepSeek prompt 2',
            change_description: 'Evolved DeepSeek',
            metrics: { score: 86.4 },
            status: 'active',
            week_start: '2026-07-17',
            week_end: '2026-07-24',
            created_at: '2026-07-17T00:00:00Z',
            parent_tag: 'sector-ds-v1.0',
            research_output: null,
            is_backtest: false,
            track_id: 'deepseek-v4-flash',
        },
        {
            id: 'exp-mm-1',
            prompt_name: 'SECTOR_PREDICTOR_PROMPT',
            variant_tag: 'sector-mm-v1.0',
            experiment_type: 'baseline',
            prompt_content: 'MiniMax prompt',
            change_description: 'Initial MiniMax',
            metrics: { score: 79.2 },
            status: 'active',
            week_start: '2026-07-17',
            week_end: '2026-07-24',
            created_at: '2026-07-17T00:00:00Z',
            parent_tag: null,
            research_output: null,
            is_backtest: false,
            track_id: 'MiniMax-M3',
        },
        {
            id: 'exp-gemini-1',
            prompt_name: 'SECTOR_PREDICTOR_PROMPT',
            variant_tag: 'sector-gem-v1.0',
            experiment_type: 'baseline',
            prompt_content: 'Gemini prompt',
            change_description: 'Initial Gemini',
            metrics: { score: 89.1 },
            status: 'active',
            week_start: '2026-07-17',
            week_end: '2026-07-24',
            created_at: '2026-07-17T00:00:00Z',
            parent_tag: null,
            research_output: null,
            is_backtest: false,
            track_id: 'gemini-3.5-flash-lite',
        },
        {
            id: 'exp-gpt-1',
            prompt_name: 'SECTOR_PREDICTOR_PROMPT',
            variant_tag: 'sector-gpt-v1.0',
            experiment_type: 'baseline',
            prompt_content: 'GPT prompt',
            change_description: 'Initial GPT',
            metrics: { score: 83.0 },
            status: 'active',
            week_start: '2026-07-17',
            week_end: '2026-07-24',
            created_at: '2026-07-17T00:00:00Z',
            parent_tag: null,
            research_output: null,
            is_backtest: false,
            track_id: 'gpt-5.6-luna',
        },
        {
            id: 'exp-legacy-1',
            prompt_name: 'SECTOR_PREDICTOR_PROMPT',
            variant_tag: 'v1.0-legacy',
            experiment_type: 'baseline',
            prompt_content: 'Legacy prompt',
            change_description: 'Old format baseline',
            metrics: { score: 70.0 },
            status: 'saved',
            week_start: '2026-07-01',
            week_end: '2026-07-08',
            created_at: '2026-07-01T00:00:00Z',
            parent_tag: null,
            research_output: null,
            is_backtest: false,
            track_id: 'track_default',
        },
    ];

    it('matches model tracks accurately based on track_id and variant_tag', () => {
        const [ds, mm, gemini, gpt] = SECTOR_MODEL_TRACKS;

        expect(ds.matches('deepseek-v4-flash', 'v1.0')).toBe(true);
        expect(ds.matches(null, 'sector-deepseek-v2.0')).toBe(true);
        expect(ds.matches('MiniMax-M3', 'v1.0')).toBe(false);

        expect(mm.matches('MiniMax-M3', 'v1.0')).toBe(true);
        expect(gemini.matches('gemini-3.5-flash-lite', 'v1.0')).toBe(true);
        expect(gpt.matches('gpt-5.6-luna', 'v1.0')).toBe(true);
        expect(gpt.matches('openai/gpt-4o', 'v1.0')).toBe(true);

        expect(LEGACY_TRACK_CONFIG.matches('track_default', 'v1.0-legacy')).toBe(true);
        expect(LEGACY_TRACK_CONFIG.matches('deepseek-v4-flash', 'v1.0')).toBe(false);
    });

    it('identifies available tracks dynamically including legacy when present', () => {
        const tracksWithLegacy = getAvailableTracks(mockExperiments);
        expect(tracksWithLegacy.some((t) => t.id === 'legacy')).toBe(true);

        const onlyModern = mockExperiments.filter((e) => e.track_id !== 'track_default');
        const tracksWithoutLegacy = getAvailableTracks(onlyModern);
        expect(tracksWithoutLegacy.some((t) => t.id === 'legacy')).toBe(false);
    });

    it('filters experiments strictly by track ID', () => {
        const dsExps = filterExperimentsByTrack(mockExperiments, 'deepseek');
        expect(dsExps).toHaveLength(2);
        expect(dsExps.map((e) => e.id)).toEqual(['exp-ds-1', 'exp-ds-2']);

        const mmExps = filterExperimentsByTrack(mockExperiments, 'minimax');
        expect(mmExps).toHaveLength(1);
        expect(mmExps[0].id).toBe('exp-mm-1');

        const allExps = filterExperimentsByTrack(mockExperiments, 'all');
        expect(allExps).toHaveLength(6);

        const legacyExps = filterExperimentsByTrack(mockExperiments, 'legacy');
        expect(legacyExps).toHaveLength(1);
        expect(legacyExps[0].id).toBe('exp-legacy-1');
    });

    it('filters predictions by model name corresponding to track', () => {
        const mockPredictions = [
            { id: '1', model_name: 'deepseek-flash' },
            { id: '2', model_name: 'MiniMax-M3' },
            { id: '3', model_name: 'gemini-3.5-flash-lite' },
            { id: '4', model_name: 'gpt-5.6-luna' },
        ] as unknown as SectorPrediction[];

        const dsPreds = filterPredictionsByTrack(mockPredictions, 'deepseek');
        expect(dsPreds).toHaveLength(1);
        expect(dsPreds[0].model_name).toBe('deepseek-flash');

        const allPreds = filterPredictionsByTrack(mockPredictions, 'all');
        expect(allPreds).toHaveLength(4);
    });

    it('calculates track-specific baseline score and finds active variant', () => {
        const dsExps = filterExperimentsByTrack(mockExperiments, 'deepseek');
        expect(calculateTrackBaselineScore(dsExps)).toBe('86.4000');
        expect(findTrackActiveVariant(dsExps)).toBe('sector-ds-v1.1');

        const mmExps = filterExperimentsByTrack(mockExperiments, 'minimax');
        expect(calculateTrackBaselineScore(mmExps)).toBe('79.2000');
        expect(findTrackActiveVariant(mmExps)).toBe('sector-mm-v1.0');

        expect(calculateTrackBaselineScore([])).toBe('N/A');
        expect(findTrackActiveVariant([])).toBe('N/A');
    });

    it('computes model track summaries for the 4 models', () => {
        const summaries = computeModelTrackSummaries(mockExperiments);
        expect(summaries).toHaveLength(4);

        const dsSummary = summaries.find((s) => s.track.id === 'deepseek');
        expect(dsSummary?.activeVariant).toBe('sector-ds-v1.1');
        expect(dsSummary?.baselineScore).toBe('86.4000');
        expect(dsSummary?.experimentCount).toBe(2);
        expect(dsSummary?.status).toBe('active');

        const mmSummary = summaries.find((s) => s.track.id === 'minimax');
        expect(mmSummary?.activeVariant).toBe('sector-mm-v1.0');
        expect(mmSummary?.baselineScore).toBe('79.2000');
        expect(mmSummary?.experimentCount).toBe(1);

        const geminiSummary = summaries.find((s) => s.track.id === 'gemini');
        expect(geminiSummary?.activeVariant).toBe('sector-gem-v1.0');
        expect(geminiSummary?.baselineScore).toBe('89.1000');

        const gptSummary = summaries.find((s) => s.track.id === 'openai');
        expect(gptSummary?.activeVariant).toBe('sector-gpt-v1.0');
        expect(gptSummary?.baselineScore).toBe('83.0000');
    });

    it('resolves track info badge and label for individual experiments', () => {
        const dsInfo = getExperimentTrackInfo(mockExperiments[0]);
        expect(dsInfo.label).toBe('DeepSeek');
        expect(dsInfo.colorScheme).toBe('info');

        const mmInfo = getExperimentTrackInfo(mockExperiments[2]);
        expect(mmInfo.label).toBe('MiniMax');

        const legacyInfo = getExperimentTrackInfo(mockExperiments[5]);
        expect(legacyInfo.label).toBe('default');
    });
});
