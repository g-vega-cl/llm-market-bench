/**
 * Portfolio configuration utilities
 */

import modelsConfig from '@repo/config/models.json';

export function normalizeOwnerId(ownerId: string | null): string {
    if (!ownerId) return '';
    return ownerId
        .toLowerCase()
        .replace(/[\s_-]+/g, '-')
        .replace(/^-+|-+$/g, '');
}

let cachedActiveOwnerIds: string[] | null = null;

/**
 * Returns the list of active owner IDs from the models.json config.
 * These are the owner_ids that should be considered "active" portfolios.
 * Portfolios with owner_ids not in this list are considered deprecated/retired.
 */
export function getActiveOwnerIds(): string[] {
    if (cachedActiveOwnerIds) {
        return cachedActiveOwnerIds;
    }

    try {
        const values = Object.values(modelsConfig as Record<string, unknown>);
        // Normalize all owner IDs for consistent comparison, filtering for strings only
        cachedActiveOwnerIds = values
            .filter((val): val is string => typeof val === 'string')
            .map((id) => normalizeOwnerId(id));
        return cachedActiveOwnerIds;
    } catch (error) {
        console.error('Failed to load models.json:', error);
        return [];
    }
}

let cachedAutoresearchOwnerIds: string[] | null = null;

/**
 * Returns the list of owner IDs that use auto-research.
 */
export function getAutoresearchOwnerIds(): string[] {
    if (cachedAutoresearchOwnerIds) {
        return cachedAutoresearchOwnerIds;
    }

    try {
        const ids = (modelsConfig as Record<string, unknown>)
            .AUTORESEARCH_EXPERIMENT_OWNER_IDS as string[];
        cachedAutoresearchOwnerIds = (ids || []).map((id: string) => normalizeOwnerId(id));
        return cachedAutoresearchOwnerIds || [];
    } catch (error) {
        console.error('Failed to load autoresearch config:', error);
        return [];
    }
}

/**
 * Checks if a portfolio uses auto-research based on its owner ID.
 */
export function isAutoresearchPortfolio(ownerId: string | null): boolean {
    if (!ownerId) return false;
    const normalized = normalizeOwnerId(ownerId);
    return getAutoresearchOwnerIds().includes(normalized);
}
