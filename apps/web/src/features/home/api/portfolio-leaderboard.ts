import { getDbAdminClient } from '~/lib/db';
import { portfolioLabel } from '../lib/portfolio-label';

const BOARD_SIZE = 5;
const SPY_MAX_ROWS = 90;

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

/** Rebase an equity series to percent return from the anchor the ranking used. */
export function rebaseToAnchor(
    series: Array<{ date: string; equity: number }>,
    anchor: number | null,
): EquityPoint[] {
    if (!anchor || !Number.isFinite(anchor) || anchor <= 0) return [];
    return series.map((point) => ({
        date: point.date,
        value: (point.equity / anchor - 1) * 100,
    }));
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
        .select(
            'portfolio_id, owner_id, return_pct, observations, anchor_date, anchor_equity, window_days, median_return_pct',
        )
        .order('rank', { ascending: true })
        .order('portfolio_id', { ascending: true })
        .limit(BOARD_SIZE);

    if (error) throw dbError(error);
    return (data || []) as Array<Record<string, unknown>>;
}

async function loadSeries(
    db: Db,
    ids: string[],
    startDate: string,
): Promise<Map<string, Array<{ date: string; equity: number }>>> {
    const { data, error } = await db
        .from('portfolio_performance')
        .select('portfolio_id, date, total_equity')
        .in('portfolio_id', ids)
        .gte('date', startDate)
        .order('date', { ascending: true });

    // An unchecked error here paints a blank chart that reads as "nothing traded yet".
    if (error) throw dbError(error);

    const byPortfolio = new Map<string, Array<{ date: string; equity: number }>>();
    for (const id of ids) byPortfolio.set(id, []);
    for (const point of (data || []) as Array<Record<string, unknown>>) {
        const bucket = byPortfolio.get(String(point.portfolio_id));
        if (bucket) {
            bucket.push({ date: String(point.date), equity: toNumber(point.total_equity) });
        }
    }
    return byPortfolio;
}

async function loadSpy(db: Db, startDate: string): Promise<EquityPoint[]> {
    const { data, error } = await db
        .from('price_history')
        .select('price, fetched_at')
        .eq('ticker', 'SPY')
        .gte('fetched_at', startDate)
        // Newest-first then reversed: an ascending LIMIT would keep the oldest rows
        // once price_history carries intraday bars.
        .order('fetched_at', { ascending: false })
        .limit(SPY_MAX_ROWS);

    if (error) return [];

    const rows = ((data || []) as Array<Record<string, unknown>>).reverse();
    const series = rows.map((row) => ({
        date: String(row.fetched_at).slice(0, 10),
        equity: toNumber(row.price),
    }));
    return rebaseToAnchor(series, series[0]?.equity ?? null);
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
    // Start every series at the earliest anchor the board used: deriving it from the
    // view, not a local clock, is what keeps the chart and the ranking on one window.
    const startDate =
        rows
            .map((row) => String(row.anchor_date ?? ''))
            .filter(Boolean)
            .sort()[0] ?? '';

    const [series, spy, trackedCount] = await Promise.all([
        loadSeries(db, ids, startDate),
        loadSpy(db, startDate),
        loadCount(db),
    ]);

    const boardRows: LeaderboardRow[] = rows.map((row) => {
        const id = String(row.portfolio_id);
        return {
            portfolioId: id,
            label: portfolioLabel(String(row.owner_id)),
            returnPct: Math.round(toNumber(row.return_pct) * 100) / 100,
            observations: toNumber(row.observations),
            series: rebaseToAnchor(series.get(id) || [], toNumber(row.anchor_equity)),
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
