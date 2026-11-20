import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { getDbAdminClient, getDbServerClient } from '~/lib/db';
import { hydrateMemoriesBlockText, hydrateNewsBlockText } from '../prompt-builder';
import type {
    CompletedTradeRecord,
    LivePortfolioAndRuns,
    LiveRunResult,
    OpenPositionRecord,
    PushStrategy,
    RecipeAlert,
    RecipeJobRecord,
} from '../types';
import { getEtDateString } from '../utils/market-hours';

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

export async function fetchLivePortfolioAndRuns(
    recipeId: string,
    userId: string,
): Promise<LivePortfolioAndRuns> {
    const db = getDbServerClient({ useServiceRole: true });
    const { data: recipeRow, error: recipeErr } = await db
        .from('strategy_recipes')
        .select(
            'id, user_id, name, is_live, turbo_expires_at, is_public, is_template, paper_cash, paper_positions, paper_trades',
        )
        .eq('id', recipeId)
        .single();

    if (recipeErr || !recipeRow) {
        throw new Error(`Recipe not found: ${recipeId}`);
    }

    const row = recipeRow as {
        id: string;
        user_id: string;
        name?: string | null;
        is_live?: boolean | null;
        turbo_expires_at?: string | null;
        is_public: boolean;
        is_template: boolean;
        paper_cash?: number | null;
        paper_positions?: OpenPositionRecord[] | null;
        paper_trades?: CompletedTradeRecord[] | null;
    };
    const isOwner = row.user_id === userId;
    if (!isOwner && !row.is_public && !row.is_template) {
        throw new Error('Unauthorized: cannot view this recipe portfolio');
    }

    const [{ data: runRows }, quotaRes] = await Promise.all([
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
        isOwner
            ? db
                  .from('recipe_user_quotas')
                  .select('last_turbo_et_date')
                  .eq('user_id', userId)
                  .limit(1)
            : Promise.resolve({ data: [] as Array<{ last_turbo_et_date?: string | null }> }),
    ]);

    const todayEt = getEtDateString(new Date());
    const quotaRow = Array.isArray(quotaRes.data) ? quotaRes.data[0] : null;
    const turboUsedToday = Boolean(
        isOwner &&
            quotaRow &&
            (quotaRow as { last_turbo_et_date?: string | null }).last_turbo_et_date === todayEt,
    );

    const recentLiveRuns = (runRows || []) as RecipeJobRecord[];
    const rawPositions = Array.isArray(row.paper_positions) ? row.paper_positions : [];
    const latestPrices = await collectLatestMarkPrices(db, rawPositions, recentLiveRuns);

    const cash = Number(row.paper_cash ?? 10000);
    const openPositions = enrichLiveOpenPositions(rawPositions, latestPrices);
    const holdingsVal = openPositions.reduce(
        (sum, p) => sum + Number(p.shares || 0) * Number(p.current_price ?? p.entry_price ?? 0),
        0,
    );

    return {
        portfolio: {
            cash: Number(cash.toFixed(2)),
            total_equity: Number((cash + holdingsVal).toFixed(2)),
            open_positions: openPositions,
            trades: Array.isArray(row.paper_trades) ? row.paper_trades : [],
        },
        recentLiveRuns,
        liveMeta: {
            recipeName: row.name ?? '',
            isLive: Boolean(row.is_live),
            isOwner,
            turboExpiresAt: row.turbo_expires_at ?? null,
            turboUsedToday,
        },
    };
}

export const fetchLivePortfolioAndRunsFn = createServerFn({ method: 'GET' })
    .validator((d: { recipeId: string }) => d)
    .handler(async ({ data: { recipeId } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        if (!user?.id) throw new Error('Unauthorized: please sign in to inspect live portfolios');
        return fetchLivePortfolioAndRuns(recipeId, user.id);
    });
