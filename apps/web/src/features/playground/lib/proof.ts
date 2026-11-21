import type { PortfolioLeaderboard } from '~/features/home/api/portfolio-leaderboard';

export interface ProofRow {
    label: string;
    returnPct: number;
}

export interface Proof {
    winner: ProofRow | null;
    worst: ProofRow | null;
    medianReturnPct: number | null;
    trackedCount: number | null;
    windowDays: number;
    asOf: string | null;
    degraded: boolean;
}

/**
 * The board already ships a worst row and a top row; the homepage publishes both
 * rather than picking a favourable subset client-side.
 */
export function pickProof(leaderboard: PortfolioLeaderboard | null | undefined): Proof {
    const rows = Array.isArray(leaderboard?.rows) ? leaderboard.rows : [];
    const winner = rows[0] ?? null;
    const worst = leaderboard?.worst ?? null;
    const asOf = winner?.series?.at(-1)?.date ?? leaderboard?.spy?.at(-1)?.date ?? null;

    return {
        winner: winner ? { label: winner.label, returnPct: winner.returnPct } : null,
        worst: worst ? { label: worst.label, returnPct: worst.returnPct } : null,
        medianReturnPct: leaderboard?.medianReturnPct ?? null,
        trackedCount: leaderboard?.trackedCount ?? null,
        windowDays: leaderboard?.windowDays ?? 30,
        asOf,
        degraded: Boolean(leaderboard?.degraded),
    };
}

export function formatPct(value: number | null): string {
    if (value === null || !Number.isFinite(value)) return '—';
    const sign = value > 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
}
