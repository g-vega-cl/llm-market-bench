import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { StudioActionBar } from './StudioActionBar';

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
    it('wires every action to its handler', () => {
        const handlers = renderBar();

        fireEvent.click(screen.getByRole('button', { name: '★ Waitlist' }));
        fireEvent.click(screen.getByRole('button', { name: 'Alerts (2)' }));
        fireEvent.click(screen.getByRole('button', { name: 'Enable Live (3x/d)' }));
        fireEvent.click(screen.getByRole('button', { name: '▶ Backtest (Random 2W)' }));

        expect(handlers.onOpenWaitlist).toHaveBeenCalledTimes(1);
        expect(handlers.onOpenAlerts).toHaveBeenCalledTimes(1);
        expect(handlers.onToggleScheduledLive).toHaveBeenCalledTimes(1);
        expect(handlers.onBacktest).toHaveBeenCalledTimes(1);
    });

    it('reflects the live-on state', () => {
        renderBar({
            isCurrentlyScheduledLive: true,
        });

        expect(screen.getByRole('button', { name: 'Live: ON (3x/d)' })).toBeInTheDocument();
    });

    it('shows loading state on the live toggle button', () => {
        renderBar({
            isTogglingLive: true,
        });

        const btn = screen.getByRole('button', { name: 'Enable Live (3x/d)' });
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

        expect(screen.getByRole('button', { name: 'Enable Live (3x/d)' })).toBeDisabled();
        expect(screen.getByRole('button', { name: '★ Waitlist' })).toBeEnabled();
    });

    it('does not render a Run Live button', () => {
        renderBar();
        expect(screen.queryByRole('button', { name: /Run Live/i })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /Running Live/i })).not.toBeInTheDocument();
    });
});
