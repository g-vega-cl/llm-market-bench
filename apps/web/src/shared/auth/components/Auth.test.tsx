import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Auth } from './Auth';

const mockSignInWithOAuth = vi.hoisted(() => vi.fn());
const mockGetAuthBrowserClient = vi.hoisted(() =>
    vi.fn(() => ({
        auth: {
            signInWithOAuth: mockSignInWithOAuth,
        },
    })),
);

vi.mock('~/lib/auth-client', () => ({
    getAuthBrowserClient: mockGetAuthBrowserClient,
}));

describe('Auth — layout and disclaimers', () => {
    it('renders in-flow inside a voxel Card without a fixed modal scrim', () => {
        const { container } = render(<Auth redirectPath="/portfolios" />);
        const outer = container.firstElementChild as HTMLElement;

        expect(outer.className).not.toContain('fixed');
        expect(outer.className).not.toContain('bg-black/80');
        expect(outer.querySelector('.voxel-card')).toBeInTheDocument();
        expect(screen.getByText('Research & paper trading only')).toBeInTheDocument();
        expect(
            screen.getByText(
                /paper trading only\. not financial advice\. no returns guaranteed\./i,
            ),
        ).toBeInTheDocument();
        expect(screen.getByRole('link', { name: /public sample backtest/i })).toHaveAttribute(
            'href',
            '/recipes-demo',
        );
    });
});

describe('Auth — recipe beta panel', () => {
    const panelProps = {
        actionText: 'Sign in to Benchify',
    };

    it('shows the Recipe Studio beta panel when the redirect target is /recipes', () => {
        render(<Auth {...panelProps} redirectPath="/recipes?recipeId=rec-1" />);

        expect(screen.getByText('Strategy Recipe Studio — Free Beta Access')).toBeInTheDocument();
        expect(screen.getByText(/2 free 2-week backtests\/day/i)).toBeInTheDocument();
        expect(screen.getByRole('link', { name: /public sample backtest/i })).toHaveAttribute(
            'href',
            '/recipes-demo',
        );
    });

    it('hides the panel for /recipes-demo and unrelated redirect targets', () => {
        const { rerender } = render(<Auth {...panelProps} redirectPath="/recipes-demo" />);
        expect(
            screen.queryByText('Strategy Recipe Studio — Free Beta Access'),
        ).not.toBeInTheDocument();

        rerender(<Auth {...panelProps} redirectPath="/portfolios" />);
        expect(
            screen.queryByText('Strategy Recipe Studio — Free Beta Access'),
        ).not.toBeInTheDocument();
    });
});

describe('Auth — uses design system', () => {
    const defaultProps = {
        actionText: 'Sign in to Benchify',
    };

    it('renders buttons using DS Button component', () => {
        render(<Auth {...defaultProps} />);

        const buttons = screen.getAllByRole('button');
        expect(buttons.length).toBeGreaterThanOrEqual(1);

        for (const btn of buttons) {
            expect(btn.className).toContain('inline-flex');
            expect(btn.className).toContain('font-bold');
        }
    });

    it('renders a Google sign-in button using DS Button component', () => {
        render(<Auth {...defaultProps} />);

        const button = screen.getByRole('button', { name: /continue with google/i });
        expect(button.className).toContain('inline-flex');
        expect(button.className).toContain('font-bold');
    });

    it('does not render username or password fields', () => {
        render(<Auth {...defaultProps} />);

        expect(screen.queryByLabelText('Username')).not.toBeInTheDocument();
        expect(screen.queryByLabelText('Password')).not.toBeInTheDocument();
    });
});

describe('Auth — Google OAuth', () => {
    it('marks the session before starting Google OAuth, guards re-entry, and shows loading state', async () => {
        mockSignInWithOAuth.mockReset();
        mockSignInWithOAuth.mockReturnValue(new Promise(() => {}));
        window.sessionStorage.clear();
        render(<Auth redirectPath="/chat" />);

        const btn = screen.getByRole('button', { name: /continue with google/i });
        fireEvent.click(btn);
        fireEvent.click(btn);

        await waitFor(() => {
            expect(mockSignInWithOAuth).toHaveBeenCalledTimes(1);
            expect(mockSignInWithOAuth).toHaveBeenCalledWith({
                provider: 'google',
                options: {
                    redirectTo: `${window.location.origin}/auth/callback?next=%2Fchat`,
                },
            });
        });
        expect(window.sessionStorage.getItem('benchify_auth_started')).toBe('google');
        expect(screen.getByRole('button', { name: /redirecting to google/i })).toBeDisabled();
    });

    it('resets redirecting state and clears session marker on bfcache pageshow without resurrecting stale errorCode', async () => {
        mockSignInWithOAuth.mockReset();
        mockSignInWithOAuth.mockReturnValue(new Promise(() => {}));
        render(<Auth redirectPath="/chat" errorCode="access_denied" />);

        expect(screen.getByRole('alert')).toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: /continue with google/i }));
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();

        const pageShowEvent = new Event('pageshow') as PageTransitionEvent;
        Object.defineProperty(pageShowEvent, 'persisted', { value: true });
        fireEvent(window, pageShowEvent);

        await waitFor(() => {
            expect(screen.getByRole('button', { name: /continue with google/i })).toBeEnabled();
        });
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
        expect(window.sessionStorage.getItem('benchify_auth_started')).toBeNull();
    });

    it('shows an inline error alert and clears session marker when OAuth returns an error', async () => {
        mockSignInWithOAuth.mockReset();
        mockSignInWithOAuth.mockResolvedValue({ error: new Error('OAuth provider unavailable') });
        window.sessionStorage.clear();
        render(<Auth redirectPath="/chat" />);

        fireEvent.click(screen.getByRole('button', { name: /continue with google/i }));

        await waitFor(() => {
            expect(screen.getByRole('alert')).toHaveTextContent('OAuth provider unavailable');
        });
        expect(window.sessionStorage.getItem('benchify_auth_started')).toBeNull();
        expect(screen.getByRole('button', { name: /continue with google/i })).toBeEnabled();
    });

    it('recovers cleanly if getAuthBrowserClient throws', async () => {
        mockGetAuthBrowserClient.mockImplementationOnce(() => {
            throw new Error('Missing Supabase Auth URL');
        });
        render(<Auth redirectPath="/chat" />);

        fireEvent.click(screen.getByRole('button', { name: /continue with google/i }));

        await waitFor(() => {
            expect(screen.getByRole('alert')).toHaveTextContent('Missing Supabase Auth URL');
        });
        expect(screen.getByRole('button', { name: /continue with google/i })).toBeEnabled();
    });

    it('maps known errorCode values, ignores arbitrary phishing copy, and clears stale session marker on mount', () => {
        window.sessionStorage.setItem('benchify_auth_started', 'google');
        const { rerender, unmount } = render(<Auth errorCode="access_denied" />);

        expect(screen.getByRole('alert')).toHaveTextContent(
            'Google sign-in was cancelled. Try again when you are ready.',
        );
        expect(window.sessionStorage.getItem('benchify_auth_started')).toBeNull();

        rerender(<Auth errorCode="Account suspended — call 555-0199" />);
        expect(screen.getByRole('alert')).toHaveTextContent(
            'Google sign-in could not be completed. Please try again.',
        );
        expect(screen.getByRole('alert')).not.toHaveTextContent('555-0199');

        unmount();
        window.sessionStorage.setItem('benchify_auth_started', 'google');
        render(<Auth />);
        expect(window.sessionStorage.getItem('benchify_auth_started')).toBeNull();
    });
});
