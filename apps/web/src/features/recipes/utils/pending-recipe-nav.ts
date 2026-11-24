/**
 * Which saved recipe the router is currently navigating to, and through which
 * bot-card affordance, if any.
 *
 * `/recipes` links to two destinations per bot card — `/build?recipeId=<id>`
 * (the recipe workspace) and `/recipes/live/<id>` (the live page). While the
 * destination's loader is resolving, TanStack Router exposes that in-flight
 * location as `router.state.location` with `status === 'pending'`, so the card
 * pending state is derived from the router instead of being latched in local
 * state (a failed or aborted navigation would strand a latched flag).
 */
export type PendingRecipeTarget = {
    recipeId: string;
    destination: 'workspace' | 'live';
};

export function pendingRecipeTarget(
    status: 'pending' | 'idle',
    location: { pathname?: string; search?: unknown },
): PendingRecipeTarget | null {
    if (status !== 'pending') return null;

    // The live page is identified by its path and wins over a stray query
    // string, so `/recipes/live/<id>?recipeId=other` still reports `live`.
    const pathname = typeof location.pathname === 'string' ? location.pathname : '';
    const liveMatch = /^\/recipes\/live\/([^/?#]+)/.exec(pathname);
    const liveId = liveMatch ? normaliseId(safeDecode(liveMatch[1])) : null;
    if (liveId) return { recipeId: liveId, destination: 'live' };

    const workspaceId = readRecipeIdFromSearch(location.search);
    return workspaceId ? { recipeId: workspaceId, destination: 'workspace' } : null;
}

function readRecipeIdFromSearch(search: unknown): string | null {
    if (typeof search === 'string') {
        const raw = new URLSearchParams(search.replace(/^\?/, '')).get('recipeId');
        return normaliseId(raw);
    }
    if (search && typeof search === 'object') {
        const raw = (search as { recipeId?: unknown }).recipeId;
        return normaliseId(typeof raw === 'string' ? raw : null);
    }
    return null;
}

function normaliseId(value: string | null): string | null {
    const trimmed = value?.trim();
    return trimmed ? trimmed : null;
}

function safeDecode(value: string): string {
    try {
        return decodeURIComponent(value);
    } catch {
        return value;
    }
}
