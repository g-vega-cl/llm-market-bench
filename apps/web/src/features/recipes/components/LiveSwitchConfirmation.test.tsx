import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { LiveSwitchConfirmation } from './LiveSwitchConfirmation';

function renderConfirmation(overrides: Partial<Parameters<typeof LiveSwitchConfirmation>[0]> = {}) {
    const handlers = {
        onConfirm: vi.fn(),
        onCancel: vi.fn(),
    };
    render(
        <LiveSwitchConfirmation
            conflictingRecipe={{
                id: 'rec-1',
                name: 'Trump & Chips',
                cadence: '3h',
                is_live: true,
                trial_count: 0,
                updated_at: '',
            }}
            targetRecipeName="Quality Value"
            isSwitching={false}
            {...handlers}
            {...overrides}
        />,
    );
    return handlers;
}

describe('LiveSwitchConfirmation', () => {
    it('renders the conflict message with both recipe names', () => {
        renderConfirmation();

        // "Trump & Chips" appears both in the message and in the cancel button text
        expect(screen.getAllByText(/Trump & Chips/i).length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText(/Quality Value/i)).toBeInTheDocument();
        expect(screen.getByText(/is currently live/i)).toBeInTheDocument();
        expect(screen.getByText(/instead\?/i)).toBeInTheDocument();
    });

    it('wires confirm and cancel handlers', () => {
        const handlers = renderConfirmation();

        fireEvent.click(screen.getByRole('button', { name: 'Switch to This' }));
        fireEvent.click(screen.getByRole('button', { name: 'Keep Trump & Chips' }));

        expect(handlers.onConfirm).toHaveBeenCalledTimes(1);
        expect(handlers.onCancel).toHaveBeenCalledTimes(1);
    });

    it('disables buttons while switching', () => {
        renderConfirmation({ isSwitching: true });

        expect(screen.getByRole('button', { name: 'Switch to This' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Keep Trump & Chips' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Switch to This' })).toHaveAttribute(
            'aria-busy',
            'true',
        );
    });

    it('has role alert for accessibility', () => {
        renderConfirmation();
        const trough = screen.getByRole('alert');
        expect(trough).toBeInTheDocument();
    });
});
