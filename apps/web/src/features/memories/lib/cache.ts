import type { Memory } from '@llm-market-bench/database';

const CACHE_KEY = 'benchify_memories_v1';
const MAX_CACHE_SIZE = 500;

/**
 * Safely retrieves cached memories from LocalStorage.
 * Returns an empty array if running on server (SSR) or if cache is empty/invalid.
 */
export function getCachedMemories(): Memory[] {
    if (typeof window === 'undefined') {
        return [];
    }

    try {
        const cached = localStorage.getItem(CACHE_KEY);
        if (!cached) return [];

        const parsed = JSON.parse(cached);
        return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
        console.error('Failed to parse cached memories:', e);
        return [];
    }
}

/**
 * Safely saves memories list to LocalStorage.
 */
export function saveCachedMemories(memories: Memory[]): void {
    if (typeof window === 'undefined') return;

    try {
        localStorage.setItem(CACHE_KEY, JSON.stringify(memories));
    } catch (e) {
        console.error('Failed to save memories to cache:', e);
    }
}

/**
 * Merges new memories with existing cached ones.
 * - Deduplicates items by unique id
 * - Sorts them chronologically descending (newest first)
 * - Caps the final list size at 500 items to avoid storage limit issues
 */
export function mergeAndDeduplicate(newMemories: Memory[], cachedMemories: Memory[]): Memory[] {
    const merged = [...newMemories, ...cachedMemories];

    const seen = new Set<string>();
    const deduplicated = merged.filter((m) => {
        if (!m.id) return true; // keep items without ids just in case
        if (seen.has(m.id)) return false;
        seen.add(m.id);
        return true;
    });

    // Sort by created_at descending (newest first)
    deduplicated.sort((a, b) => {
        const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
        const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
        return dateB - dateA;
    });

    // Cap at the maximum allowed size
    return deduplicated.slice(0, MAX_CACHE_SIZE);
}
