import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { RecipeJobRecord } from '../types';
import {
    BuilderBotLiveStatus,
    describeLastTurn,
    describeLedger,
    describeNextRun,
    resolveLiveState,
} from './BuilderBotLiveStatus';
import type { RecipeLiveSummary } from './live-summary';

vi.mock('@tanstack/react-router', () => ({
    Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
        <a href={to}>{children}</a>
    ),
}));

const liveTurn: RecipeJobRecord = {
    id: 'live-run-1',
    recipe_id: 'live-123',
    mode: 'live_turn',
    status: 'completed',
    progress_pct: 100,
    result_json: null,
    error_message: null,
    created_at: '2026-11-24T19:00:00Z',
    completed_at: '2026-11-24T19:00:51Z',
};

describe('resolveLiveState', () => {
    it('separates paused, scheduled and turbo states', () => {
        expect(resolveLiveState(false)).toMatchObject({ label: 'PAUSED', isLive: false });
        expect(resolveLiveState(true)).toMatchObject({ label: 'LIVE ON (30m)', isLive: true });
        expect(resolveLiveState(null)).toMatchObject({
            label: 'SCHEDULE UNKNOWN',
            isLive: null,
        });
    });
});

describe('describeNextRun', () => {
    it('never claims a next run while paused', () => {
        expect(describeNextRun(false, null, new Date('2026-11-24T19:00:00Z'))).toBe(
            'Next run Paused',
        );
    });

    it('prefers the turbo window over the slot label', () => {
        expect(describeNextRun(true, '3m left', new Date('2026-11-24T19:00:00Z'))).toBe(
            'Next run within 5m (Turbo) · 3m left',
        );
    });

    it('names the next ET slot from the timestamp it is given', () => {
        // 14:29 ET — the 14:30 slot is still ahead.
        expect(describeNextRun(true, null, new Date('2026-11-24T19:29:00Z'))).toBe(
            'Next run 14:30 ET today',
        );
        // 14:31 ET — that slot has passed, so 15:00 is next.
        expect(describeNextRun(true, null, new Date('2026-11-24T19:31:00Z'))).toBe(
            'Next run 15:00 ET today',
        );
    });
});

describe('describeLastTurn', () => {
    it('does not turn an unread snapshot into "never traded"', () => {
        expect(describeLastTurn(null, false)).toEqual({
            text: 'Live history not loaded',
            tone: 'muted',
        });
    });

    it('reports an empty history only when the read succeeded', () => {
        expect(describeLastTurn(null, true).text).toBe('No live turns yet');
    });

    it('maps every run status to a tone', () => {
        expect(describeLastTurn(liveTurn)).toMatchObject({ tone: 'success' });
        expect(describeLastTurn({ ...liveTurn, status: 'failed' })).toMatchObject({
            tone: 'danger',
        });
        expect(describeLastTurn({ ...liveTurn, status: 'processing' })).toMatchObject({
            text: expect.stringContaining('running'),
        });
        expect(describeLastTurn({ ...liveTurn, status: 'pending' })).toMatchObject({
            text: expect.stringContaining('queued'),
        });
        expect(describeLastTurn({ ...liveTurn, status: 'cancelled' })).toMatchObject({
            text: expect.stringContaining('cancelled'),
        });
    });

    it('carries the provider reason on a failure and trims a long one', () => {
        expect(
            describeLastTurn({
                ...liveTurn,
                status: 'failed',
                error_message: 'Request timed out.',
            }),
        ).toMatchObject({ text: expect.stringContaining('— Request timed out.') });

        const long = describeLastTurn({
            ...liveTurn,
            status: 'failed',
            error_message: 'x'.repeat(200),
        });
        expect(long.text).toContain('…');
        expect(long.text.length).toBeLessThan(200);
    });
});

describe('describeLedger', () => {
    it('keeps cents so a sub-dollar move is not rounded into a different number', () => {
        expect(describeLedger(10_000.4, 4_120.05)).toBe('Equity $10,000.40 · Cash $4,120.05');
    });

    it('renders equity alone when cash is missing', () => {
        expect(describeLedger(9_980, null)).toBe('Equity $9,980.00');
    });

    it('renders nothing for an unknown or non-finite ledger', () => {
        expect(describeLedger(null, null)).toBeNull();
        expect(describeLedger(Number.NaN, 1)).toBeNull();
    });
});

describe('BuilderBotLiveStatus clock', () => {
    beforeEach(() => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2026-11-24T19:29:00Z'));
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('moves the next-run label to the following slot as the clock ticks', () => {
        render(<BuilderBotLiveStatus recipeId="live-123" isScheduledLive summary={null} />);

        expect(screen.getByTestId('bot-live-status')).toHaveTextContent(/14:30 ET today/);

        act(() => {
            vi.advanceTimersByTime(120_000);
        });

        expect(screen.getByTestId('bot-live-status')).toHaveTextContent(/15:00 ET today/);
    });

    it('announces only the state badge, not the ticking clock', () => {
        render(<BuilderBotLiveStatus recipeId="live-123" isScheduledLive summary={null} />);

        const regions = screen.getAllByRole('status');
        expect(regions).toHaveLength(1);
        expect(regions[0]).toHaveTextContent('LIVE ON (30m)');
        expect(regions[0]).not.toHaveTextContent(/Next run/);
    });

    it('keeps the turbo countdown out of the announced region', () => {
        const turboExpiresAt = new Date(Date.now() + 3 * 60_000).toISOString();
        render(
            <BuilderBotLiveStatus
                recipeId="live-123"
                isScheduledLive
                turboExpiresAt={turboExpiresAt}
                summary={null}
            />,
        );

        const region = screen.getByRole('status');
        expect(region).toHaveTextContent('LIVE ON (30m)');
        expect(region).not.toHaveTextContent(/left/);
        expect(screen.getByTestId('bot-live-status')).toHaveTextContent(/3m left/);
    });

    it('reports an empty history when the summary was read without runs', () => {
        const empty: RecipeLiveSummary = {
            totalEquity: 1000,
            cash: 1000,
            isLive: true,
            isOwner: true,
            turboExpiresAt: null,
            lastRun: null,
            fetchedAt: '2026-11-24T19:01:00Z',
        };
        render(<BuilderBotLiveStatus recipeId="live-123" isScheduledLive summary={empty} />);

        const banner = screen.getByTestId('bot-live-status');
        expect(banner).toHaveTextContent(/No live turns yet/i);
        expect(banner).not.toHaveTextContent(/Live history not loaded/i);
    });
});
