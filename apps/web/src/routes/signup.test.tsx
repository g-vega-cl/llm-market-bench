import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SignupComp } from './signup';

const mockIdentify = vi.fn();
const mockCapture = vi.fn();

vi.mock('@posthog/react', () => ({
    usePostHog: () => ({
        identify: mockIdentify,
        capture: mockCapture,
    }),
}));

vi.mock('@tanstack/react-router', async () => {
    const actual = await vi.importActual('@tanstack/react-router');
    return {
        ...actual,
        useRouter: () => ({ invalidate: vi.fn(), navigate: vi.fn() }),
    };
});

vi.mock('@tanstack/react-start', async () => {
    const actual = await vi.importActual('@tanstack/react-start');
    return {
        ...actual,
        useServerFn: (fn: (...args: unknown[]) => unknown) => fn,
    };
});

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

vi.mock('~/lib/supabase-client', () => ({
    getSupabaseBrowserClient: () => ({
        auth: {
            signInWithOAuth: vi.fn(),
        },
    }),
}));

describe('SignupComp', () => {
    it('renders Sign Up form and buttons', () => {
        render(<SignupComp />);

        expect(screen.getByRole('heading', { name: 'Sign Up' })).toBeInTheDocument();
        const buttons = screen.getAllByRole('button');
        expect(buttons.length).toBeGreaterThanOrEqual(1);
    });
});
