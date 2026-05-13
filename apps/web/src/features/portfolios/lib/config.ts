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
        const values = Object.values(modelsConfig as Record<string, string>);
        // Normalize all owner IDs for consistent comparison
        cachedActiveOwnerIds = values.map((id) => normalizeOwnerId(id));
        return cachedActiveOwnerIds;
    } catch (error) {
        console.error('Failed to load models.json:', error);
        return [];
    }
}
