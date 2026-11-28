import { describe, expect, it } from 'vitest';
import type { BacktestError } from '../types';
import {
    buildBacktestError,
    isQuotaLimitMessage,
    normalizeEquityTimestamp,
    toLiveEquitySnapshots,
    upsertSavedRecipeSummary,
} from './live-studio-helpers';

const baseList = [
    {
        id: 'rec-1',
        name: 'Old Name',
        cadence: '3h',
        is_live: false,
        trial_count: 0,
        updated_at: '2026-04-06T09:00:00Z',
    },
];

const savedRecipe = {
    id: 'rec-2',
    name: 'Trump & Chips',
    cadence: '3h',
    trial_count: 0,
    updated_at: '2026-04-06T09:32:00Z',
} as const;

describe('isQuotaLimitMessage', () => {
    it.each([
        'Daily backtest limit reached (2/2 in 24h).',
        'Concurrent backtest limit reached (1/1 active).',
        'Backtest queue is currently full (20/20).',
        'Scheduled live limit reached (1/1).',
    ])('returns true for %s', (msg) => expect(isQuotaLimitMessage(msg)).toBe(true));

    it.each([
        'Network timeout',
        'Navigation aborted',
        'Recipe not found',
        '',
    ])('returns false for %s', (msg) => expect(isQuotaLimitMessage(msg)).toBe(false));
});

describe('buildBacktestError', () => {
    it('classifies quota limit failures as kind quota without backtestJobId', () => {
        const err = buildBacktestError({
            err: new Error('Daily backtest limit reached (2/2 in 24h).'),
        }) as BacktestError;
        expect(err.kind).toBe('quota');
        expect(err.backtestJobId).toBeUndefined();
    });

    it('preserves the queued backtest job id when navigation fails', () => {
        const err = buildBacktestError({
            err: new Error('Navigation aborted'),
            queuedBacktestJobId: 'job-42',
        }) as BacktestError;
        expect(err.kind).toBe('navigation');
        expect(err.backtestJobId).toBe('job-42');
    });

    it('returns execution kind for generic failures', () => {
        const err = buildBacktestError({ err: new Error('Worker timed out') }) as BacktestError;
        expect(err.kind).toBe('execution');
        expect(err.message).toBe('Worker timed out');
    });

    it('handles a non-Error thrown value', () => {
        const err = buildBacktestError({ err: 'just a string' }) as BacktestError;
        expect(err.kind).toBe('execution');
        expect(err.message).toBe('Execution failed');
    });
});

describe('toLiveEquitySnapshots', () => {
    it('normalizes ET (EST and EDT) and ISO equity curve timestamps and sorts chronologically', () => {
        expect(normalizeEquityTimestamp('2026-11-14 09:30 ET')).toBe('2026-11-14T09:30:00-05:00');
        expect(normalizeEquityTimestamp('2026-07-14 09:30 ET')).toBe('2026-07-14T09:30:00-04:00');
        expect(normalizeEquityTimestamp('2026-11-15T14:30:00Z')).toBe('2026-11-15T14:30:00Z');
        expect(normalizeEquityTimestamp('not-a-date')).toBeNull();

        const snapshots = toLiveEquitySnapshots([
            { time: '2026-11-15 15:30 ET', equity: 10250 },
            { time: 'bad', equity: 9999 },
            { time: '2026-11-14 09:30 ET', equity: 10000 },
        ]);
        expect(snapshots).toEqual([
            { date: '2026-11-14T09:30:00-05:00', total_equity: 10000 },
            { date: '2026-11-15T15:30:00-05:00', total_equity: 10250 },
        ]);
    });
});

describe('upsertSavedRecipeSummary', () => {
    it('appends a brand new saved recipe', () => {
        const next = upsertSavedRecipeSummary(baseList as never, savedRecipe as never);
        expect(next).toHaveLength(2);
        expect(next[0].id).toBe('rec-2');
        expect(next[1].id).toBe('rec-1');
        expect(next[0].name).toBe('Trump & Chips');
    });

    it('updates an existing recipe in place', () => {
        const existing = { ...savedRecipe, id: 'rec-1', name: 'New Name' };
        const next = upsertSavedRecipeSummary(baseList as never, existing as never);
        expect(next).toHaveLength(1);
        expect(next[0].name).toBe('New Name');
    });

    it('applies an explicit is_live override', () => {
        const next = upsertSavedRecipeSummary(baseList as never, savedRecipe as never, true);
        const updated = next.find((r) => r.id === 'rec-2');
        expect(updated?.is_live).toBe(true);
    });
});

describe('isQuotaLimitMessage — token refusals', () => {
    it.each([
        ['a zero balance', 'You are out of tokens. Sign up to get 15 every week.'],
        ['an exhausted guest budget', "Today's guest runs are used up. Sign up to keep building."],
        [
            'the retired daily cap, still emitted by old clients',
            'Daily backtest limit reached (2/2 in 24h).',
        ],
        ['a full queue', 'Global queue is currently full. Try again shortly.'],
    ])('treats %s as a quota failure', (_label, message) => {
        expect(isQuotaLimitMessage(message)).toBe(true);
    });

    it('does not swallow unrelated execution errors', () => {
        expect(isQuotaLimitMessage('Could not reserve a token: empty response')).toBe(false);
        expect(isQuotaLimitMessage('Navigation aborted')).toBe(false);
    });
});
