import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { calculateBenchmarkMoves, Route, RouteComponent } from './index';

const mockInvalidate = vi.fn();
const mockReloadFeatureFlags = vi.fn();
const mockCapture = vi.fn();

vi.mock('@tanstack/react-router', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@tanstack/react-router')>();
    return {
        ...actual,
        useRouter: () => ({
            invalidate: mockInvalidate,
        }),
    };
});

vi.mock('@posthog/react', () => ({
    usePostHog: () => ({
        reloadFeatureFlags: mockReloadFeatureFlags,
        capture: mockCapture,
    }),
}));

vi.mock('~/features/home/pages/HomePage', () => ({
    HomePage: ({ data }: { data: { currentUser?: { email?: string } | null } }) => (
        <div data-testid="mock-home-page">
            Homepage Content - User: {data.currentUser?.email ?? 'anonymous'}
        </div>
    ),
}));

describe('Homepage Route Component (routes/index)', () => {
    beforeEach(() => {
        vi.useFakeTimers();
        mockInvalidate.mockClear();
        mockReloadFeatureFlags.mockClear();
        mockCapture.mockClear();

        Object.defineProperty(document, 'hidden', {
            configurable: true,
            value: false,
        });

        // Mock Route.useLoaderData and Route.useRouteContext
        vi.spyOn(Route, 'useLoaderData').mockReturnValue({
            portfolios: [],
            benchmark: { todayPct: 0, weekPct: 0 },
            bars: [],
            agentState: undefined,
            isMarketOpen: true,
            feeling: undefined,
            barometer: null,
        } as ReturnType<typeof Route.useLoaderData>);

        vi.spyOn(Route, 'useRouteContext').mockReturnValue({
            user: { id: 'usr-123', email: 'trader@example.com' },
        } as ReturnType<typeof Route.useRouteContext>);
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.useRealTimers();
    });

    it('renders HomePage with loader data and context', () => {
        render(<RouteComponent />);
        expect(screen.getByTestId('mock-home-page')).toBeInTheDocument();
        expect(screen.getByText(/User: trader@example\.com/)).toBeInTheDocument();
    });

    it('invalidates router and syncs posthog on window focus after cooldown', () => {
        render(<RouteComponent />);

        // Advance timers past initial 5000ms throttle cooldown
        vi.advanceTimersByTime(5001);

        act(() => {
            window.dispatchEvent(new Event('focus'));
        });

        expect(mockInvalidate).toHaveBeenCalledTimes(1);
        expect(mockReloadFeatureFlags).toHaveBeenCalledTimes(1);
        expect(mockCapture).toHaveBeenCalledWith('window_focus_refreshed', { path: '/' });
    });

    it('invalidates router when tab becomes visible after visibilitychange', () => {
        render(<RouteComponent />);

        vi.advanceTimersByTime(5001);

        act(() => {
            document.dispatchEvent(new Event('visibilitychange'));
        });

        expect(mockInvalidate).toHaveBeenCalledTimes(1);
        expect(mockReloadFeatureFlags).toHaveBeenCalledTimes(1);
        expect(mockCapture).toHaveBeenCalledWith('window_focus_refreshed', { path: '/' });
    });
});

describe('calculateBenchmarkMoves', () => {
    const historicalData = [
        { date: '2026-11-03', price: 754.35 },
        { date: '2026-11-04', price: 766.81 },
        { date: '2026-11-05', price: 733.0 },
        { date: '2026-11-06', price: 735.29 },
        { date: '2026-11-09', price: 752.69 },
    ];

    it('calculates moves purely from history when no live quote provided', () => {
        const moves = calculateBenchmarkMoves(historicalData);
        // Nov 9 ($752.69) vs Nov 6 ($735.29): +2.37%
        expect(moves.todayPct).toBe(2.37);
        // Nov 9 ($752.69) vs Nov 3 ($754.35): -0.22%
        expect(moves.weekPct).toBe(-0.22);
    });

    it('incorporates today live intraday quote vs yesterday EOD close (reproduction test)', () => {
        // Today is Nov 10, intraday price is $747.08
        // (747.08 - 752.69) / 752.69 = -0.745% -> -0.75%
        // (747.08 - 754.35) / 754.35 = -0.963% -> -0.96%
        const liveQuote = { price: 747.08, date: '2026-11-10' };
        const moves = calculateBenchmarkMoves(historicalData, liveQuote);

        expect(moves.todayPct).toBe(-0.75);
        expect(moves.weekPct).toBe(-0.96);
    });

    it('updates same-day price when quote date matches latest benchmark date during market hours', () => {
        const dataWithToday = [...historicalData, { date: '2026-11-10', price: 750.0 }];
        // During market hours (isMarketOpen: true), live quote should update same-day bar
        const liveQuote = { price: 747.08, date: '2026-11-10' };
        const moves = calculateBenchmarkMoves(dataWithToday, liveQuote, true);

        expect(moves.todayPct).toBe(-0.75);
        expect(moves.weekPct).toBe(-0.96);
    });

    it('preserves official EOD close when market is closed (does not overwrite with stale tick)', () => {
        const officialClose = 750.0;
        const dataWithEOD = [...historicalData, { date: '2026-11-10', price: officialClose }];
        // When market is closed (isMarketOpen: false), official EOD close takes precedence
        const staleBar = { price: 747.08, date: '2026-11-10' };
        const moves = calculateBenchmarkMoves(dataWithEOD, staleBar, false);

        // (750.00 - 752.69) / 752.69 = -0.357% -> -0.36%
        expect(moves.todayPct).toBe(-0.36);
    });

    it('ignores stale quote with date earlier than latest benchmark history', () => {
        const staleQuote = { price: 700.0, date: '2026-11-05' };
        const moves = calculateBenchmarkMoves(historicalData, staleQuote);

        expect(moves.todayPct).toBe(2.37);
        expect(moves.weekPct).toBe(-0.22);
    });

    it('handles empty or insufficient data gracefully', () => {
        expect(calculateBenchmarkMoves([])).toEqual({ todayPct: 0, weekPct: 0 });
        expect(calculateBenchmarkMoves([{ date: '2026-11-10', price: 747.08 }])).toEqual({
            todayPct: 0,
            weekPct: 0,
        });
    });
});
