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

/**
 * Returns true if an owner ID represents a mechanical/system portfolio (starts with 'sys-').
 */
export function isSystemPortfolio(ownerId: string | null): boolean {
    if (!ownerId) return false;
    return normalizeOwnerId(ownerId).startsWith('sys-');
}

let cachedAutoresearchOwnerIds: string[] | null = null;

function addOwnerIds(set: Set<string>, ids: unknown) {
    if (Array.isArray(ids)) {
        for (const id of ids) {
            if (typeof id === 'string') set.add(normalizeOwnerId(id));
        }
    }
}

function collectTrackOwnerIds(config: Record<string, unknown>): string[] {
    const set = new Set<string>();
    addOwnerIds(set, config.AUTORESEARCH_EXPERIMENT_OWNER_IDS);
    const tracks = config.AUTORESEARCH_TRACKS;
    if (tracks && typeof tracks === 'object') {
        for (const ownerList of Object.values(tracks)) {
            addOwnerIds(set, ownerList);
        }
    }
    return Array.from(set);
}

/**
 * Returns the list of owner IDs that use auto-research (combines AUTORESEARCH_EXPERIMENT_OWNER_IDS and all tracks).
 */
export function getAutoresearchOwnerIds(): string[] {
    if (cachedAutoresearchOwnerIds) {
        return cachedAutoresearchOwnerIds;
    }

    try {
        cachedAutoresearchOwnerIds = collectTrackOwnerIds(modelsConfig as Record<string, unknown>);
        return cachedAutoresearchOwnerIds;
    } catch (error) {
        console.error('Failed to load autoresearch config:', error);
        return [];
    }
}

/**
 * Formats track ID to human readable string (e.g. 'track_default' -> 'Default Track', 'track_claude' -> 'Claude').
 */
export function formatTrackLabel(trackId?: string | null): string {
    if (!trackId || trackId === 'track_default') return 'Default Track';
    const clean = trackId.replace(/^track_/, '').replace(/_/g, ' ');
    return clean.charAt(0).toUpperCase() + clean.slice(1);
}

/**
 * Returns the track metadata for a given portfolio owner ID, if assigned.
 */
export function getPortfolioTrack(
    ownerId: string | null,
): { trackId: string; trackLabel: string } | null {
    if (!ownerId) return null;
    const normalized = normalizeOwnerId(ownerId);
    try {
        const tracks = (modelsConfig as Record<string, unknown>).AUTORESEARCH_TRACKS as
            | Record<string, string[]>
            | undefined;

        if (tracks && typeof tracks === 'object') {
            for (const [trackId, ownerList] of Object.entries(tracks)) {
                if (Array.isArray(ownerList)) {
                    const normalizedList = ownerList.map((id) => normalizeOwnerId(id));
                    if (normalizedList.includes(normalized)) {
                        return { trackId, trackLabel: formatTrackLabel(trackId) };
                    }
                }
            }
        }

        if (isAutoresearchPortfolio(ownerId)) {
            return { trackId: 'track_default', trackLabel: 'Default Track' };
        }
    } catch (error) {
        console.error('Failed to resolve portfolio track:', error);
    }
    return null;
}

/**
 * Checks if a portfolio uses auto-research based on its owner ID.
 */
export function isAutoresearchPortfolio(ownerId: string | null): boolean {
    if (!ownerId) return false;
    const normalized = normalizeOwnerId(ownerId);
    return getAutoresearchOwnerIds().includes(normalized);
}

let cachedVerifierOwnerIds: string[] | null = null;

export function getVerifierOwnerIds(): string[] {
    if (cachedVerifierOwnerIds) {
        return cachedVerifierOwnerIds;
    }

    try {
        const config = modelsConfig as Record<string, unknown>;
        const enabled = config.VERIFIER_ENABLED_OWNER_IDS;
        if (Array.isArray(enabled)) {
            cachedVerifierOwnerIds = enabled.map((id) => normalizeOwnerId(id));
            return cachedVerifierOwnerIds;
        }

        const tracks = config.AUTORESEARCH_TRACKS as Record<string, string[]> | undefined;
        if (tracks?.track_claude && Array.isArray(tracks.track_claude)) {
            cachedVerifierOwnerIds = tracks.track_claude.map((id) => normalizeOwnerId(id));
            return cachedVerifierOwnerIds;
        }

        return [];
    } catch (error) {
        console.error('Failed to load verifier config:', error);
        return [];
    }
}

/**
 * Checks if a portfolio uses a verifier based on its owner ID.
 * Only track_claude portfolios use the verifier.
 */
export function hasVerifier(ownerId: string | null): boolean {
    if (!ownerId) return false;
    const normalized = normalizeOwnerId(ownerId);
    return getVerifierOwnerIds().includes(normalized);
}
