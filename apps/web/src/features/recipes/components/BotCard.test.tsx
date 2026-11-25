import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { RecipeSummaryItem } from '../types';
import { BotCard } from './BotCard';

const routerMock = vi.hoisted(() => ({
    state: { status: 'idle' as 'idle' | 'pending' },
}));

vi.mock('@tanstack/react-router', () => ({
    useRouter: () => ({ state: routerMock.state }),
    Link: ({
        children,
        to,
        params,
        search,
        disabled,
        ...rest
    }: {
        children: React.ReactNode;
        to: string;
        params?: Record<string, string>;
        search?: Record<string, string>;
        disabled?: boolean;
    } & Record<string, unknown>) => {
        let href = to;
        if (params) {
            for (const [key, value] of Object.entries(params)) {
                href = href.replace(`$${key}`, value);
            }
        }
        if (search?.recipeId) {
            href = `${href}?recipeId=${search.recipeId}`;
        }
        return (
            <a href={disabled ? undefined : href} aria-disabled={disabled || undefined} {...rest}>
                {children}
            </a>
        );
    },
}));

const liveBot: RecipeSummaryItem = {
    id: 'bot-1',
    name: 'AI Capex Momentum',
    cadence: '3h',
    is_live: true,
    is_public: true,
    trial_count: 2,
    updated_at: '2026-11-20T10:00:00Z',
};

function renderCard(overrides: Partial<Parameters<typeof BotCard>[0]> = {}) {
    const onToggleLive = vi.fn();
    const onRemove = vi.fn();
    const onToggleVisibility = vi.fn();
    render(
        <BotCard
            item={liveBot}
            pendingDestination={null}
            isLocked={false}
            isTogglingLive={false}
            isRemoving={false}
            isTogglingVisibility={false}
            onToggleLive={onToggleLive}
            onRemove={onRemove}
            onToggleVisibility={onToggleVisibility}
            {...overrides}
        />,
    );
    return { onToggleLive, onRemove, onToggleVisibility };
}

describe('BotCard', () => {
    beforeEach(() => {
        routerMock.state.status = 'idle';
    });

    it('shows a visible open affordance beside the bot name that links to the bot overview', () => {
        renderCard();

        const openLink = screen.getByTestId('bot-open-bot-1');
        expect(openLink).toHaveAttribute('href', '/recipes/bot-1');
        expect(openLink).toHaveTextContent('AI Capex Momentum');
        expect(
            screen.getByRole('link', { name: /AI Capex Momentum \(open recipe workspace\)/ }),
        ).toBe(openLink);
        expect(openLink).toHaveClass('hover:underline');
        expect(screen.getByTestId('bot-open-chevron-bot-1')).toBeInTheDocument();
    });

    it('names the workspace as the destination while that navigation is in flight', () => {
        renderCard({ pendingDestination: 'workspace' });

        expect(screen.getByTestId('bot-actions-bot-1')).toHaveAttribute('aria-busy', 'true');
        expect(screen.getByText('Opening bot…')).toBeInTheDocument();

        const openLink = screen.getByTestId('bot-open-bot-1');
        expect(openLink).not.toHaveAttribute('href');
        expect(openLink).toHaveAttribute('aria-disabled', 'true');
        expect(openLink).toHaveClass('text-voxel-muted');
        expect(screen.queryByTestId('bot-open-chevron-bot-1')).not.toBeInTheDocument();
        expect(screen.getByTestId('bot-open-pending-bot-1')).toBeInTheDocument();

        expect(screen.getByRole('button', { name: 'Pause Live' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Remove AI Capex Momentum' })).toBeDisabled();
        expect(screen.getByTestId('bot-live-bot-1')).not.toHaveAttribute('href');
    });

    it('names the live page as the destination while that navigation is in flight', () => {
        renderCard({ pendingDestination: 'live' });

        expect(screen.getByText('Opening live view…')).toBeInTheDocument();
        expect(screen.queryByText('Opening bot…')).not.toBeInTheDocument();
        expect(screen.getByTestId('bot-live-bot-1')).not.toHaveAttribute('href');
        expect(screen.getByTestId('bot-open-bot-1')).not.toHaveAttribute('href');
    });

    it('keeps the idle card interactive and idle-looking', () => {
        renderCard();

        expect(screen.getByTestId('bot-actions-bot-1')).not.toHaveAttribute('aria-busy');
        expect(screen.queryByText('Opening bot…')).not.toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Pause Live' })).toBeEnabled();
        expect(screen.getByTestId('bot-live-bot-1')).toHaveAttribute(
            'href',
            '/recipes/live/bot-1/runs',
        );
    });

    it('locks navigation and actions while a live or remove mutation is in flight', () => {
        renderCard({ isLocked: true });

        expect(screen.getByRole('button', { name: 'Pause Live' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Remove AI Capex Momentum' })).toBeDisabled();
        expect(screen.getByTestId('bot-open-bot-1')).not.toHaveAttribute('href');
        expect(screen.getByTestId('bot-live-bot-1')).not.toHaveAttribute('href');
    });

    it('does not swallow a modified click, and still allows a later plain click', () => {
        renderCard();

        const openLink = screen.getByTestId('bot-open-bot-1');
        expect(fireEvent.click(openLink, { cancelable: true, ctrlKey: true })).toBe(true);
        expect(fireEvent.click(openLink, { cancelable: true })).toBe(true);
    });

    it('blocks a second click once the router reports a pending navigation', () => {
        renderCard();

        const openLink = screen.getByTestId('bot-open-bot-1');
        expect(fireEvent.click(openLink, { cancelable: true })).toBe(true);

        // navigate() flips the router status inside the first click's stack.
        routerMock.state.status = 'pending';
        expect(fireEvent.click(openLink, { cancelable: true })).toBe(false);

        routerMock.state.status = 'idle';
        expect(fireEvent.click(openLink, { cancelable: true })).toBe(true);
    });

    it('swallows clicks on an inert link while a mutation is in flight', () => {
        renderCard({ isLocked: true });

        expect(fireEvent.click(screen.getByTestId('bot-open-bot-1'))).toBe(false);
    });

    it('routes the toggle and remove actions through the card callbacks', () => {
        const { onToggleLive, onRemove } = renderCard({ item: { ...liveBot, is_live: false } });

        fireEvent.click(screen.getByRole('button', { name: 'Enable Live (30m)' }));
        fireEvent.click(screen.getByRole('button', { name: 'Remove AI Capex Momentum' }));

        expect(onToggleLive).toHaveBeenCalledTimes(1);
        expect(onRemove).toHaveBeenCalledTimes(1);
    });

    it('shows the visibility state as a quiet control that names the setting', () => {
        const { onToggleVisibility } = renderCard();

        const control = screen.getByRole('button', {
            name: 'Bot visibility for AI Capex Momentum',
        });
        expect(control).toHaveTextContent('Public');
        // The accessible name stays stable; the state lives in aria-pressed, so a
        // screen reader never hears "make private, pressed" on a public bot.
        expect(control).toHaveAttribute('aria-pressed', 'true');

        fireEvent.click(control);
        expect(onToggleVisibility).toHaveBeenCalledTimes(1);
    });

    it('reads Private for a hidden bot with the same accessible name', () => {
        renderCard({ item: { ...liveBot, is_public: false } });

        const control = screen.getByRole('button', {
            name: 'Bot visibility for AI Capex Momentum',
        });
        expect(control).toHaveTextContent('Private');
        expect(control).toHaveAttribute('aria-pressed', 'false');
    });

    it('locks the visibility control while its own mutation is in flight', () => {
        renderCard({ isTogglingVisibility: true });

        expect(
            screen.getByRole('button', { name: 'Bot visibility for AI Capex Momentum' }),
        ).toBeDisabled();
    });
});
