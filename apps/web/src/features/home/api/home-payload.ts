import {
    emptyLeaderboard,
    fetchPortfolioLeaderboard,
    normalizePoints,
    normalizeRows,
    type PortfolioLeaderboard,
} from '~/features/home/api/portfolio-leaderboard';
import { fetchPublicDesk, type PublicDesk } from '~/features/recipes/api/public-board-api';

export const EMPTY_DESK: PublicDesk = {
    cards: [],
    feed: [],
    liveCount: 0,
    beatSpyCount: 0,
    medianReturnPct: null,
    spotlight: null,
};

export function normalizeDesk(value: unknown): PublicDesk {
    const raw = (value ?? {}) as Partial<PublicDesk>;
    return {
        cards: Array.isArray(raw.cards) ? raw.cards : [],
        feed: Array.isArray(raw.feed) ? raw.feed : [],
        liveCount: Number(raw.liveCount ?? 0),
        beatSpyCount: Number(raw.beatSpyCount ?? 0),
        medianReturnPct: typeof raw.medianReturnPct === 'number' ? raw.medianReturnPct : null,
        spotlight:
            raw.spotlight && typeof raw.spotlight === 'object'
                ? (raw.spotlight as PublicDesk['spotlight'])
                : null,
    };
}

export function normalizeLeaderboard(value: unknown): PortfolioLeaderboard {
    const raw = (value ?? {}) as Partial<PortfolioLeaderboard>;
    return {
        // Rows carry a nested series array that also crosses the loader boundary;
        // coercing only the outer arrays was the deploy-skew crash of 4be16417.
        rows: normalizeRows(raw.rows),
        worst: normalizeRows(raw.worst ? [raw.worst] : [])[0] ?? null,
        spy: normalizePoints(raw.spy),
        medianReturnPct:
            typeof raw.medianReturnPct === 'number' && Number.isFinite(raw.medianReturnPct)
                ? raw.medianReturnPct
                : null,
        trackedCount:
            raw.trackedCount === null || raw.trackedCount === undefined
                ? null
                : Number.isFinite(Number(raw.trackedCount))
                  ? Number(raw.trackedCount)
                  : null,
        windowDays: Number.isFinite(Number(raw.windowDays)) ? Number(raw.windowDays) : 30,
        // An absent payload is an unknown board, not a young one.
        degraded: value == null ? true : Boolean(raw.degraded),
        spyUnavailable: Boolean(raw.spyUnavailable),
    };
}

/**
 * A missing board beats an error page on the front door — including during the
 * window before a migration has been applied. Every read degrades on its own.
 */
export async function getHomePayload(): Promise<{
    desk: PublicDesk;
    leaderboard: PortfolioLeaderboard;
}> {
    const [desk, leaderboard] = await Promise.all([
        fetchPublicDesk().catch((error: unknown) => {
            console.error('[home] public desk unavailable', error);
            return EMPTY_DESK;
        }),
        fetchPortfolioLeaderboard().catch((error: unknown) => {
            // A missing view and an empty board are different facts: log the first
            // and let the page say "unavailable" instead of "young".
            console.error('[home] portfolio leaderboard unavailable', error);
            return emptyLeaderboard(true);
        }),
    ]);
    return { desk, leaderboard };
}
