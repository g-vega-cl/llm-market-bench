import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { GuestRunPanel } from './GuestRunPanel';

const startGuestBacktestFn = vi.fn();
const fetchGuestJobFn = vi.fn();

vi.mock('../api/recipes-api', () => ({
    startGuestBacktestFn: (...args: unknown[]) => startGuestBacktestFn(...args),
    fetchGuestJobFn: (...args: unknown[]) => fetchGuestJobFn(...args),
}));

vi.mock('@tanstack/react-router', () => ({
    Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
        <a href={to}>{children}</a>
    ),
}));

beforeEach(() => {
    startGuestBacktestFn.mockReset();
    fetchGuestJobFn.mockReset();
});

describe('GuestRunPanel', () => {
    it('states the price before the click', () => {
        render(<GuestRunPanel recipeId="rec-1" />);
        expect(screen.getByText('Run this one (1 token)')).toBeTruthy();
        expect(screen.getByRole('status').textContent).toContain('One token buys one backtest');
    });

    it('shows the refusal message when the guest has no tokens left', async () => {
        startGuestBacktestFn.mockRejectedValue(
            new Error('You are out of tokens. Sign up to get 15 every week.'),
        );
        render(<GuestRunPanel recipeId="rec-1" />);

        fireEvent.click(screen.getByText('Run this one (1 token)'));

        await waitFor(() => {
            expect(screen.getByRole('status').textContent).toContain('You are out of tokens');
        });
        // A refusal must not leave the button spinning.
        expect(screen.getByText('Run this one (1 token)')).toBeTruthy();
    });

    it('queues, reports progress and links to the result', async () => {
        startGuestBacktestFn.mockResolvedValue({ id: 'job-1' });
        fetchGuestJobFn.mockResolvedValueOnce({
            id: 'job-1',
            recipe_id: 'rec-1',
            status: 'processing',
            progress_pct: 40,
            error_message: null,
        });
        render(<GuestRunPanel recipeId="rec-1" pollMs={5} />);

        fireEvent.click(screen.getByText('Run this one (1 token)'));

        await waitFor(() => {
            expect(screen.getByRole('status').textContent).toContain('Running: 40%');
        });

        fetchGuestJobFn.mockResolvedValueOnce({
            id: 'job-1',
            recipe_id: 'rec-1',
            status: 'completed',
            progress_pct: 100,
            error_message: null,
        });

        await waitFor(() => {
            expect(screen.getByRole('status').textContent).toContain('Finished');
        });
        expect(screen.getByText('Open the result →')).toBeTruthy();
    });
});
