import { isRedirect } from '@tanstack/react-router';
import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { Route as SignupRoute, SignupRouteComponent } from './signup';

type GuardContext = { user: { id: string; email: string } | null };

async function runSignupBeforeLoad(
    context: GuardContext,
    search: Record<string, unknown> = {},
): Promise<unknown> {
    try {
        await (
            SignupRoute.options.beforeLoad as (args: {
                context: GuardContext;
                search: Record<string, unknown>;
            }) => Promise<void>
        )({
            context,
            search,
        });
        return null;
    } catch (err) {
        return err;
    }
}

afterEach(() => vi.restoreAllMocks());

describe('/signup route', () => {
    it('does not redirect anonymous visitors to /login so /signup renders an explicit create-account view', async () => {
        const result = await runSignupBeforeLoad(
            { user: null },
            { next: '/recipes?recipeId=rec-1', error: 'access_denied' },
        );
        expect(result).toBeNull();
    });

    it('renders the dedicated signup heading, Google signup CTA, and sign-in cross-link', () => {
        vi.spyOn(SignupRoute, 'useSearch').mockReturnValue({
            next: '/build',
            redirect: undefined,
            error: undefined,
        } as never);

        render(<SignupRouteComponent />);

        expect(
            screen.getByRole('heading', { name: /create your benchify account/i }),
        ).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /sign up with google/i })).toBeInTheDocument();
        expect(screen.getByRole('link', { name: /sign in/i })).toHaveAttribute(
            'href',
            '/login?redirect=%2Fbuild',
        );
    });

    it('redirects signed-in visitors straight to their sanitized target without bouncing through /login', async () => {
        const selfTarget = await runSignupBeforeLoad(
            { user: { id: 'u1', email: 'u@example.com' } },
            { next: '/signup' },
        );
        expect(isRedirect(selfTarget)).toBe(true);
        expect((selfTarget as { options: { href: string } }).options.href).toBe('/');

        const recipesTarget = await runSignupBeforeLoad(
            { user: { id: 'u1', email: 'u@example.com' } },
            { next: '/recipes' },
        );
        expect(isRedirect(recipesTarget)).toBe(true);
        expect((recipesTarget as { options: { href: string } }).options.href).toBe('/recipes');
    });
});
