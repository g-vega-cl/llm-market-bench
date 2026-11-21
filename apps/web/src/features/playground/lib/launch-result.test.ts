import { describe, expect, it } from 'vitest';
import { launchMessage, normalizeLaunchRow } from './launch-result';

const NOW = new Date('2026-11-20T15:00:00Z');

describe('normalizeLaunchRow', () => {
    it('maps a queued backtest with its live state', () => {
        const result = normalizeLaunchRow(
            { recipe_id: 'r1', job_id: 'j1', live_state: 'live', reason: 'ok' },
            NOW,
        );
        expect(result).toMatchObject({
            kind: 'backtest',
            recipeId: 'r1',
            jobId: 'j1',
            live: 'live',
        });
    });

    it('treats a replayed request as the same backtest', () => {
        const result = normalizeLaunchRow(
            { recipe_id: 'r1', job_id: 'j1', live_state: 'not-requested', reason: 'replay' },
            NOW,
        );
        expect(result.kind).toBe('backtest');
    });

    it('reports a cap as blocked instead of as an error', () => {
        expect(
            normalizeLaunchRow(
                { recipe_id: 'r1', live_state: 'not-requested', reason: 'daily-cap' },
                NOW,
            ),
        ).toMatchObject({ kind: 'blocked', reason: 'daily-cap' });
        expect(
            normalizeLaunchRow({ recipe_id: 'r1', live_state: 'denied', reason: 'live-cap' }, NOW),
        ).toMatchObject({ kind: 'blocked', reason: 'live-cap' });
    });

    it('keeps a live recipe with no job reachable', () => {
        expect(
            normalizeLaunchRow(
                { recipe_id: 'r1', job_id: null, live_state: 'live', reason: 'ok' },
                NOW,
            ),
        ).toMatchObject({ kind: 'live-only', recipeId: 'r1' });
    });

    it('marks an invalid graph as invalid rather than retryable', () => {
        expect(normalizeLaunchRow({ reason: 'invalid-graph' }, NOW)).toMatchObject({
            kind: 'invalid',
        });
    });

    it('never returns a variant without a recipe id or a message', () => {
        const empty = normalizeLaunchRow(null, NOW);
        expect(empty.kind).toBe('error');
        expect(launchMessage(empty)).not.toBe('');
    });
});

describe('launchMessage', () => {
    it('names the next slot for a live bot', () => {
        const message = launchMessage({
            kind: 'backtest',
            recipeId: 'r1',
            jobId: 'j1',
            live: 'live',
            nextSlotLabel: 'Mon 09:30 ET',
            queuePosition: 2,
        });
        expect(message).toContain('Mon 09:30 ET');
        expect(message).toContain('Queue position 3');
    });

    it('explains a blocked run without pretending it failed', () => {
        const message = launchMessage({
            kind: 'blocked',
            recipeId: 'r1',
            reason: 'daily-cap',
            nextResetLabel: 'tomorrow (limits reset daily)',
        });
        expect(message).toMatch(/^Saved, but no run was queued/);
    });
});
