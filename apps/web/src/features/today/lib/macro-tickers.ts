/**
 * Centralized list of the 23 macro tickers tracked by the LLM Market Bench daily pipeline.
 * Categorized by asset class.
 */
export const MACRO_TICKERS = {
    Market: {
        SPY: 'S&P 500',
        QQQ: 'Nasdaq 100',
        TLT: '20+yr Treasury',
        VGK: 'Europe',
        EWJ: 'Japan',
        GLD: 'Gold',
        USO: 'Oil (WTI)',
        VIXY: 'Volatility Index',
    },
    Equities: {
        SPY: 'S&P 500',
        QQQ: 'Nasdaq 100',
        DIA: 'Dow Jones',
        IWM: 'Russell 2000',
    },
    International: {
        EWJ: 'Japan',
        EWY: 'South Korea',
        VGK: 'Europe',
        MCHI: 'China',
        EEM: 'Emerging Markets',
        EWU: 'United Kingdom',
        EWC: 'Canada',
        INDA: 'India',
    },
    Commodities: {
        GLD: 'Gold',
        SLV: 'Silver',
        CPER: 'Copper',
        USO: 'Oil (WTI)',
        UNG: 'Natural Gas',
    },
    'Bonds & Treasury Yields': {
        IEF: '7-10yr Treasury',
        TLT: '20+yr Treasury',
        TIP: 'TIPS (Inflation)',
    },
    'FX & Risk': {
        UUP: 'US Dollar Index',
        VIXY: 'Volatility Index',
    },
    Crypto: {
        BTCUSD: 'Bitcoin',
    },
} as const;

export type MacroCategory = keyof typeof MACRO_TICKERS;
export type MacroTickerSymbol = keyof (typeof MACRO_TICKERS)[MacroCategory];

// Flat array of all unique tickers for DB fetching
export const MACRO_TICKERS_LIST = Array.from(
    new Set(Object.values(MACRO_TICKERS).flatMap((cat) => Object.keys(cat))),
) as MacroTickerSymbol[];

export interface HistoricalPricePoint {
    price: number;
    fetched_at: string;
}

export interface MacroStat {
    ticker: string;
    name: string;
    category: MacroCategory;
    price: number;
    todayPctChange: number;
    stdevPct: number;
    regimeFlag: 'Normal' | '❗ UNUSUAL' | '⚠️ HIGHLY UNUSUAL';
    hasHistory: boolean;
}

/**
 * Calculates standard deviation and today's percentage change for a given ticker,
 * aligning 100% with core/macro_tracker.py calculations.
 */
export function calculateMacroStats(
    ticker: string,
    name: string,
    category: MacroCategory,
    currentPrice: number,
    history: HistoricalPricePoint[],
): MacroStat {
    if (!history || history.length < 2) {
        return {
            ticker,
            name,
            category,
            price: currentPrice,
            todayPctChange: 0,
            stdevPct: 0,
            regimeFlag: 'Normal',
            hasHistory: false,
        };
    }

    // 1. Calculate daily returns over the historical periods
    // Note: History is ordered newest-to-oldest (descending fetched_at).
    // Therefore, history[i] is today/newest, history[i+1] is yesterday/older.
    const returns: number[] = [];
    for (let i = 0; i < history.length - 1; i++) {
        const prev = Number(history[i + 1].price);
        const curr = Number(history[i].price);
        if (prev > 0) {
            returns.push((curr - prev) / prev);
        }
    }

    // 2. Today's Move (current quote vs yesterday's close)
    let yesterdayClose = Number(history[0].price);
    let todayPx = currentPrice;

    // Check if market is closed (meaning current quote price is equal to the most recent historical close price)
    // If so, today's move shifts to comparison between history[0] and history[1]
    if (Math.abs(currentPrice - Number(history[0].price)) < 0.001 && history.length > 1) {
        yesterdayClose = Number(history[1].price);
        todayPx = Number(history[0].price);
    }

    const todayPctChange =
        yesterdayClose > 0 ? ((todayPx - yesterdayClose) / yesterdayClose) * 100 : 0.0;

    // 3. Compute Standard Deviation (Rolling Volatility)
    let stdevPct = 0;
    let regimeFlag: 'Normal' | '❗ UNUSUAL' | '⚠️ HIGHLY UNUSUAL' = 'Normal';

    if (returns.length > 2) {
        const meanReturn = returns.reduce((sum, val) => sum + val, 0) / returns.length;
        const variance =
            returns.reduce((sum, val) => sum + (val - meanReturn) ** 2, 0) / (returns.length - 1);
        stdevPct = Math.sqrt(variance) * 100;

        const absChange = Math.abs(todayPctChange);
        if (absChange > 2.0 * stdevPct) {
            regimeFlag = '⚠️ HIGHLY UNUSUAL';
        } else if (absChange > 1.5 * stdevPct) {
            regimeFlag = '❗ UNUSUAL';
        }
    }

    return {
        ticker,
        name,
        category,
        price: todayPx,
        todayPctChange,
        stdevPct,
        regimeFlag,
        hasHistory: true,
    };
}
