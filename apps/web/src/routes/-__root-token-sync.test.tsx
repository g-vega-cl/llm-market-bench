import {
    createMemoryHistory,
    createRootRoute,
    createRouter,
    RouterProvider,
} from '@tanstack/react-router';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PostHogAuthSync, Route } from './__root';

vi.mock('@posthog/react', () => ({
    PostHogProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    usePostHog: () => null,
}));

const mockEnsureWeeklyTokens = vi.fn();
vi.mock('~/features/recipes/api/token-ledger', () => ({
    ensureWeeklyTokensFn: (...args: never[]) => mockEnsureWeeklyTokens(...args),
}));

/**
 * The refill is a load-time side effect, so it is pinned to the one behaviour
 * that costs real money: a stale screen in a tab that never reloads.
 */
describe('weekly token refill', () => {
    const installSync = async (userId: string) => {
        vi.spyOn(Route, 'useRouteContext').mockReturnValue({ user: null });
        const testRoute = createRootRoute({
            component: () => (
                <>
                    <PostHogAuthSync user={{ id: userId, email: `${userId}@example.com` }} />
                    <div>Sync ready</div>
                </>
            ),
        });
        const router = createRouter({
            routeTree: testRoute,
            history: createMemoryHistory({ initialEntries: ['/'] }),
        });
        const invalidate = vi.spyOn(router, 'invalidate').mockResolvedValue(undefined);
        render(<RouterProvider router={router} />);
        await screen.findByText('Sync ready');
        return invalidate;
    };

    beforeEach(() => {
        mockEnsureWeeklyTokens.mockReset();
        window.sessionStorage.clear();
    });

    it('does not refetch the UI when the week was already granted', async () => {
        mockEnsureWeeklyTokens.mockResolvedValue({ balance: 12, applied: false });
        const invalidate = await installSync('usr-sync');

        await waitFor(() => expect(mockEnsureWeeklyTokens).toHaveBeenCalledTimes(1));
        expect(invalidate).not.toHaveBeenCalled();
    });

    it('refetches when a grant lands, so an open tab stops showing the old balance', async () => {
        mockEnsureWeeklyTokens
            .mockResolvedValueOnce({ balance: 0, applied: false })
            .mockResolvedValueOnce({ balance: 15, applied: true });
        const invalidate = await installSync('usr-sync');

        await waitFor(() => expect(mockEnsureWeeklyTokens).toHaveBeenCalledTimes(1));
        expect(invalidate).not.toHaveBeenCalled();

        // Same tab, new day: focus must re-sync instead of trusting the old key.
        window.sessionStorage.clear();
        fireEvent(window, new Event('focus'));

        await waitFor(() => expect(invalidate).toHaveBeenCalledTimes(1));
    });

    it('stays quiet when the refill call fails', async () => {
        const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
        mockEnsureWeeklyTokens.mockRejectedValue(new Error('db down'));
        const invalidate = await installSync('usr-sync');

        await waitFor(() => expect(mockEnsureWeeklyTokens).toHaveBeenCalledTimes(1));
        expect(invalidate).not.toHaveBeenCalled();
        consoleError.mockRestore();
    });
});
