import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { GuestRunPanel } from './GuestRunPanel';

const startGuestBacktestFn = vi.fn();
const fetchGuestJobFn = vi.fn();
const fetchGuestBalanceFn = vi.fn();

vi.mock('../api/recipes-api', () => ({
    startGuestBacktestFn: (...args: unknown[]) => startGuestBacktestFn(...args),
    fetchGuestJobFn: (...args: unknown[]) => fetchGuestJobFn(...args),
    fetchGuestBalanceFn: (...args: unknown[]) => fetchGuestBalanceFn(...args),
}));

vi.mock('@tanstack/react-router', () => ({
    Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
        <a href={to}>{children}</a>
    ),
}));

beforeEach(() => {
    startGuestBacktestFn.mockReset();
    fetchGuestJobFn.mockReset();
    fetchGuestBalanceFn.mockReset();
    // A first-time visitor: five owed, nothing spent yet.
    fetchGuestBalanceFn.mockResolvedValue({ balance: 5, grant: 5 });
});

describe('GuestRunPanel', () => {
    it('states the price before the click', () => {
        render(<GuestRunPanel recipeId="rec-1" />);
        expect(screen.getByText('Run this one (1 token)')).toBeTruthy();
        expect(screen.getByRole('status').textContent).toContain('One token buys one backtest');
    });

    it('shows the refusal message when the guest has no tokens left', async () => {
        startGuestBacktestFn.mockRejectedValue(
            new Error('You are out of guest tokens. Sign up for 15 a week.'),
        );
        render(<GuestRunPanel recipeId="rec-1" />);

        fireEvent.click(screen.getByText('Run this one (1 token)'));

        await waitFor(() => {
            expect(screen.getByRole('status').textContent).toContain(
                'You are out of guest tokens. Sign up for 15 a week.',
            );
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

describe('GuestRunPanel balance', () => {
    it('replaces the grant with what is actually left', async () => {
        fetchGuestBalanceFn.mockResolvedValue({ balance: 4, grant: 5 });
        render(<GuestRunPanel recipeId="rec-1" />);

        await waitFor(() => {
            expect(screen.getByText('4 OF 5 LEFT')).toBeTruthy();
        });
        expect(screen.queryByText('5 FREE TOKENS')).toBeNull();
    });

    it('disables the run and points at signup once the balance is zero', async () => {
        fetchGuestBalanceFn.mockResolvedValue({ balance: 0, grant: 5 });
        render(<GuestRunPanel recipeId="rec-1" />);

        const button = await screen.findByText('Out of tokens');
        expect((button as HTMLButtonElement).disabled).toBe(true);
        expect(screen.getByRole('status').textContent).toContain('Sign in for 15 a week');
        expect(screen.queryByText('Run this one (1 token)')).toBeNull();
    });

    it('re-reads the balance after a run finishes, so the count is not stale', async () => {
        // Mount reads 5; the post-run read must not stay stuck on it.
        fetchGuestBalanceFn
            .mockResolvedValueOnce({ balance: 5, grant: 5 })
            .mockResolvedValue({ balance: 4, grant: 5 });
        startGuestBacktestFn.mockResolvedValue({ id: 'job-1' });
        fetchGuestJobFn.mockResolvedValueOnce({
            id: 'job-1',
            recipe_id: 'rec-1',
            status: 'completed',
            progress_pct: 100,
            error_message: null,
        });

        render(<GuestRunPanel recipeId="rec-1" pollMs={5} />);
        fireEvent.click(await screen.findByText('Run this one (1 token)'));

        await waitFor(() => {
            expect(screen.getByText('Open the result →')).toBeTruthy();
        });
        await waitFor(() => {
            expect(screen.getByText('4 OF 5 LEFT')).toBeTruthy();
        });
    });
});
