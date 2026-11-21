import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { getDbAdminClient } from '~/lib/db';

export type RunRequestResult =
    | { kind: 'submitted' }
    | { kind: 'already' }
    | { kind: 'error'; message: string; needsAuth?: boolean };

/**
 * "Ask for more runs" — one row per user per ET day (`UNIQUE (user_id, request_day)`),
 * so a double submit is a 23505 the UI can explain instead of a duplicate.
 */
export const submitRunRequestFn = createServerFn({ method: 'POST' })
    .validator((data: { email: string; note: string }) => data)
    .handler(async ({ data }): Promise<RunRequestResult> => {
        const auth = getAuthServerClient();
        const { data: authData } = await auth.auth.getUser();
        const userId = authData?.user?.id;
        if (!userId) {
            return { kind: 'error', needsAuth: true, message: 'Sign in to ask for more runs.' };
        }

        const db = getDbAdminClient();
        const { error } = await db.from('run_requests').insert({
            user_id: userId,
            email: data.email.slice(0, 200),
            note: data.note.slice(0, 280),
        });

        if (!error) return { kind: 'submitted' };
        if (error.code === '23505') return { kind: 'already' };
        if (/does not exist|schema cache|PGRST205/i.test(error.message ?? '')) {
            return {
                kind: 'error',
                message: 'Requests are not open yet — try again after the deploy.',
            };
        }
        return { kind: 'error', message: error.message ?? 'Could not send the request.' };
    });
