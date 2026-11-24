import { describe, expect, it } from 'vitest';
import type { LivePortfolioAndRuns, RecipeJobRecord } from '../types';
import { toLiveSummary } from './live-summary';

const run: RecipeJobRecord = {
    id: 'run-1',
    recipe_id: 'r1',
    mode: 'live_turn',
    status: 'completed',
    progress_pct: 100,
    result_json: null,
    error_message: null,
    created_at: '2026-11-24T19:00:00Z',
    completed_at: '2026-11-24T19:00:51Z',
};

const fetchedAt = '2026-11-24T19:01:00Z';

function snapshot(overrides: Partial<LivePortfolioAndRuns> = {}): LivePortfolioAndRuns {
    return {
        portfolio: {
            cash: 4120.25,
            total_equity: 10412.5,
            open_positions: [],
            trades: [{ ticker: 'SPY' } as never],
            equity_curve: [{ time: fetchedAt, equity: 10_000 }],
        },
        recentLiveRuns: [run, { ...run, id: 'run-0' }],
        liveMeta: {
            recipeName: 'Congress Trade Tracker',
            isLive: true,
            isOwner: true,
            turboExpiresAt: null,
            turboUsedToday: false,
        },
        ...overrides,
    } as LivePortfolioAndRuns;
}

describe('toLiveSummary', () => {
    it('keeps an unread payload unknown instead of inventing zeros', () => {
        expect(toLiveSummary(null, fetchedAt)).toBeNull();
    });

    it('carries only the facts the block renders', () => {
        const summary = toLiveSummary(snapshot(), fetchedAt);

        expect(summary).toEqual({
            totalEquity: 10412.5,
            cash: 4120.25,
            isLive: true,
            isOwner: true,
            turboExpiresAt: null,
            lastRun: run,
            fetchedAt,
        });
        // The ledger, the equity curve and the older runs stay out of the payload.
        expect(summary).not.toHaveProperty('portfolio');
        expect(summary).not.toHaveProperty('recentLiveRuns');
    });

    it('turns a non-finite ledger into unknown rather than a number', () => {
        const summary = toLiveSummary(
            {
                ...snapshot(),
                portfolio: {
                    cash: Number.NaN,
                    total_equity: Number.POSITIVE_INFINITY,
                    open_positions: [],
                    trades: [],
                },
            },
            fetchedAt,
        );

        expect(summary?.totalEquity).toBeNull();
        expect(summary?.cash).toBeNull();
    });

    it('treats a payload without liveMeta as not owned', () => {
        const summary = toLiveSummary({ ...snapshot(), liveMeta: undefined }, fetchedAt);

        expect(summary?.isOwner).toBe(false);
        expect(summary?.isLive).toBe(false);
    });
});
