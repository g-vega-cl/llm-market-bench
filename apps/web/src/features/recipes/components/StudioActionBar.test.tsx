import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { StudioActionBar } from './StudioActionBar';

vi.mock('@tanstack/react-router', () => ({
    Link: ({
        children,
        to,
        params,
        className,
    }: {
        children: React.ReactNode;
        to: string;
        params?: Record<string, string>;
        className?: string;
    }) => {
        let href = to;
        if (params) {
            for (const [k, v] of Object.entries(params)) {
                href = href.replace(`$${k}`, v);
            }
        }
        return (
            <a href={href} className={className}>
                {children}
            </a>
        );
    },
}));

function renderBar(overrides: Partial<Parameters<typeof StudioActionBar>[0]> = {}) {
    const handlers = {
        onOpenWaitlist: vi.fn(),
        onOpenAlerts: vi.fn(),
        onToggleScheduledLive: vi.fn(),
        onBacktest: vi.fn(),
    };
    render(
        <StudioActionBar
            isTogglingLive={false}
            isCurrentlyScheduledLive={false}
            isRunningBacktest={false}
            backtestButtonLabel="▶ Backtest (Random 2W)"
            unreadAlerts={2}
            {...handlers}
            {...overrides}
        />,
    );
    return handlers;
}

describe('StudioActionBar', () => {
    afterEach(() => {
        vi.useRealTimers();
    });

    it('wires every action to its handler', () => {
        const handlers = renderBar();

        fireEvent.click(screen.getByRole('button', { name: '★ Waitlist' }));
        fireEvent.click(screen.getByRole('button', { name: 'Alerts (2)' }));
        fireEvent.click(screen.getByRole('button', { name: 'Enable Live (30m)' }));
        fireEvent.click(screen.getByRole('button', { name: '▶ Backtest (Random 2W)' }));

        expect(handlers.onOpenWaitlist).toHaveBeenCalledTimes(1);
        expect(handlers.onOpenAlerts).toHaveBeenCalledTimes(1);
        expect(handlers.onToggleScheduledLive).toHaveBeenCalledTimes(1);
        expect(handlers.onBacktest).toHaveBeenCalledTimes(1);
    });

    it('reflects the live-on state, links to live status, and wires Turbo during market hours', () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2026-11-18T11:00:00-05:00'));
        const onActivateTurbo = vi.fn();

        renderBar({
            isCurrentlyScheduledLive: true,
            liveRecipeId: 'rec-live-1',
            onActivateTurbo,
        });

        expect(screen.getByRole('button', { name: 'Live: ON (30m)' })).toBeInTheDocument();
        expect(screen.getByRole('link', { name: /Live Runs/i })).toHaveAttribute(
            'href',
            '/recipes/live/rec-live-1/runs',
        );
        fireEvent.click(screen.getByRole('button', { name: /Turbo \(5m x 1h\)/i }));
        expect(onActivateTurbo).toHaveBeenCalledTimes(1);
    });

    it('shows loading state on the live toggle button', () => {
        renderBar({
            isTogglingLive: true,
        });

        const btn = screen.getByRole('button', { name: 'Enable Live (30m)' });
        expect(btn).toBeDisabled();
        expect(btn).toHaveAttribute('aria-busy', 'true');
    });

    it('shows loading state on the backtest button', () => {
        renderBar({
            isRunningBacktest: true,
            backtestButtonLabel: 'Starting Backtest...',
        });

        const btn = screen.getByRole('button', { name: 'Starting Backtest...' });
        expect(btn).toBeDisabled();
        expect(btn).toHaveAttribute('aria-busy', 'true');
    });

    it('disables the live toggle while backtest is running', () => {
        renderBar({
            isRunningBacktest: true,
        });

        expect(screen.getByRole('button', { name: 'Enable Live (30m)' })).toBeDisabled();
        expect(screen.getByRole('button', { name: '★ Waitlist' })).toBeEnabled();
    });

    it('does not render a Run Live button', () => {
        renderBar();
        expect(screen.queryByRole('button', { name: /Run Live/i })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /Running Live/i })).not.toBeInTheDocument();
    });
});
