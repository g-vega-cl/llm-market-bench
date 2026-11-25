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

let cachedArchivedOwnerIds: Set<string> | null = null;

/**
 * Owner IDs declared retired in packages/config/models.json.
 * Their rows are preserved forever but they are no longer active or updated.
 */
export function getArchivedOwnerIds(): Set<string> {
    if (cachedArchivedOwnerIds) {
        return cachedArchivedOwnerIds;
    }

    try {
        const raw = (modelsConfig as Record<string, unknown>).ARCHIVED_PORTFOLIO_OWNER_IDS;
        const ids = Array.isArray(raw)
            ? raw.filter((value): value is string => typeof value === 'string')
            : [];
        cachedArchivedOwnerIds = new Set(ids.map((id) => normalizeOwnerId(id)));
        return cachedArchivedOwnerIds;
    } catch (error) {
        console.error('Failed to load archived portfolio ids:', error);
        cachedArchivedOwnerIds = new Set();
        return cachedArchivedOwnerIds;
    }
}

/**
 * True when the owner has been retired (archived) and must be shown as inactive.
 */
export function isArchivedPortfolio(ownerId: string | null): boolean {
    if (!ownerId) return false;
    return getArchivedOwnerIds().has(normalizeOwnerId(ownerId));
}

/**
 * Single definition of "active portfolio" for the read layer.
 *
 * Archived ids are inactive even when they are mechanical `sys-*` portfolios,
 * which would otherwise be treated as always-on.
 */
export function isActiveOwnerId(ownerId: string | null): boolean {
    if (!ownerId) return false;
    if (isArchivedPortfolio(ownerId)) return false;
    if (isSystemPortfolio(ownerId)) return true;
    return getActiveOwnerIds().includes(normalizeOwnerId(ownerId));
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

const SYSTEM_PORTFOLIO_SUBTITLES: Record<string, string> = {
    'sys-future-forces': 'Multi-Horizon Thematic Forces & Catalysts (2–24 Months)',
    'sys-smid-quality-compounder': 'Quality & Momentum Small-to-Large Compounder (Zero-Ceiling)',
    'sys-pead-drift': 'Post-Earnings Drift Systematic Momentum (SUE + Jev)',
    'sys-max-pain': 'Daily Options Max Pain 0DTE Pinning (Ni et al. + Jev)',
    'sys-sentiment-fader': 'Contrarian Options Sentiment & Put/Call Ratio Fader',
    'sys-sector-ls-consensus': 'Consensus Sector Long/Short Dispersion',
    'sys-sector-ls-30d': '30-Day Consensus Sector Long/Short Dispersion',
    'sys-sector-ls-90d': '90-Day Consensus Sector Long/Short Dispersion',
    'sys-sector-uncorr-20d': '20-Day Uncorrelated Sector Momentum (Low-Beta Barbell)',
    'sys-sector-uncorr-7d': '7-Day Uncorrelated Sector Momentum (Weekly Rotation)',
    'sys-sector-naive-momentum': '20-Day Unconstrained Momentum (Top 2 Winners)',
    'sys-sector-mean-reversion': '7-Day Sector Mean Reversion (Oversold Bounce)',
};

export function getSystemPortfolioSubtitle(ownerId: string): string | undefined {
    if (SYSTEM_PORTFOLIO_SUBTITLES[ownerId]) {
        return SYSTEM_PORTFOLIO_SUBTITLES[ownerId];
    }
    if (ownerId.startsWith('sys-daily-tlt-close-')) {
        return 'Daily 20+ Year Treasury Bond Trader (3:50 PM Exit)';
    }
    if (ownerId.startsWith('sys-daily-spy-close-')) {
        return 'Daily S&P 500 Close Trader (3:50 PM Exit)';
    }
    if (ownerId.startsWith('sys-daily-spy-')) {
        return 'Daily S&P 500 Intraday Trader (Profit Target Exit)';
    }
    if (ownerId.startsWith('sys-picks-')) {
        return 'Daily 3 Up / 3 Down Stock Picks (RTH Open → Close)';
    }
    return undefined;
}
