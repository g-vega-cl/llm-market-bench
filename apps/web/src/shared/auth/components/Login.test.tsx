import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Login } from './Login';

vi.mock('@posthog/react', () => ({
    usePostHog: () => ({
        identify: vi.fn(),
        capture: vi.fn(),
    }),
}));

vi.mock('@tanstack/react-router', async () => {
    const actual = await vi.importActual('@tanstack/react-router');
    return {
        ...actual,
        useRouter: () => ({ invalidate: vi.fn(), navigate: vi.fn() }),
    };
});

vi.mock('@tanstack/react-start', () => ({
    useServerFn: (fn: (...args: unknown[]) => unknown) => fn,
}));

vi.mock('@tanstack/react-query', async () => {
    const actual = await vi.importActual('@tanstack/react-query');
    return {
        ...actual,
        useMutation: () => ({
            mutate: vi.fn(),
            status: 'idle',
            data: null,
        }),
    };
});

vi.mock('~/routes/_authed', () => ({
    loginFn: vi.fn(),
}));

vi.mock('~/routes/signup', () => ({
    signupFn: vi.fn(),
}));

vi.mock('~/lib/supabase-client', () => ({
    getSupabaseBrowserClient: () => ({
        auth: {
            signInWithOAuth: vi.fn(),
        },
    }),
}));

describe('Login — uses design system', () => {
    it('renders buttons using DS Button component', () => {
        render(<Login />);

        const buttons = screen.getAllByRole('button');
        expect(buttons.length).toBeGreaterThanOrEqual(1);

        for (const btn of buttons) {
            expect(btn.className).toContain('inline-flex');
            expect(btn.className).toContain('font-bold');
        }
    });
});
