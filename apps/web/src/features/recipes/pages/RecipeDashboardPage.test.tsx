import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { RecipeSummaryItem } from '../types';
import { RecipeDashboardPage } from './RecipeDashboardPage';

const routerState = vi.hoisted(() => ({
    status: 'idle' as 'idle' | 'pending',
    location: { pathname: '/recipes', search: {} as Record<string, unknown> },
}));

vi.mock('@tanstack/react-router', () => ({
    useRouterState: ({ select }: { select: (state: unknown) => unknown }) =>
        select({ status: routerState.status, location: routerState.location }),
    useRouter: () => ({ state: { status: routerState.status } }),
    Link: ({
        children,
        to,
        params,
        search,
        className,
        disabled,
        ...rest
    }: {
        children: React.ReactNode;
        to: string;
        params?: Record<string, string>;
        search?: Record<string, string>;
        className?: string;
        disabled?: boolean;
    } & Record<string, unknown>) => {
        let href = to;
        if (params) {
            for (const [key, val] of Object.entries(params)) {
                href = href.replace(`$${key}`, val);
            }
        }
        if (search?.recipeId) {
            href = `${href}?recipeId=${search.recipeId}`;
        }
        return (
            <a
                href={disabled ? undefined : href}
                aria-disabled={disabled || undefined}
                className={className}
                {...rest}
            >
                {children}
            </a>
        );
    },
}));

vi.mock('../api/archive-recipe', () => ({
    archiveRecipeFn: vi.fn(),
}));

vi.mock('../api/recipes-quota-api', () => ({
    fetchRecipeQuotaStatusFn: vi.fn(),
    toggleLiveScheduleFn: vi.fn(),
    switchLiveScheduleFn: vi.fn(),
}));

vi.mock('../api/recipes-studio-api', () => ({
    fetchRecipeAlertsFn: vi.fn(),
    markAlertReadFn: vi.fn(),
    submitWaitlistPledgeFn: vi.fn(),
}));

import { archiveRecipeFn } from '../api/archive-recipe';
import { toggleLiveScheduleFn } from '../api/recipes-quota-api';

const sampleBots: RecipeSummaryItem[] = [
    {
        id: 'bot-1',
        name: 'AI Capex Momentum',
        cadence: '3h',
        is_live: true,
        is_public: true,
        trial_count: 2,
        updated_at: '2026-11-20T10:00:00Z',
    },
    {
        id: 'bot-2',
        name: 'Value Compounder',
        cadence: '1d',
        is_live: false,
        is_public: true,
        trial_count: 0,
        updated_at: '2026-11-19T10:00:00Z',
    },
];

beforeEach(() => {
    vi.clearAllMocks();
    routerState.status = 'idle';
    routerState.location = { pathname: '/recipes', search: {} };
});

describe('RecipeDashboardPage', () => {
    it('shows a focused empty-state hero with a single Build Your First Bot CTA when user has 0 bots', () => {
        render(<RecipeDashboardPage initialUserRecipes={[]} />);

        expect(screen.getByTestId('empty-bots-hero')).toBeInTheDocument();
        expect(screen.getByRole('link', { name: /Build Your First Bot/i })).toHaveAttribute(
            'href',
            '/build',
        );
        expect(screen.queryByRole('link', { name: /\+ Build New Bot/i })).not.toBeInTheDocument();
        expect(screen.queryByText(/★ Waitlist/i)).not.toBeInTheDocument();
        expect(screen.queryByText(/How 2-Week PIT Backtests Work/i)).not.toBeInTheDocument();
    });

    it('shows minimal bot cards linking to /recipes/$recipeId and a single + Build New Bot CTA', () => {
        render(<RecipeDashboardPage initialUserRecipes={sampleBots} />);

        expect(screen.getByRole('link', { name: /\+ Build New Bot/i })).toHaveAttribute(
            'href',
            '/build',
        );
        expect(
            screen.getByRole('link', { name: /AI Capex Momentum \(open recipe workspace\)/ }),
        ).toHaveAttribute('href', '/recipes/bot-1');
        expect(
            screen.getByRole('link', { name: /Value Compounder \(open recipe workspace\)/ }),
        ).toHaveAttribute('href', '/recipes/bot-2');
        expect(screen.getByRole('link', { name: 'LIVE 30m' })).toHaveAttribute(
            'href',
            '/recipes/live/bot-1/runs',
        );
    });

    it('shows the in-flight state on the card being opened, and disables every card action', () => {
        routerState.status = 'pending';
        routerState.location = { pathname: '/recipes/bot-2', search: {} };
        render(<RecipeDashboardPage initialUserRecipes={sampleBots} />);

        expect(screen.getByTestId('bot-actions-bot-2')).toHaveAttribute('aria-busy', 'true');
        expect(screen.getByTestId('bot-open-bot-2')).toHaveAttribute('aria-disabled', 'true');
        expect(screen.getByTestId('bot-open-bot-2')).not.toHaveAttribute('href');
        expect(screen.getByText('Opening bot…')).toBeInTheDocument();

        // The other card is untouched: only the card being opened goes busy.
        expect(screen.getByTestId('bot-actions-bot-1')).not.toHaveAttribute('aria-busy');
        expect(screen.getByTestId('bot-open-bot-1')).toHaveAttribute('href', '/recipes/bot-1');

        expect(screen.getByRole('button', { name: 'Pause Live' })).toBeEnabled();
        expect(screen.getByRole('button', { name: 'Enable Live (30m)' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Remove AI Capex Momentum' })).toBeEnabled();
    });

    it('removes a bot when clicking Remove', async () => {
        vi.mocked(archiveRecipeFn).mockResolvedValue({ archived: true, id: 'bot-2' } as never);
        render(<RecipeDashboardPage initialUserRecipes={sampleBots} />);

        fireEvent.click(screen.getByRole('button', { name: 'Remove Value Compounder' }));

        await waitFor(() => {
            expect(archiveRecipeFn).toHaveBeenCalledWith({ data: { recipeId: 'bot-2' } });
            expect(screen.queryByText('Value Compounder')).not.toBeInTheDocument();
        });
    });

    it('allows enabling a 2nd live bot directly when maxLiveRecipes is 3, and confirms switch only at limit', async () => {
        vi.mocked(toggleLiveScheduleFn).mockResolvedValue({
            recipeId: 'bot-2',
            is_live: true,
        } as never);

        render(<RecipeDashboardPage initialUserRecipes={sampleBots} />);

        fireEvent.click(screen.getByRole('button', { name: 'Enable Live (30m)' }));

        await waitFor(() => {
            expect(toggleLiveScheduleFn).toHaveBeenCalledWith({
                data: { recipeId: 'bot-2', isLive: true },
            });
        });
        expect(screen.queryByText(/Live Bot Limit Reached/i)).not.toBeInTheDocument();
    });
});
