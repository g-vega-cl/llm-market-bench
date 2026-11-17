import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { StudioActionBar } from './StudioActionBar';

function renderBar(overrides: Partial<Parameters<typeof StudioActionBar>[0]> = {}) {
    const handlers = {
        onOpenWaitlist: vi.fn(),
        onOpenAlerts: vi.fn(),
        onToggleScheduledLive: vi.fn(),
        onRunLive: vi.fn(),
        onBacktest: vi.fn(),
    };
    render(
        <StudioActionBar
            isBusy={false}
            isTogglingLive={false}
            isCurrentlyScheduledLive={false}
            isRunningLiveTurn={false}
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
        fireEvent.click(screen.getByRole('button', { name: 'Schedule Live (3x/d)' }));
        fireEvent.click(screen.getByRole('button', { name: '▶ Run Live' }));
        fireEvent.click(screen.getByRole('button', { name: '▶ Backtest (Random 2W)' }));

        expect(handlers.onOpenWaitlist).toHaveBeenCalledTimes(1);
        expect(handlers.onOpenAlerts).toHaveBeenCalledTimes(1);
        expect(handlers.onToggleScheduledLive).toHaveBeenCalledTimes(1);
        expect(handlers.onRunLive).toHaveBeenCalledTimes(1);
        expect(handlers.onBacktest).toHaveBeenCalledTimes(1);
    });

    it('reflects the scheduled-live and running states', () => {
        renderBar({
            isCurrentlyScheduledLive: true,
            isRunningLiveTurn: true,
            isRunningBacktest: true,
            backtestButtonLabel: 'Starting Backtest...',
        });

        expect(screen.getByRole('button', { name: /Scheduled Live: ON/ })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Running Live...' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Starting Backtest/ })).toBeInTheDocument();
    });

    it('disables the run actions while another request is in flight', () => {
        renderBar({ isBusy: true });

        expect(screen.getByRole('button', { name: 'Schedule Live (3x/d)' })).toBeDisabled();
        expect(screen.getByRole('button', { name: '▶ Run Live' })).toBeDisabled();
        expect(screen.getByRole('button', { name: '▶ Backtest (Random 2W)' })).toBeDisabled();
        expect(screen.getByRole('button', { name: '★ Waitlist' })).toBeEnabled();
    });
});
