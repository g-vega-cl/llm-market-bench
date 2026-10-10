import type { PromptExperiment } from '@llm-market-bench/database';
import { describe, expect, it } from 'vitest';
import type { DailyPrediction } from '../api/fetch-daily-predictions';
import {
    computeDailyPredictionStats,
    computeExperimentMilestones,
    DEFAULT_DAILY_PREDICTOR_TOOLS,
    formatDeltaText,
    getActiveBadge,
    getDeltaColor,
    getMilestoneSubtitle,
    getPredictorModelsForTicker,
    getSidebarStatusBadge,
    PREDICTOR_MODELS,
    parseCuratedManifest,
    resolveActiveDailyPrompt,
} from './daily-predictions-helpers';

describe('daily-predictions-helpers', () => {
    it('defines PREDICTOR_MODELS with proper matching', () => {
        expect(PREDICTOR_MODELS).toHaveLength(4);
        const deepseek = PREDICTOR_MODELS[0];
        expect(deepseek.matches('deepseek-v4-flash')).toBe(true);
        expect(deepseek.matches('MiniMax')).toBe(false);

        const minimax = PREDICTOR_MODELS[1];
        expect(minimax.matches('MiniMax-M3')).toBe(true);

        const jev = PREDICTOR_MODELS[2];
        expect(jev.matches('~typesafe/jev-latest')).toBe(true);

        const jevLocal = PREDICTOR_MODELS[3];
        expect(jevLocal.id).toBe('jev-local-autoresearched');
        expect(jevLocal.label).toBe('Jev (Local Champion)');
        expect(jevLocal.matches('jev-local-autoresearched')).toBe(true);
    });

    it('defines getPredictorModelsForTicker with SPY and TLT models', () => {
        const spyModels = getPredictorModelsForTicker('SPY');
        expect(spyModels).toHaveLength(4);
        expect(spyModels[0].id).toBe('deepseek-v4-flash');
        expect(spyModels[1].id).toBe('MiniMax-M3');
        expect(spyModels[2].id).toBe('~typesafe/jev-latest');
        expect(spyModels[3].id).toBe('jev-local-autoresearched');

        const bondModels = getPredictorModelsForTicker('TLT');
        expect(bondModels).toHaveLength(3);
        expect(bondModels[0].id).toBe('gpt-5.6-luna');
        expect(bondModels[0].label).toBe('GPT-5.6 Luna');
        expect(bondModels[0].matches('gpt-5.6-luna')).toBe(true);
        expect(bondModels[1].id).toBe('deepseek-v4-flash');
        expect(bondModels[2].id).toBe('~typesafe/jev-latest');
    });

    it('defines DEFAULT_DAILY_PREDICTOR_TOOLS', () => {
        expect(DEFAULT_DAILY_PREDICTOR_TOOLS).toContain('fetch_daily_newsletter');
        expect(DEFAULT_DAILY_PREDICTOR_TOOLS).toContain('get_premarket_quote');
    });

    describe('computeDailyPredictionStats', () => {
        it('calculates stats correctly for evaluated predictions', () => {
            const predictions: DailyPrediction[] = [
                {
                    id: '1',
                    prediction_date: '2026-08-01',
                    target_date: '2026-08-01',
                    ticker: 'SPY',
                    model_name: 'deepseek',
                    predicted_direction: 'UP',
                    confidence: 80,
                    status: 'evaluated',
                    is_correct: true,
                    intraday_hit: true,
                    brier_score: 0.04,
                } as DailyPrediction,
                {
                    id: '2',
                    prediction_date: '2026-08-02',
                    target_date: '2026-08-02',
                    ticker: 'SPY',
                    model_name: 'deepseek',
                    predicted_direction: 'DOWN',
                    confidence: 70,
                    status: 'evaluated',
                    is_correct: false,
                    intraday_hit: false,
                    brier_score: 0.36,
                } as DailyPrediction,
                {
                    id: '3',
                    prediction_date: '2026-08-03',
                    target_date: '2026-08-03',
                    ticker: 'SPY',
                    model_name: 'deepseek',
                    predicted_direction: 'UP',
                    confidence: 60,
                    status: 'pending',
                } as DailyPrediction,
            ];

            const stats = computeDailyPredictionStats(predictions);
            expect(stats.totalEvaluated).toBe(2);
            expect(stats.correctCount).toBe(1);
            expect(stats.accuracyPct).toBe('50.0');
            expect(stats.intradayHitPct).toBe('50.0');
            expect(stats.avgBrier).toBe('0.2000');
        });

        it('handles empty predictions list', () => {
            const stats = computeDailyPredictionStats([]);
            expect(stats.totalEvaluated).toBe(0);
            expect(stats.correctCount).toBe(0);
            expect(stats.accuracyPct).toBe('N/A');
            expect(stats.intradayHitPct).toBe('N/A');
            expect(stats.avgBrier).toBe('N/A');
        });
    });

    describe('resolveActiveDailyPrompt', () => {
        it('prioritizes newest active prompt over baseline', () => {
            const experiments: PromptExperiment[] = [
                {
                    id: '1',
                    variant_tag: 'v1',
                    status: 'baseline',
                    created_at: '2026-08-01T00:00:00Z',
                } as PromptExperiment,
                {
                    id: '2',
                    variant_tag: 'v2',
                    status: 'active',
                    created_at: '2026-08-02T00:00:00Z',
                } as PromptExperiment,
            ];

            const res = resolveActiveDailyPrompt(experiments);
            expect(res.activePrompt?.variant_tag).toBe('v2');
            expect(res.isBaselineAnchor).toBe(false);
        });

        it('falls back to baseline when active is not found', () => {
            const experiments: PromptExperiment[] = [
                {
                    id: '1',
                    variant_tag: 'baseline-1',
                    status: 'baseline',
                    created_at: '2026-08-01T00:00:00Z',
                } as PromptExperiment,
            ];

            const res = resolveActiveDailyPrompt(experiments);
            expect(res.activePrompt?.variant_tag).toBe('baseline-1');
            expect(res.isBaselineAnchor).toBe(true);
        });
    });

    describe('computeExperimentMilestones', () => {
        it('computes delta against parent experiment', () => {
            const experiments: PromptExperiment[] = [
                {
                    id: 'parent',
                    variant_tag: 'parent-tag',
                    status: 'baseline',
                    metrics: { score: 70.0 },
                    created_at: '2026-08-01T00:00:00Z',
                } as unknown as PromptExperiment,
                {
                    id: 'child',
                    variant_tag: 'child-tag',
                    parent_tag: 'parent-tag',
                    status: 'active',
                    metrics: { score: 75.5 },
                    created_at: '2026-08-02T00:00:00Z',
                } as unknown as PromptExperiment,
            ];

            const milestones = computeExperimentMilestones(experiments);
            expect(milestones.activeScore).toBe(75.5);
            expect(milestones.bestBaselineScore).toBe(75.5);
            expect(milestones.delta).toBe(5.5);
        });
    });

    describe('formatDeltaText and getDeltaColor', () => {
        it('formats evaluating state', () => {
            expect(formatDeltaText(null, true)).toBe('Pending Evaluation');
            expect(formatDeltaText(null, false)).toBe('Baseline Initialized');
            expect(formatDeltaText(2.5, false)).toBe('▲ +2.50 vs Parent');
            expect(formatDeltaText(-1.5, false)).toBe('▼ -1.50 vs Parent');
        });

        it('gets color for deltas', () => {
            expect(getDeltaColor(null)).toBe('#0f172a');
            expect(getDeltaColor(1.0)).toBe('#16a34a');
            expect(getDeltaColor(-1.0)).toBe('#dc2626');
        });
    });

    describe('badge and subtitle helpers', () => {
        it('returns proper active badges', () => {
            expect(getActiveBadge('active')).toEqual({ text: '🟢 ACTIVE', colorScheme: 'success' });
            expect(getActiveBadge('baseline')).toEqual({
                text: '🏆 BASELINE',
                colorScheme: 'accent',
            });
            expect(getActiveBadge('saved')).toEqual({ text: '📦 SAVED', colorScheme: 'neutral' });
        });

        it('returns proper milestone subtitle', () => {
            expect(getMilestoneSubtitle(true)).toBe('Ratchet-reverted to all-time benchmark');
            expect(getMilestoneSubtitle(false, 'active')).toBe(
                'Live mutated strategy undergoing evaluation',
            );
            expect(getMilestoneSubtitle(false, 'discarded')).toBe('Status: discarded');
        });

        it('returns proper sidebar status badges', () => {
            expect(getSidebarStatusBadge('active', true)).toEqual({
                colorScheme: 'success',
                label: '🟢 ACTIVE',
            });
            expect(getSidebarStatusBadge('active', false)).toEqual({
                colorScheme: 'neutral',
                label: '📦 SAVED',
            });
            expect(getSidebarStatusBadge('baseline', false)).toEqual({
                colorScheme: 'accent',
                label: '🏆 BASELINE',
            });
            expect(getSidebarStatusBadge('discarded', false)).toEqual({
                colorScheme: 'danger',
                label: '❌ DISCARDED',
            });
        });
    });

    describe('parseCuratedManifest', () => {
        it('returns null for null, undefined, or empty string', () => {
            expect(parseCuratedManifest(null)).toBeNull();
            expect(parseCuratedManifest(undefined)).toBeNull();
            expect(parseCuratedManifest('')).toBeNull();
        });

        it('returns null for plain text prompt content', () => {
            expect(parseCuratedManifest('You are a predictor model')).toBeNull();
        });

        it('extracts manifest from valid JSON prompt content', () => {
            const json = JSON.stringify({
                criteria: { UP: 'Bullish criteria', DOWN: 'Bearish criteria' },
                manifest: {
                    selected_newsletters: ['Sherwood News', 'Chartr'],
                    include_macro_proxies: ['QQQ', 'IWM'],
                    include_intraday_profile: true,
                },
            });
            const parsed = parseCuratedManifest(json);
            expect(parsed).toEqual({
                selected_newsletters: ['Sherwood News', 'Chartr'],
                include_macro_proxies: ['QQQ', 'IWM'],
                include_intraday_profile: true,
            });
        });
    });
});
