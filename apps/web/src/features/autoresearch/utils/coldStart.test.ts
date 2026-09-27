import type { PromptExperiment } from '@llm-market-bench/database';
import { describe, expect, it } from 'vitest';
import { isExperimentColdStart, isTrackColdStart } from './coldStart';

describe('coldStart utils', () => {
    describe('isExperimentColdStart', () => {
        it('returns false when experiment is null or undefined', () => {
            expect(isExperimentColdStart(null)).toBe(false);
            expect(isExperimentColdStart(undefined)).toBe(false);
        });

        it('returns false when research_output has no is_cold_start flag', () => {
            const exp = {
                id: 'exp-1',
                research_output: { selected_tools: ['get_stock_quote'] },
            } as unknown as PromptExperiment;
            expect(isExperimentColdStart(exp)).toBe(false);
        });

        it('returns false when research_output is null or empty', () => {
            const exp = {
                id: 'exp-1',
                research_output: null,
            } as unknown as PromptExperiment;
            expect(isExperimentColdStart(exp)).toBe(false);
        });

        it('returns true when research_output.is_cold_start is true', () => {
            const exp = {
                id: 'exp-1',
                research_output: { is_cold_start: true },
            } as unknown as PromptExperiment;
            expect(isExperimentColdStart(exp)).toBe(true);
        });
    });

    describe('isTrackColdStart', () => {
        it('returns false when track has no experiments', () => {
            expect(isTrackColdStart('track_default', [])).toBe(false);
        });

        it('returns true when the active experiment for the track is cold start', () => {
            const experiments = [
                {
                    id: 'exp-1',
                    track_id: 'track_claude',
                    status: 'active',
                    research_output: { is_cold_start: true },
                },
                {
                    id: 'exp-2',
                    track_id: 'track_default',
                    status: 'active',
                    research_output: { is_cold_start: false },
                },
            ] as unknown as PromptExperiment[];

            expect(isTrackColdStart('track_claude', experiments)).toBe(true);
            expect(isTrackColdStart('track_default', experiments)).toBe(false);
        });

        it('prioritizes the active experiment over older saved experiments', () => {
            const experiments = [
                {
                    id: 'exp-1',
                    track_id: 'track_claude',
                    status: 'active',
                    research_output: { is_cold_start: false },
                },
                {
                    id: 'exp-2',
                    track_id: 'track_claude',
                    status: 'saved',
                    research_output: { is_cold_start: true },
                },
            ] as unknown as PromptExperiment[];

            // Active is false, even though an older saved one was cold start
            expect(isTrackColdStart('track_claude', experiments)).toBe(false);
        });

        it('falls back to latest experiment if no active experiment exists', () => {
            const experiments = [
                {
                    id: 'exp-1',
                    track_id: 'track_openai',
                    status: 'saved',
                    research_output: { is_cold_start: true },
                },
            ] as unknown as PromptExperiment[];

            expect(isTrackColdStart('track_openai', experiments)).toBe(true);
        });
    });
});
