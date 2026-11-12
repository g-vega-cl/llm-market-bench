import type { RecipeGraph } from './types';

export const STARTER_RECIPES: RecipeGraph[] = [
    {
        name: 'NVDA Semiconductor VWAP Momentum',
        description:
            'Scalps high-volume semiconductor headlines when price confirms above session VWAP.',
        cadence: '5m',
        concurrency: {
            max_open_trades: 2,
            max_equity_pct_per_trade: 50.0,
        },
        nodes: [
            {
                id: 'news-1',
                type: 'news_source',
                title: 'Semiconductor Headlines',
                config: {
                    bucket: 'semiconductors',
                    tickers: ['NVDA', 'AMD', 'TSM', 'AVGO'],
                    lookback_hours: 24,
                },
            },
            {
                id: 'tech-1',
                type: 'technical_gate',
                title: 'VWAP & RSI Filter',
                config: {
                    conditions: [
                        { metric: 'price', operator: '>', target: 'vwap' },
                        { metric: 'rsi_14', operator: '<', target: 65.0 },
                    ],
                },
            },
            {
                id: 'llm-1',
                type: 'classification',
                title: 'Jev Catalyst Classifier',
                config: {
                    model: '~typesafe/jev-latest',
                    target_choice: 'BULLISH',
                    min_confidence: 70.0,
                },
            },
            {
                id: 'risk-1',
                type: 'risk_output',
                title: 'Risk Guardrails',
                config: {
                    action: 'BUY',
                    stop_loss_pct: 1.5,
                    target_profit_pct: 3.0,
                    max_hold_bars: 12,
                    exit_on_session_close: true,
                },
            },
        ],
        edges: [
            { from: 'news-1', to: 'tech-1' },
            { from: 'tech-1', to: 'llm-1' },
            { from: 'llm-1', to: 'risk-1' },
        ],
    },
    {
        name: 'SPY Macro Fed Rates Gate',
        description:
            'Filters Fed policy and CPI inflation headlines, requiring technical RSI pullback.',
        cadence: '5m',
        concurrency: {
            max_open_trades: 1,
            max_equity_pct_per_trade: 100.0,
        },
        nodes: [
            {
                id: 'news-fed',
                type: 'news_source',
                title: 'Fed & Macro Rates Feed',
                config: {
                    bucket: 'fed_rates',
                    tickers: ['SPY', 'QQQ', 'TLT'],
                    lookback_hours: 48,
                },
            },
            {
                id: 'tech-fed',
                type: 'technical_gate',
                title: 'Oversold Pullback Gate',
                config: {
                    conditions: [{ metric: 'rsi_14', operator: '<', target: 35.0 }],
                },
            },
            {
                id: 'analyst-fed',
                type: 'generative_analyst',
                title: 'Strata Macro Reasoner',
                config: {
                    model: 'auto-strata',
                    system_prompt:
                        'Analyze FOMC rate commentary and evaluate whether policy easing or hawkish pause is favored.',
                },
            },
            {
                id: 'risk-fed',
                type: 'risk_output',
                title: 'Macro Sizing',
                config: {
                    action: 'BUY',
                    stop_loss_pct: 1.0,
                    target_profit_pct: 2.0,
                    max_hold_bars: 24,
                    exit_on_session_close: true,
                },
            },
        ],
        edges: [
            { from: 'news-fed', to: 'tech-fed' },
            { from: 'tech-fed', to: 'analyst-fed' },
            { from: 'analyst-fed', to: 'risk-fed' },
        ],
    },
    {
        name: 'Tech SMA Trend Following',
        description:
            'Pure trend alignment trading moving average golden crosses during market hours.',
        cadence: '1d',
        concurrency: {
            max_open_trades: 3,
            max_equity_pct_per_trade: 33.3,
        },
        nodes: [
            {
                id: 'tape-tech',
                type: 'price_tape',
                title: 'Daily Market Tape',
                config: {
                    ticker: 'QQQ',
                    cadence: '1d',
                },
            },
            {
                id: 'tech-sma',
                type: 'technical_gate',
                title: 'SMA-20 > SMA-50 Gate',
                config: {
                    conditions: [
                        { metric: 'sma_20', operator: '>', target: 'sma_50' },
                        { metric: 'price', operator: '>', target: 'sma_20' },
                    ],
                },
            },
            {
                id: 'risk-sma',
                type: 'risk_output',
                title: 'Multi-Day Swing Risk',
                config: {
                    action: 'BUY',
                    stop_loss_pct: 3.0,
                    target_profit_pct: 7.0,
                    max_hold_bars: 10,
                    exit_on_session_close: false,
                },
            },
        ],
        edges: [
            { from: 'tape-tech', to: 'tech-sma' },
            { from: 'tech-sma', to: 'risk-sma' },
        ],
    },
    {
        name: 'Earnings Guidance Drift',
        description: 'Catches post-earnings guidance beat news confirmed by relative volume surge.',
        cadence: '5m',
        concurrency: {
            max_open_trades: 2,
            max_equity_pct_per_trade: 50.0,
        },
        nodes: [
            {
                id: 'news-earn',
                type: 'news_source',
                title: 'Earnings Beat Wire',
                config: {
                    bucket: 'earnings',
                    lookback_hours: 12,
                },
            },
            {
                id: 'tech-rvol',
                type: 'technical_gate',
                title: 'RVOL Volume Surge Filter',
                config: {
                    conditions: [
                        { metric: 'rvol', operator: '>=', target: 1.5 },
                        { metric: 'price', operator: '>', target: 'vwap' },
                    ],
                },
            },
            {
                id: 'llm-earn',
                type: 'classification',
                title: 'Guidance Beat Classifier',
                config: {
                    model: '~typesafe/jev-latest',
                    target_choice: 'BULLISH',
                    min_confidence: 75.0,
                },
            },
            {
                id: 'risk-earn',
                type: 'risk_output',
                title: 'Earnings Drift Target',
                config: {
                    action: 'BUY',
                    stop_loss_pct: 2.0,
                    target_profit_pct: 4.5,
                    max_hold_bars: 18,
                    exit_on_session_close: true,
                },
            },
        ],
        edges: [
            { from: 'news-earn', to: 'tech-rvol' },
            { from: 'tech-rvol', to: 'llm-earn' },
            { from: 'llm-earn', to: 'risk-earn' },
        ],
    },
];
