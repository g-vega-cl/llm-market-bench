/**
 * useCurrentUser — client-only user state.
 *
 * Why this exists
 * ---------------
 * The previous implementation called `supabase.auth.getUser()` in the root
 * route's `beforeLoad` (server-side) for every page hit — even fully public
 * pages like the homepage. That single Supabase call was responsible for
 * ~250 ms of the homepage's 730 ms TTFB.
 *
 * This hook fetches user state lazily on the client via a server function
 * exposed by TanStack Start. The homepage (and other public routes) no longer
 * pay any auth cost during SSR. Protected routes (under `/_authed/*`) still
 * enforce auth via their own server-side check.
 */

import { useQuery } from '@tanstack/react-query';
import { createServerFn } from '@tanstack/react-start';
import { useEffect, useState } from 'react';
import { getSupabaseServerClient } from './supabase';

export interface CurrentUser {
    email: string;
}

export const currentUserQueryKey = ['current-user'] as const;

/**
 * Server function: returns the current user (or null) by inspecting the
 * Supabase session cookies. Returns null on the server for SSR but resolves
 * to the real user when called from the client.
 */
export const getCurrentUser = createServerFn({ method: 'GET' }).handler(
    async (): Promise<CurrentUser | null> => {
        try {
            const supabase = getSupabaseServerClient();
            const { data } = await supabase.auth.getUser();
            if (!data.user?.email) return null;
            return { email: data.user.email };
        } catch {
            return null;
        }
    },
);

async function fetchCurrentUser(): Promise<CurrentUser | null> {
    return getCurrentUser();
}

/**
 * Returns the current user via a client-side query. Returns `undefined` while
 * loading and `null` if the user is not signed in.
 */
export function useCurrentUser() {
    const [enabled, setEnabled] = useState(false);
    useEffect(() => setEnabled(true), []);

    return useQuery({
        queryKey: currentUserQueryKey,
        queryFn: fetchCurrentUser,
        enabled,
        staleTime: 1000 * 60,
        gcTime: 1000 * 60 * 5,
    });
}
