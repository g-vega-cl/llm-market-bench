import { getRecipeJobStatusFn } from '../api/recipes-api';
import type {
    ExecutionState,
    LivePortfolioSnapshot,
    LiveRunResult,
    RecipeSummaryItem,
    StrategyRecipeRecord,
} from '../types';

export async function pollJobResults(jobId: string): Promise<ExecutionState> {
    for (let attempts = 0; attempts < 30; attempts++) {
        await new Promise((r) => setTimeout(r, 1000));
        try {
            const res = await getRecipeJobStatusFn({ data: { jobId } });
            if (res?.status === 'completed' && res.result_json) {
                return { status: 'live_done', result: res.result_json as LiveRunResult };
            }
            if (res?.status === 'cancelled') {
                return { status: 'error', message: 'Execution was cancelled.' };
            }
            if (res?.status === 'failed') {
                return { status: 'error', message: res.error_message || 'Execution failed' };
            }
        } catch {
            // Ignore transient polling errors
        }
    }
    return {
        status: 'error',
        message:
            'Job queued — worker is still processing. Check Alerts Inbox or try again shortly.',
    };
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
    if (!existing) {
        return [
            {
                id: saved.id,
                name: saved.name,
                cadence: saved.cadence,
                is_live: nextLive,
                trial_count: saved.trial_count ?? 0,
                updated_at: saved.updated_at ?? new Date().toISOString(),
            },
            ...prev,
        ];
    }
    return prev.map((r) =>
        r.id === saved.id
            ? { ...r, name: saved.name, cadence: saved.cadence, is_live: nextLive }
            : r,
    );
}
