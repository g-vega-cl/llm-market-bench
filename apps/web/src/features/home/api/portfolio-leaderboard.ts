import { getDbAdminClient } from '~/lib/db';
import { portfolioLabel } from '../lib/portfolio-label';

const BOARD_SIZE = 5;
const SPY_MAX_ROWS = 120;

type Db = ReturnType<typeof getDbAdminClient>;

export interface EquityPoint {
    date: string;
    value: number;
}

export interface LeaderboardRow {
    portfolioId: string;
    label: string;
    returnPct: number;
    observations: number;
    series: EquityPoint[];
}

export interface PortfolioLeaderboard {
    rows: LeaderboardRow[];
    spy: EquityPoint[];
    medianReturnPct: number | null;
    /** Portfolios on the board, or null when the count read failed. */
    trackedCount: number | null;
    windowDays: number;
    /** True when the board could not be read — unknown, not empty. */
    degraded: boolean;
    /** True when the benchmark read failed while the portfolios loaded. */
    spyUnavailable: boolean;
}

export function emptyLeaderboard(degraded = false): PortfolioLeaderboard {
    return {
        rows: [],
        spy: [],
        medianReturnPct: null,
        trackedCount: null,
        windowDays: 30,
        degraded,
        spyUnavailable: false,
    };
}

function toNumber(value: unknown): number {
    const n = Number(value);
    return Number.isFinite(n) ? n : 0;
}

function dbError(error: { code?: string; message: string }): Error {
    // Keep the PostgREST code: PGRST205 (stale schema cache) and 42P01 (missing
    // object) need different responses, and the message alone hides that.
    return new Error(`${error.code ?? 'PGRST'}: ${error.message}`);
}

/** Coerces chart points that crossed the loader boundary. */
export function normalizePoints(value: unknown): EquityPoint[] {
    if (!Array.isArray(value)) return [];
    return value.flatMap((raw) => {
        const point = (raw ?? {}) as Record<string, unknown>;
        const date = typeof point.date === 'string' ? point.date : '';
        const numeric = Number(point.value);
        return date && Number.isFinite(numeric) ? [{ date, value: numeric }] : [];
    });
}

/** Coerces the loader payload, including each row's nested series. */
export function normalizeRows(value: unknown): LeaderboardRow[] {
    if (!Array.isArray(value)) return [];
    return value.map((raw) => {
        const row = (raw ?? {}) as Record<string, unknown>;
        return {
            portfolioId: String(row.portfolioId ?? ''),
            label: String(row.label ?? ''),
            returnPct: toNumber(row.returnPct),
            observations: toNumber(row.observations),
            series: normalizePoints(row.series),
        };
    });
}

async function loadRanked(db: Db): Promise<Array<Record<string, unknown>>> {
    const { data, error } = await db
        .from('portfolio_leaderboard')
        .select('portfolio_id, owner_id, return_pct, observations, window_days, median_return_pct')
        .order('rank', { ascending: true })
        .order('portfolio_id', { ascending: true })
        .limit(BOARD_SIZE);

    if (error) throw dbError(error);
    return (data || []) as Array<Record<string, unknown>>;
}

/**
 * Percent series arrive pre-computed from `portfolio_leaderboard_series`, already
 * anchored on the same equity the ranking used — no arithmetic in this layer.
 */
async function loadSeries(db: Db, ids: string[]): Promise<Map<string, EquityPoint[]>> {
    const { data, error } = await db
        .from('portfolio_leaderboard_series')
        .select('portfolio_id, date, return_pct')
        .in('portfolio_id', ids)
        .order('date', { ascending: true });

    // An unchecked error here paints a blank chart that reads as "nothing traded yet".
    if (error) throw dbError(error);

    const byPortfolio = new Map<string, EquityPoint[]>();
    for (const id of ids) byPortfolio.set(id, []);
    for (const point of (data || []) as Array<Record<string, unknown>>) {
        const bucket = byPortfolio.get(String(point.portfolio_id));
        if (bucket) {
            bucket.push({ date: String(point.date), value: toNumber(point.return_pct) });
        }
    }
    return byPortfolio;
}

/** SPY percent series, anchored in SQL on the board's earliest anchor date. */
async function loadSpy(db: Db): Promise<EquityPoint[]> {
    const { data, error } = await db
        .from('spy_benchmark_series')
        .select('date, return_pct')
        .order('date', { ascending: true })
        .limit(SPY_MAX_ROWS);

    if (error) return [];

    return ((data || []) as Array<Record<string, unknown>>).map((row) => ({
        date: String(row.date),
        value: toNumber(row.return_pct),
    }));
}

async function loadCount(db: Db): Promise<number | null> {
    const { count, error } = await db
        .from('portfolio_leaderboard')
        .select('portfolio_id', { count: 'exact', head: true });

    // Never fall back to the page length: that reports "1 portfolios" as fact.
    return error ? null : count;
}

export async function fetchPortfolioLeaderboard(): Promise<PortfolioLeaderboard> {
    const db = getDbAdminClient();
    const rows = await loadRanked(db);
    if (rows.length === 0) return emptyLeaderboard();

    const ids = rows.map((row) => String(row.portfolio_id));
    const [series, spy, trackedCount] = await Promise.all([
        loadSeries(db, ids),
        loadSpy(db),
        loadCount(db),
    ]);

    const boardRows: LeaderboardRow[] = rows.map((row) => {
        const id = String(row.portfolio_id);
        return {
            portfolioId: id,
            label: portfolioLabel(String(row.owner_id)),
            returnPct: Math.round(toNumber(row.return_pct) * 100) / 100,
            observations: toNumber(row.observations),
            series: series.get(id) || [],
        };
    });

    const median = rows[0]?.median_return_pct;

    return {
        rows: boardRows,
        spy,
        medianReturnPct: median === null || median === undefined ? null : toNumber(median),
        trackedCount,
        windowDays: toNumber(rows[0]?.window_days) || 30,
        degraded: false,
        spyUnavailable: spy.length === 0,
    };
}
