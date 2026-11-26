import { isRedirect } from '@tanstack/react-router';
import { describe, expect, it } from 'vitest';
import { Route as SignupRoute } from './signup';

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

describe('/signup redirect route', () => {
    it('redirects anonymous visitors to /login and normalizes ?next= into ?redirect=', async () => {
        const thrown = await runSignupBeforeLoad(
            { user: null },
            { next: '/recipes?recipeId=rec-1', error: 'access_denied' },
        );
        expect(isRedirect(thrown)).toBe(true);
        expect((thrown as { options: Record<string, unknown> }).options).toMatchObject({
            to: '/login',
            search: {
                redirect: '/recipes?recipeId=rec-1',
                error: 'access_denied',
            },
            replace: true,
        });
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
