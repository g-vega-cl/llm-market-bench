export interface ActualReturns {
    [ownerId: string]: {
        startEquity: number;
        endEquity: number;
        actualReturn: number;
    };
}

export interface PortfolioDetail {
    owner_id: string;
    initial_equity?: number;
    initial_cash?: number;
    end_equity?: number;
    do_nothing_return_pct?: number;
    positions?: Record<string, unknown>;
}

export type PerformanceRow = {
    portfolio_id: string;
    total_equity: string | number;
    date: string;
    portfolios:
        | {
              owner_id: string;
          }
        | null
        | undefined;
};

export interface DailyMetrics {
    portfolioReturn: number;
    spyReturn: number;
    doNothingReturn: number;
    opportunityCost: number;
    maxDrawdown: number;
    dailyExcessReturn: number;
    dailyDrawdownPenalty: number;
    dailyScore: number;
}

export interface Checkpoint {
    day: string;
    score: number;
    portfolio: number;
    isFuture: boolean;
    dateStr?: string;
}

export const DAY_MULTIPLIERS: Record<string, number> = {
    Monday: 0.15,
    Tuesday: 0.35,
    Wednesday: 0.55,
    Thursday: 0.8,
    Friday: 1.0,
};

export function getAgentDisplayName(ownerId: string | null | undefined): string {
    if (!ownerId) return 'Unknown Agent';
    const normalized = ownerId.toLowerCase().replace(/[\s_-]+/g, '-');
    if (normalized.includes('gemini-3.5-flash-lite')) return 'Gemini 3.5 Flash Lite';
    if (normalized.includes('gemini-3.1-flash-lite')) return 'Gemini 3.1 Flash Lite';
    if (normalized.includes('deepseek-v4-pro')) return 'DeepSeek V4 Pro';
    if (normalized.includes('deepseek-v4-flash')) return 'DeepSeek V4 Flash';
    if (normalized.includes('claude-haiku-4-5')) return 'Claude Haiku 4.5';
    if (normalized.includes('gpt-5.6-luna')) return 'GPT 5.6 Luna';
    if (normalized.includes('minimax-m3') || normalized.includes('minimax')) return 'MiniMax-M3';
    return ownerId;
}

export function getPortfolioReturn(
    metrics: Record<string, number | null | undefined>,
    isActive: boolean,
    actualReturns: ActualReturns | null,
): number {
    const portfolioReturn = metrics.portfolio_return_pct;
    if (portfolioReturn !== null && portfolioReturn !== undefined) {
        return portfolioReturn;
    }
    if (isActive && actualReturns && Object.keys(actualReturns).length > 0) {
        const rets = Object.values(actualReturns).map((r) => r.actualReturn);
        return rets.reduce((sum, val) => sum + val, 0) / rets.length;
    }
    return isActive ? 1.45 : 0;
}

export function getSpyReturn(
    metrics: Record<string, number | null | undefined>,
    isActive: boolean,
    actualSpyReturn: number | null,
): number {
    if (isActive && actualSpyReturn !== null) {
        return actualSpyReturn;
    }
    const spyReturn = metrics.spy_return_pct;
    if (spyReturn !== null && spyReturn !== undefined) {
        return spyReturn;
    }
    return isActive ? 0.85 : 0;
}

export function getDoNothingReturn(
    metrics: Record<string, number | null | undefined>,
    isActive: boolean,
): number {
    const doNothingReturn = metrics.do_nothing_return_pct;
    if (doNothingReturn !== null && doNothingReturn !== undefined) {
        return doNothingReturn;
    }
    const details = (metrics.portfolio_details || {}) as Record<string, PortfolioDetail>;
    const detailEntries = Object.values(details);
    if (detailEntries.length > 0) {
        const dnReturns = detailEntries.map((d) => d.do_nothing_return_pct ?? 0);
        return dnReturns.reduce((sum, val) => sum + val, 0) / dnReturns.length;
    }
    return isActive ? 1.1 : 0;
}

export function calculateDailyMetrics(
    metrics: Record<string, number | null | undefined>,
    isActive: boolean,
    actualSpyReturn: number | null,
    actualReturns: ActualReturns | null,
): DailyMetrics {
    const portfolioReturn = getPortfolioReturn(metrics, isActive, actualReturns);
    const spyReturn = getSpyReturn(metrics, isActive, actualSpyReturn);
    const doNothingReturn = getDoNothingReturn(metrics, isActive);
    const bondReturn = metrics.bond_return_pct ?? (isActive ? 0.05 : 0);

    const opportunityCost = metrics.opportunity_cost_penalty ?? portfolioReturn - bondReturn;
    const maxDrawdown = metrics.max_drawdown ?? (isActive ? 1.25 : 0);

    const excessVsSpy = portfolioReturn - spyReturn;
    const excessVsDoNothing = portfolioReturn - doNothingReturn;
    const excessVsBond = portfolioReturn - bondReturn;

    const dailyExcessReturn = 0.4 * excessVsSpy + 0.4 * excessVsDoNothing + 0.2 * excessVsBond;
    const dailyDrawdownPenalty = maxDrawdown * 0.3;
    const dailyScore = dailyExcessReturn - dailyDrawdownPenalty;

    return {
        portfolioReturn,
        spyReturn,
        doNothingReturn,
        opportunityCost,
        maxDrawdown,
        dailyExcessReturn,
        dailyDrawdownPenalty,
        dailyScore,
    };
}

export function getCheckpoints(
    dailyScore: number,
    portfolioReturn: number,
    weekStartStr?: string,
    isActive?: boolean,
): Checkpoint[] {
    const days = [
        { name: 'Monday', multiplier: 0.15 },
        { name: 'Tuesday', multiplier: 0.35 },
        { name: 'Wednesday', multiplier: 0.55 },
        { name: 'Thursday', multiplier: 0.8 },
        { name: 'Friday', multiplier: 1.0 },
    ];

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    let startDate: Date | null = null;
    if (weekStartStr) {
        const [year, month, day] = weekStartStr.split('-').map(Number);
        startDate = new Date(year, month - 1, day);
        startDate.setHours(0, 0, 0, 0);
    }

    return days.map((d, idx) => {
        let isFuture = false;
        let dateStr = '';
        if (startDate) {
            const checkpointDate = new Date(startDate);
            checkpointDate.setDate(startDate.getDate() + idx);
            checkpointDate.setHours(0, 0, 0, 0);
            if (isActive) {
                isFuture = checkpointDate > today;
            }
            dateStr = `${checkpointDate.getMonth() + 1}/${checkpointDate.getDate()}`;
        }

        return {
            day: d.name,
            score: dailyScore * d.multiplier,
            portfolio: portfolioReturn * d.multiplier,
            isFuture,
            dateStr,
        };
    });
}

export function groupPerformanceData(data: PerformanceRow[]) {
    const grouped: Record<string, { date: string; equity: number }[]> = {};
    const ownerIdMap: Record<string, string> = {};

    for (const row of data) {
        const ownerId = row.portfolios?.owner_id;
        const pid = row.portfolio_id;
        if (!ownerId) continue;
        ownerIdMap[pid] = ownerId;
        if (!grouped[pid]) {
            grouped[pid] = [];
        }
        grouped[pid].push({
            date: row.date,
            equity: Number(row.total_equity),
        });
    }
    return { grouped, ownerIdMap };
}

export function calculateActualReturns(
    grouped: Record<string, { date: string; equity: number }[]>,
    ownerIdMap: Record<string, string>,
): ActualReturns {
    const results: ActualReturns = {};
    for (const [pid, history] of Object.entries(grouped)) {
        if (history.length < 2) continue;
        history.sort((a, b) => a.date.localeCompare(b.date));
        const startEquity = history[0].equity;
        const endEquity = history[history.length - 1].equity;
        const ownerId = ownerIdMap[pid];
        if (startEquity > 0) {
            results[ownerId] = {
                startEquity,
                endEquity,
                actualReturn: ((endEquity - startEquity) / startEquity) * 100,
            };
        }
    }
    return results;
}

export function calculateSpyReturn(prices: { price: number | string }[]): number {
    let cumulative = 1.0;
    for (let i = 1; i < prices.length; i++) {
        const prev = Number(prices[i - 1].price || 0);
        const curr = Number(prices[i].price || 0);
        if (prev > 0) {
            cumulative *= 1 + (curr - prev) / prev;
        }
    }
    return (cumulative - 1) * 100;
}

export function getProcessedActualReturns(data: unknown[]): ActualReturns {
    const { grouped, ownerIdMap } = groupPerformanceData(data as PerformanceRow[]);
    return calculateActualReturns(grouped, ownerIdMap);
}
