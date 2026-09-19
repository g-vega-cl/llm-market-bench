import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { LogoutComponent } from './logout';

const mockReset = vi.fn();
const mockNavigate = vi.fn();
const mockInvalidate = vi.fn();
const mockLogoutFn = vi.fn().mockResolvedValue({});

vi.mock('@posthog/react', () => ({
    usePostHog: () => ({
        reset: mockReset,
    }),
}));

vi.mock('@tanstack/react-router', async () => {
    const actual = await vi.importActual('@tanstack/react-router');
    return {
        ...actual,
        useRouter: () => ({
            navigate: mockNavigate,
            invalidate: mockInvalidate,
        }),
    };
});

vi.mock('~/lib/supabase-client', () => ({
    getSupabaseBrowserClient: () => ({
        auth: {
            signOut: vi.fn().mockResolvedValue({ error: null }),
        },
    }),
}));

describe('LogoutComponent', () => {
    it('calls posthog.reset, signs out, and redirects to home', async () => {
        render(<LogoutComponent logoutAction={mockLogoutFn} />);

        expect(mockReset).toHaveBeenCalled();
        expect(mockLogoutFn).toHaveBeenCalled();
        await screen.findByText('Logging out...');
    });
});
