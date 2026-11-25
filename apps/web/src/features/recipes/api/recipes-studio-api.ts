import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { getDbAdminClient, getDbServerClient } from '~/lib/db';
import { hydrateMemoriesBlockText, hydrateNewsBlockText } from '../prompt-builder';
import type {
    CompletedTradeRecord,
    LivePortfolioAndRuns,
    LivePortfolioSnapshot,
    LiveRunResult,
    OpenPositionRecord,
    PushStrategy,
    RecipeAlert,
    RecipeCadence,
    RecipeJobRecord,
    RecipeOverviewData,
} from '../types';
import { getEtDateString } from '../utils/market-hours';
import { fetchRecipeBacktestHistory } from './recipe-jobs-api';

export async function fetchRecipeAlerts(userId: string): Promise<RecipeAlert[]> {
    const db = getDbAdminClient();
    const { data, error } = await db
        .from('recipe_alerts_inbox')
        .select('*')
        .eq('user_id', userId)
        .order('created_at', { ascending: false })
        .limit(50);

    if (error) {
        throw new Error(error.message);
    }
    return (data || []) as RecipeAlert[];
}

export const fetchRecipeAlertsFn = createServerFn({ method: 'GET' }).handler(async () => {
    const auth = getAuthServerClient();
    const {
        data: { user },
    } = await auth.auth.getUser();
    if (!user?.id) throw new Error('Unauthorized: please sign in to view recipe alerts');
    return fetchRecipeAlerts(user.id);
});

export async function markAlertRead(
    alertId: string,
    userId: string,
): Promise<{ success: boolean }> {
    const db = getDbAdminClient();
    const { error } = await db
        .from('recipe_alerts_inbox')
        .update({ is_read: true })
        .eq('id', alertId)
        .eq('user_id', userId);

    if (error) throw new Error(error.message);
    return { success: true };
}

export const markAlertReadFn = createServerFn({ method: 'POST' })
    .validator((d: { alertId: string }) => d)
    .handler(async ({ data: { alertId } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        if (!user?.id) throw new Error('Unauthorized: please sign in to update alerts');
        return markAlertRead(alertId, user.id);
    });

export async function submitWaitlistPledge(
    userId: string,
    email: string,
    intendedTier: string,
    feedback = '',
): Promise<{ success: boolean }> {
    const db = getDbAdminClient();
    const { error } = await db.from('recipe_waitlist_pledges').insert({
        user_id: userId,
        email,
        intended_tier: intendedTier,
        feedback,
    });

    if (error) throw new Error(error.message);
    return { success: true };
}

export const submitWaitlistPledgeFn = createServerFn({ method: 'POST' })
    .validator((d: { email: string; intendedTier: string; feedback?: string }) => d)
    .handler(async ({ data: { email, intendedTier, feedback = '' } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        if (!user?.id) throw new Error('Unauthorized: please sign in to submit a waitlist pledge');
        return submitWaitlistPledge(user.id, email, intendedTier, feedback);
    });

export async function previewStrategyPrompt(
    strategy: PushStrategy,
): Promise<Record<string, string>> {
    const db = getDbServerClient();
    const now = Date.now();
    const hydrated: Record<string, string> = {};

    const needsNews = strategy.stages.some((stage) =>
        stage.blocks.some((block) => block.type === 'news'),
    );
    const needsMemories = strategy.stages.some((stage) =>
        stage.blocks.some((block) => block.type === 'memories'),
    );

    let newsRows: Array<{ title?: string; full_text?: string; date_published?: string }> = [];
    if (needsNews) {
        const { data } = await db
            .from('recipe_news_corpus')
            .select('article_id, title, full_text, date_published, tickers')
            .order('date_published', { ascending: false })
            .limit(500);
        newsRows = data ?? [];
    }

    let memoryRows: Array<{
        content?: string;
        created_at?: string;
        memory_type?: string;
        importance_score?: number;
    }> = [];
    if (needsMemories) {
        const { data } = await db
            .from('memories')
            .select('id, content, created_at, memory_type, importance_score')
            .order('created_at', { ascending: false })
            .limit(500);
        memoryRows = data ?? [];
    }

    for (const stage of strategy.stages) {
        for (const block of stage.blocks) {
            if (block.type === 'news') {
                hydrated[block.id] = hydrateNewsBlockText(block, newsRows, now);
            } else if (block.type === 'memories') {
                hydrated[block.id] = hydrateMemoriesBlockText(block, memoryRows, now);
            }
        }
    }

    return hydrated;
}

export const previewStrategyPromptFn = createServerFn({ method: 'POST' })
    .validator((d: { strategy: PushStrategy }) => d)
    .handler(async ({ data: { strategy } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        if (!user?.id) throw new Error('Unauthorized: please sign in to preview live prompts');
        return previewStrategyPrompt(strategy);
    });

const LIVE_SLIPPAGE_RATE = 0.0005;

function enrichLiveOpenPositions(
    rawPositions: OpenPositionRecord[],
    latestPriceByTicker: Map<string, number>,
): OpenPositionRecord[] {
    return rawPositions.map((pos) => {
        const ticker = String(pos.ticker || '').toUpperCase();
        const shares = Number(pos.shares || 0);
        const entryPx = Number(pos.entry_price || 0);
        const costBasis = Number(pos.cost_basis ?? shares * entryPx);
        const curPx = latestPriceByTicker.get(ticker) ?? entryPx;
        const marketVal = shares * curPx;
        const netLiquidation = marketVal * (1 - LIVE_SLIPPAGE_RATE);
        const unrPnl = netLiquidation - costBasis;
        const unrPct = costBasis > 0 ? (unrPnl / costBasis) * 100 : 0;
        return {
            ...pos,
            ticker,
            current_price: Number(curPx.toFixed(4)),
            market_value: Number(marketVal.toFixed(2)),
            unrealized_pnl_net: Number(unrPnl.toFixed(2)),
            unrealized_return_pct: Number(unrPct.toFixed(2)),
        };
    });
}

interface PriceTimestampEntry {
    price: number;
    ts: string;
}

function seedRunSignalPrices(recentLiveRuns: RecipeJobRecord[]): Map<string, PriceTimestampEntry> {
    const seeded = new Map<string, PriceTimestampEntry>();
    for (const run of recentLiveRuns) {
        const res = run.result_json as LiveRunResult | null;
        if (!res?.signal_prices) continue;
        const ts = String(res.as_of_utc || run.created_at || '');
        for (const [tkr, px] of Object.entries(res.signal_prices)) {
            const sym = tkr.toUpperCase();
            const existing = seeded.get(sym);
            if (px > 0 && (!existing || ts >= existing.ts)) {
                seeded.set(sym, { price: px, ts });
            }
        }
    }
    return seeded;
}

async function collectLatestMarkPrices(
    db: ReturnType<typeof getDbServerClient>,
    rawPositions: OpenPositionRecord[],
    recentLiveRuns: RecipeJobRecord[],
): Promise<Map<string, number>> {
    const entries = seedRunSignalPrices(recentLiveRuns);
    const tickers = Array.from(
        new Set(rawPositions.map((p) => String(p.ticker || '').toUpperCase()).filter(Boolean)),
    );
    if (tickers.length > 0) {
        const { data: barRows } = await db
            .from('recipe_intraday_bars')
            .select('ticker, bar_time_utc, close')
            .in('ticker', tickers)
            .order('bar_time_utc', { ascending: false })
            .limit(Math.max(50, tickers.length * 10));
        for (const bar of (barRows || []) as {
            ticker: string;
            bar_time_utc: string;
            close: number;
        }[]) {
            const tkr = String(bar.ticker || '').toUpperCase();
            const prev = entries.get(tkr);
            if (bar.close > 0 && (!prev || bar.bar_time_utc >= prev.ts)) {
                entries.set(tkr, { price: Number(bar.close), ts: bar.bar_time_utc });
            }
        }
    }
    const latestPrices = new Map<string, number>();
    for (const [tkr, entry] of entries) {
        latestPrices.set(tkr, entry.price);
    }
    return latestPrices;
}

interface RecipePortfolioRow {
    id: string;
    user_id: string;
    name?: string | null;
    description?: string | null;
    cadence?: RecipeCadence | null;
    is_live?: boolean | null;
    turbo_expires_at?: string | null;
    is_public: boolean;
    is_template: boolean;
    archived_at?: string | null;
    graph_json?: PushStrategy | null;
    paper_cash?: number | null;
    paper_positions?: OpenPositionRecord[] | null;
    paper_trades?: CompletedTradeRecord[] | null;
    paper_equity_curve?: { time: string; equity: number }[] | null;
}

async function buildLivePortfolioSnapshot(
    db: ReturnType<typeof getDbServerClient>,
    row: RecipePortfolioRow,
    recentLiveRuns: RecipeJobRecord[],
): Promise<LivePortfolioSnapshot> {
    const rawPositions = Array.isArray(row.paper_positions) ? row.paper_positions : [];
    const latestPrices = await collectLatestMarkPrices(db, rawPositions, recentLiveRuns);

    const cash = Number(row.paper_cash ?? 10000);
    const openPositions = enrichLiveOpenPositions(rawPositions, latestPrices);
    const holdingsVal = openPositions.reduce(
        (sum, p) => sum + Number(p.shares || 0) * Number(p.current_price ?? p.entry_price ?? 0),
        0,
    );

    return {
        cash: Number(cash.toFixed(2)),
        total_equity: Number((cash + holdingsVal).toFixed(2)),
        open_positions: openPositions,
        trades: Array.isArray(row.paper_trades) ? row.paper_trades : [],
        equity_curve: Array.isArray(row.paper_equity_curve) ? row.paper_equity_curve : [],
    };
}

async function readTurboUsedToday(
    db: ReturnType<typeof getDbServerClient>,
    userId: string | null,
    isOwner: boolean,
): Promise<boolean> {
    if (!isOwner || !userId) return false;
    const quotaRes = await db
        .from('recipe_user_quotas')
        .select('last_turbo_et_date')
        .eq('user_id', userId)
        .limit(1);
    const todayEt = getEtDateString(new Date());
    const quotaRow = Array.isArray(quotaRes.data) ? quotaRes.data[0] : null;
    return Boolean(
        quotaRow &&
            (quotaRow as { last_turbo_et_date?: string | null }).last_turbo_et_date === todayEt,
    );
}

const PUBLIC_CACHE_TTL_MS = 30_000;
const PUBLIC_CACHE_MAX_ENTRIES = 50;

const publicLiveCache = new Map<string, { expiresAt: number; value: LivePortfolioAndRuns }>();
const publicOverviewCache = new Map<string, { expiresAt: number; value: RecipeOverviewData }>();

export function clearPublicRecipeReadCaches(): void {
    publicLiveCache.clear();
    publicOverviewCache.clear();
}

export function invalidatePublicRecipeCache(recipeId: string): void {
    if (!recipeId) return;
    publicLiveCache.delete(recipeId);
    publicOverviewCache.delete(recipeId);
}

function readBoundedCache<T>(
    cache: Map<string, { expiresAt: number; value: T }>,
    key: string,
): T | null {
    const entry = cache.get(key);
    if (!entry) return null;
    if (Date.now() > entry.expiresAt) {
        cache.delete(key);
        return null;
    }
    return entry.value;
}

function writeBoundedCache<T>(
    cache: Map<string, { expiresAt: number; value: T }>,
    key: string,
    value: T,
) {
    cache.delete(key);
    if (cache.size >= PUBLIC_CACHE_MAX_ENTRIES) {
        const oldestKey = cache.keys().next().value;
        if (oldestKey !== undefined) cache.delete(oldestKey);
    }
    cache.set(key, { expiresAt: Date.now() + PUBLIC_CACHE_TTL_MS, value });
}

function slimBacktestsForOverview(backtests: RecipeJobRecord[]): RecipeJobRecord[] {
    let seenLatestCompleted = false;
    return backtests.map((job) => {
        if (
            !job.result_json ||
            ('mode' in job.result_json && job.result_json.mode === 'live_turn')
        ) {
            return job;
        }
        const res = job.result_json;
        const isLatestCompleted = !seenLatestCompleted && job.status === 'completed';
        if (isLatestCompleted) seenLatestCompleted = true;

        return {
            ...job,
            result_json: isLatestCompleted
                ? {
                      ...res,
                      day_steps: (res.day_steps ?? []).map((step) => ({
                          ...step,
                          prompt: undefined,
                          trace: undefined,
                          full_output: undefined,
                      })),
                  }
                : {
                      mode: 'backtest',
                      window_dates: res.window_dates,
                      total_return_pct_midpoint: res.total_return_pct_midpoint,
                      total_return_pct_net: res.total_return_pct_net,
                      total_trades: res.total_trades,
                      win_rate_pct: res.win_rate_pct,
                      max_drawdown_pct: res.max_drawdown_pct,
                      equity_curve: [],
                      trades: [],
                  },
        };
    });
}

/**
 * Strips heavy hydrated prompts and execution trace rounds from live_turn rows
 * so Overview can analyze up to 50 recent turns without bloating SSR HTML.
 */
function slimLiveRunsForOverview(runs: RecipeJobRecord[]): RecipeJobRecord[] {
    return runs.map((run) => {
        if (
            !run.result_json ||
            !('mode' in run.result_json) ||
            run.result_json.mode !== 'live_turn'
        ) {
            return run;
        }
        const live = run.result_json as LiveRunResult;
        const rawNarrative = (live.final_output || live.stages?.[0]?.output || '').trim();
        return {
            ...run,
            result_json: {
                mode: 'live_turn',
                as_of_utc: live.as_of_utc,
                signals: live.signals ?? [],
                final_output: rawNarrative.slice(0, 240),
                stages: (live.stages ?? []).map((st) => ({
                    stage_id: st.stage_id,
                    prompt: '',
                    output: '',
                    tool_calls: st.tool_calls ?? [],
                })),
            },
        };
    });
}

function assertReadableRecipeRow(
    recipeRow: unknown,
    recipeErr: unknown,
    recipeId: string,
    userId: string | null,
    unauthorizedMessage: string,
): { row: RecipePortfolioRow; isOwner: boolean } {
    if (recipeErr || !recipeRow) {
        throw new Error(`Recipe not found: ${recipeId}`);
    }
    const row = recipeRow as RecipePortfolioRow;
    const isOwner = Boolean(userId && row.user_id === userId);
    if (!isOwner && !row.is_public && !row.is_template) {
        throw new Error(unauthorizedMessage);
    }
    if (!isOwner && row.archived_at) {
        throw new Error(`Recipe not found: ${recipeId}`);
    }
    return { row, isOwner };
}

/**
 * A cached public payload must never outlive the bot's visibility.
 *
 * These caches live in process memory, so an unpublish handled by another
 * instance cannot invalidate them; without this check a stranger keeps reading
 * a bot the owner has just hidden until the TTL expires. One small indexed read
 * re-establishes the gate, while the expensive payload stays cached.
 */
async function isStillPubliclyReadable(
    db: ReturnType<typeof getDbServerClient>,
    recipeId: string,
): Promise<boolean> {
    const { data, error } = await db
        .from('strategy_recipes')
        .select('id, is_public, is_template, archived_at')
        .eq('id', recipeId)
        .maybeSingle();
    if (error || !data) return false;
    const row = data as {
        is_public?: boolean | null;
        is_template?: boolean | null;
        archived_at?: string | null;
    };
    if (row.archived_at) return false;
    return Boolean(row.is_public) || Boolean(row.is_template);
}

export async function fetchLivePortfolioAndRuns(
    recipeId: string,
    userId: string | null,
): Promise<LivePortfolioAndRuns> {
    const db = getDbServerClient({ useServiceRole: true });
    if (!userId) {
        const cached = readBoundedCache(publicLiveCache, recipeId);
        if (cached && (await isStillPubliclyReadable(db, recipeId))) return cached;
    }

    const { data: recipeRow, error: recipeErr } = await db
        .from('strategy_recipes')
        .select(
            'id, user_id, name, description, cadence, is_live, turbo_expires_at, is_public, is_template, archived_at, paper_cash, paper_positions, paper_trades, paper_equity_curve',
        )
        .eq('id', recipeId)
        .single();

    const { row, isOwner } = assertReadableRecipeRow(
        recipeRow,
        recipeErr,
        recipeId,
        userId,
        'Unauthorized: cannot view this recipe portfolio',
    );

    const [{ data: runRows }, turboUsedToday] = await Promise.all([
        db
            .from('recipe_execution_queue')
            .select(
                'id, recipe_id, mode, status, progress_pct, provider, model, result_json, error_message, created_at, started_at, completed_at',
            )
            .eq('recipe_id', recipeId)
            .eq('user_id', row.user_id)
            .eq('mode', 'live_turn')
            .order('created_at', { ascending: false })
            .limit(10),
        readTurboUsedToday(db, userId, isOwner),
    ]);

    const recentLiveRuns = (runRows || []) as RecipeJobRecord[];
    const portfolio = await buildLivePortfolioSnapshot(db, row, recentLiveRuns);

    const result: LivePortfolioAndRuns = {
        portfolio,
        recentLiveRuns,
        liveMeta: {
            recipeName: row.name ?? '',
            description: row.description ?? '',
            cadence: row.cadence ?? '3h',
            isLive: Boolean(row.is_live),
            isOwner,
            isPublic: Boolean(row.is_public),
            isTemplate: Boolean(row.is_template),
            turboExpiresAt: row.turbo_expires_at ?? null,
            turboUsedToday,
        },
    };
    if (!isOwner) {
        writeBoundedCache(publicLiveCache, recipeId, result);
    }
    return result;
}

export const fetchLivePortfolioAndRunsFn = createServerFn({ method: 'GET' })
    .validator((d: { recipeId: string }) => d)
    .handler(async ({ data: { recipeId } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        return fetchLivePortfolioAndRuns(recipeId, user?.id ?? null);
    });

function resolveReadableOverviewRow(
    recipeRow: unknown,
    recipeErr: unknown,
    recipeId: string,
    userId: string | null,
): { row: RecipePortfolioRow; graph: PushStrategy; isOwner: boolean } {
    const { row, isOwner } = assertReadableRecipeRow(
        recipeRow,
        recipeErr,
        recipeId,
        userId,
        'Unauthorized: cannot view this recipe',
    );
    const graph = row.graph_json;
    if (!graph || !Array.isArray(graph.stages) || graph.stages.length !== 1) {
        throw new Error('Recipe has no runnable strategy graph');
    }
    return { row, graph, isOwner };
}

export async function fetchRecipeOverview(
    recipeId: string,
    userId: string | null,
): Promise<RecipeOverviewData> {
    const db = getDbServerClient({ useServiceRole: true });
    if (!userId) {
        const cached = readBoundedCache(publicOverviewCache, recipeId);
        if (cached && (await isStillPubliclyReadable(db, recipeId))) return cached;
    }

    const { data: recipeRow, error: recipeErr } = await db
        .from('strategy_recipes')
        .select(
            'id, user_id, name, description, cadence, is_public, is_template, is_live, turbo_expires_at, archived_at, graph_json, paper_cash, paper_positions, paper_trades, paper_equity_curve',
        )
        .eq('id', recipeId)
        .single();

    const { row, graph, isOwner } = resolveReadableOverviewRow(
        recipeRow,
        recipeErr,
        recipeId,
        userId,
    );

    const [{ data: runRows }, recentBacktests, turboUsedToday] = await Promise.all([
        db
            .from('recipe_execution_queue')
            .select(
                'id, recipe_id, mode, status, progress_pct, provider, model, result_json, error_message, created_at, started_at, completed_at',
            )
            .eq('recipe_id', recipeId)
            .eq('user_id', row.user_id)
            .eq('mode', 'live_turn')
            .order('created_at', { ascending: false })
            .limit(50),
        fetchRecipeBacktestHistory(recipeId, row.user_id, 5).catch(() => []),
        readTurboUsedToday(db, userId, isOwner),
    ]);

    const recentLiveRuns = (runRows || []) as RecipeJobRecord[];
    const portfolio = await buildLivePortfolioSnapshot(db, row, recentLiveRuns);

    const strategy: PushStrategy = {
        ...graph,
        id: isOwner ? row.id : undefined,
        name: row.name || graph.name,
        description: row.description ?? graph.description,
        cadence: row.cadence || graph.cadence,
    };

    const overviewResult: RecipeOverviewData = {
        recipeId: row.id,
        strategy,
        isOwner,
        isPublic: Boolean(row.is_public),
        isTemplate: Boolean(row.is_template),
        isLive: Boolean(row.is_live),
        turboExpiresAt: row.turbo_expires_at ?? null,
        turboUsedToday,
        portfolio,
        recentLiveRuns: slimLiveRunsForOverview(recentLiveRuns),
        recentBacktests: slimBacktestsForOverview(recentBacktests),
    };
    if (!isOwner) {
        writeBoundedCache(publicOverviewCache, recipeId, overviewResult);
    }
    return overviewResult;
}

export const fetchRecipeOverviewFn = createServerFn({ method: 'GET' })
    .validator((d: { recipeId: string }) => d)
    .handler(async ({ data: { recipeId } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        return fetchRecipeOverview(recipeId, user?.id ?? null);
    });
