import type {
    BacktestError,
    LivePortfolioSnapshot,
    LiveRunResult,
    RecipeSummaryItem,
    StrategyRecipeRecord,
} from '../types';

export function isQuotaLimitMessage(message: string): boolean {
    return /limit reached|queue is currently full/i.test(message);
}

/**
 * Build a BacktestError from a caught error during backtest enqueue/navigate.
 * Replaces the old buildExecutionErrorState which handled live_turn + backtest.
 */
export function buildBacktestError(params: {
    err: unknown;
    queuedBacktestJobId?: string;
}): BacktestError {
    const message = params.err instanceof Error ? params.err.message : 'Execution failed';
    if (isQuotaLimitMessage(message)) {
        console.warn('[RecipeStudio] Backtest blocked by quota:', message);
        return { kind: 'quota', message };
    }
    console.error('[RecipeStudio] Backtest failed:', params.err);
    if (params.queuedBacktestJobId) {
        return { kind: 'navigation', message, backtestJobId: params.queuedBacktestJobId };
    }
    return { kind: 'execution', message };
}

export function buildInlinePortfolio(liveRes: LiveRunResult): LivePortfolioSnapshot | null {
    const updated = liveRes.updated_portfolio;
    if (!updated) return null;
    const enrichedPositions = updated.paper_positions.map((pos) => {
        const curPx = liveRes.signal_prices?.[pos.ticker] ?? pos.current_price ?? pos.entry_price;
        const mktVal = pos.market_value ?? Number((pos.shares * curPx).toFixed(2));
        const costBasis = pos.cost_basis ?? pos.shares * pos.entry_price;
        const netLiq = mktVal * (1 - 0.0005);
        const unrPnl = pos.unrealized_pnl_net ?? netLiq - costBasis;
        const unrPct =
            pos.unrealized_return_pct ?? (costBasis > 0 ? (unrPnl / costBasis) * 100 : 0);
        return {
            ...pos,
            current_price: Number(curPx.toFixed(4)),
            market_value: mktVal,
            unrealized_pnl_net: Number(unrPnl.toFixed(2)),
            unrealized_return_pct: Number(unrPct.toFixed(2)),
        };
    });
    const holdingsVal = enrichedPositions.reduce((sum, p) => sum + Number(p.market_value ?? 0), 0);
    return {
        cash: updated.paper_cash,
        total_equity: Number((updated.paper_cash + holdingsVal).toFixed(2)),
        open_positions: enrichedPositions,
        trades: updated.paper_trades,
    };
}

export function upsertSavedRecipeSummary(
    prev: RecipeSummaryItem[],
    saved: StrategyRecipeRecord,
    isLive?: boolean,
): RecipeSummaryItem[] {
    const existing = prev.find((r) => r.id === saved.id);
    const nextLive = isLive ?? existing?.is_live ?? Boolean(saved.is_live);
    const nextTurbo = nextLive ? existing?.turbo_expires_at : null;
    if (!existing) {
        return [
            {
                id: saved.id,
                name: saved.name,
                cadence: saved.cadence,
                is_live: nextLive,
                trial_count: saved.trial_count ?? 0,
                updated_at: saved.updated_at ?? new Date().toISOString(),
                turbo_expires_at: nextTurbo ?? null,
            },
            ...prev,
        ];
    }
    return prev.map((r) =>
        r.id === saved.id
            ? {
                  ...r,
                  name: saved.name,
                  cadence: saved.cadence,
                  is_live: nextLive,
                  turbo_expires_at: nextLive ? (r.turbo_expires_at ?? null) : null,
              }
            : r,
    );
}
