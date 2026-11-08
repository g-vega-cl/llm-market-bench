import { createServerFn } from '@tanstack/react-start';
import { formatEasternTime } from '~/utils/date';
import type { LiveAgentState } from '../components/LiveAgentConsole';
import type { CandlestickBar, ChartTradeMarker } from '../components/SPYCandlestickChart';

export interface LiveTraderPortfolioSummary {
    owner_id?: string;
    portfolio_id?: string;
    total_equity: number;
    cash_balance: number;
    position_shares: number;
    position_cost_basis: number;
    position_market_value: number;
    unrealized_pnl: number;
    realized_pnl: number;
    signal?: string;
    shares?: number;
    status?: string;
}

export interface MarketFeelingRecord {
    market_direction?: string | null;
    why_explanation?: string | null;
    sentiment_label?: string | null;
    sentiment_emoji?: string | null;
    confidence_score?: number | null;
    primary_concern?: string | null;
    secondary_concern?: string | null;
    model_used?: string | null;
    created_at?: string | null;
    trades_summary?: unknown;
}

export interface IntradayPayload {
    buys?: number;
    sells?: number;
    action?: 'BUY' | 'SELL' | 'HOLD';
    technicals?: { vwap: number; rsi_14: number; trend: string };
    memories_consulted?: string[];
    bars?: CandlestickBar[];
    portfolio?: LiveTraderPortfolioSummary;
}

export function filterLastBars(
    bars: CandlestickBar[] | null | undefined,
    maxBars = 60,
): CandlestickBar[] {
    if (!bars || !Array.isArray(bars)) return [];
    return bars.slice(-maxBars);
}

export function mergeIncomingBar(
    currentBars: CandlestickBar[] | null | undefined,
    incomingBar: CandlestickBar | null | undefined,
    maxBars = 60,
): CandlestickBar[] {
    if (!incomingBar) return currentBars ? [...currentBars] : [];
    if (!currentBars || currentBars.length === 0) return [incomingBar];

    const last = currentBars[currentBars.length - 1];

    // Same minute: mutate/update forming candle in place
    if (incomingBar.time === last.time) {
        const updated: CandlestickBar = {
            time: last.time,
            open: last.open,
            high: Math.max(last.high, incomingBar.high),
            low: Math.min(last.low, incomingBar.low),
            close: incomingBar.close,
            volume: Math.max(last.volume, incomingBar.volume),
        };
        return [...currentBars.slice(0, -1), updated];
    }

    // New minute: roll over, append, and maintain maxBars window
    if (incomingBar.time > last.time) {
        return filterLastBars([...currentBars, incomingBar], maxBars);
    }

    // Stale or older timestamp: keep existing tape
    return [...currentBars];
}

export function isRegularMarketHours(date = new Date()): boolean {
    const utcHours = date.getUTCHours();
    const utcMinutes = date.getUTCMinutes();
    const day = date.getUTCDay();

    // Weekend check (0 is Sunday, 6 is Saturday)
    if (day === 0 || day === 6) return false;

    // US regular market hours: 14:30 UTC to 21:00 UTC (9:30 AM to 4:00 PM ET)
    const totalMinutes = utcHours * 60 + utcMinutes;
    return totalMinutes >= 870 && totalMinutes < 1260;
}

export function buildAgentState(
    feeling: MarketFeelingRecord | null,
    payload: IntradayPayload | null,
): LiveAgentState {
    const rawAction = payload?.action;
    const action = rawAction || ((payload?.buys ?? 0) > (payload?.sells ?? 0) ? 'BUY' : 'HOLD');

    return {
        action: action as 'BUY' | 'SELL' | 'HOLD',
        conviction: feeling?.confidence_score ?? 75,
        thought: feeling?.why_explanation || 'Scanning intraday tape and evaluating risk.',
        marketDirection:
            (feeling?.market_direction as 'BULLISH' | 'BEARISH' | 'NEUTRAL') || 'NEUTRAL',
        sentimentLabel: feeling?.sentiment_label || 'Active Surveillance',
        modelUsed: feeling?.model_used || 'Strata Orca',
        lastUpdated: feeling?.created_at ? formatEasternTime(feeling.created_at) : undefined,
        timestamp: feeling?.created_at || undefined,
        technicals: payload?.technicals,
        memoriesConsulted:
            payload?.memories_consulted ||
            (feeling?.primary_concern ? [feeling.primary_concern] : []),
        portfolio: payload?.portfolio,
    };
}

export async function fetchLatestIntradayBars(
    marketFeeling: MarketFeelingRecord | null,
): Promise<CandlestickBar[]> {
    const directPayload = (marketFeeling?.trades_summary as IntradayPayload | null) ?? null;
    const directBars = filterLastBars(directPayload?.bars, 60);
    if (directBars.length > 0) return directBars;

    try {
        const { getDbServerClient } = await import('~/lib/db');
        const supabase = getDbServerClient();
        const { data } = await supabase
            .from('market_feeling')
            .select('trades_summary')
            .not('trades_summary->bars', 'is', null)
            .order('created_at', { ascending: false })
            .limit(1);

        const fallbackPayload = data?.[0]?.trades_summary as IntradayPayload | null;
        return filterLastBars(fallbackPayload?.bars, 60);
    } catch {
        return [];
    }
}

export interface LiveTapeSnapshot {
    bars: CandlestickBar[];
    agentState: LiveAgentState | null;
    isMarketOpen: boolean;
}

export const fetchLiveIntradayTape = createServerFn({ method: 'GET' }).handler(
    async (): Promise<LiveTapeSnapshot> => {
        try {
            const { getDbServerClient } = await import('~/lib/db');
            const supabase = getDbServerClient();
            const { data } = await supabase
                .from('market_feeling')
                .select('*')
                .not('trades_summary->bars', 'is', null)
                .order('created_at', { ascending: false })
                .limit(1);

            const feeling = (data?.[0] as MarketFeelingRecord | undefined) ?? null;
            const payload = (feeling?.trades_summary as IntradayPayload | null) ?? null;
            const bars = filterLastBars(payload?.bars, 60);
            const agentState = feeling ? buildAgentState(feeling, payload) : null;

            return {
                bars,
                agentState,
                isMarketOpen: isRegularMarketHours(),
            };
        } catch {
            return {
                bars: [],
                agentState: null,
                isMarketOpen: isRegularMarketHours(),
            };
        }
    },
);

export async function fetchTodayLiveTraderTrades(
    ownerId = 'live-spy-trader',
): Promise<ChartTradeMarker[]> {
    try {
        const { getDbServerClient } = await import('~/lib/db');
        const supabase = getDbServerClient();
        const todayStr = new Date().toISOString().split('T')[0];

        const { data: portData } = await supabase
            .from('portfolios')
            .select('id')
            .eq('owner_id', ownerId)
            .limit(1);

        const portfolioId = portData?.[0]?.id;
        if (!portfolioId) return [];

        const { data: tradesData, error } = await supabase
            .from('trades')
            .select('*')
            .eq('portfolio_id', portfolioId)
            .gte('executed_at', `${todayStr}T00:00:00Z`)
            .order('executed_at', { ascending: true });

        if (error || !tradesData) return [];

        return tradesData.map((t) => ({
            time: t.executed_at,
            action: (t.signal?.toUpperCase() === 'BUY' ? 'BUY' : 'SELL') as 'BUY' | 'SELL',
            price: Number(t.price),
            shares: Number(t.quantity),
        }));
    } catch {
        return [];
    }
}
