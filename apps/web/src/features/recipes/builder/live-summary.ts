import type { LivePortfolioAndRuns, RecipeJobRecord } from '../types';

/**
 * The four facts the workspace's live block renders, cut out of the full
 * `fetchLivePortfolioAndRuns` payload. The full read carries the whole trade
 * ledger, ten runs with their `result_json`, and (since the live page chart)
 * the equity curve; none of that belongs in `/build`'s HTML.
 */
export interface RecipeLiveSummary {
    totalEquity: number | null;
    cash: number | null;
    isLive: boolean;
    isOwner: boolean;
    turboExpiresAt: string | null;
    lastRun: RecipeJobRecord | null;
    /** When this summary was read — the "as of" stamp for the money line. */
    fetchedAt: string;
}

function finite(value: number | null | undefined): number | null {
    return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

/** `null` in, `null` out: an unread ledger stays unknown rather than becoming zeros. */
export function toLiveSummary(
    snapshot: LivePortfolioAndRuns | null | undefined,
    fetchedAt: string = new Date().toISOString(),
): RecipeLiveSummary | null {
    if (!snapshot) return null;
    const runs = Array.isArray(snapshot.recentLiveRuns) ? snapshot.recentLiveRuns : [];
    return {
        totalEquity: finite(snapshot.portfolio?.total_equity),
        cash: finite(snapshot.portfolio?.cash),
        isLive: Boolean(snapshot.liveMeta?.isLive),
        // Fail closed: without a proven owner, the block must not show the ledger.
        isOwner: snapshot.liveMeta?.isOwner === true,
        turboExpiresAt: snapshot.liveMeta?.turboExpiresAt ?? null,
        lastRun: runs[0] ?? null,
        fetchedAt,
    };
}
