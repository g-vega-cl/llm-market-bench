import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, RouteComponent } from './index';

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
