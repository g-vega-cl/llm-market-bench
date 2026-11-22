import { isValidWorldId, type WorldId } from './voxel-world';

export const WORLD_STORAGE_KEY = 'benchify.world';

/**
 * Reads the visitor's persisted backdrop world preference from browser storage.
 * Safe during SSR and inside sandboxed storage contexts.
 */
export function readPreferredWorld(): WorldId | null {
    if (typeof window === 'undefined') return null;
    try {
        const stored = window.localStorage.getItem(WORLD_STORAGE_KEY);
        return isValidWorldId(stored) ? stored : null;
    } catch {
        return null;
    }
}

/**
 * Persists the visitor's chosen backdrop world preference to browser storage.
 */
export function writePreferredWorld(worldId: WorldId): boolean {
    if (typeof window === 'undefined') return false;
    try {
        window.localStorage.setItem(WORLD_STORAGE_KEY, worldId);
        return true;
    } catch {
        return false;
    }
}
