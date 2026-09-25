import { Badge, Card } from '@llm-market-bench/ui-design-system';
import type * as React from 'react';

interface StrategyExplainerProps {
    ownerId: string;
}

interface ExplainerConfig {
    emoji: string;
    title: string;
    badgeText: string;
    badgeColorScheme: 'success' | 'info' | 'warning' | 'accent';
    subtitle: string;
    borderColor: string;
    bgColor: string;
    gridColsClass?: string;
    pillars: Array<{
        title: string;
        description: React.ReactNode;
    }>;
}

const STRATEGY_CONFIGS: Record<string, ExplainerConfig> = {
    'sys-future-forces': {
        emoji: '🔮',
        title: 'Multi-Horizon Thematic Forces & Forward Catalysts',
        badgeText: '2 to 24 Months Horizon',
        badgeColorScheme: 'accent',
        subtitle:
            'Autonomous thematic portfolio exploiting unpriced forces across geopolitics, government agendas, AI attack surfaces, and sleeper moats.',
        borderColor: 'border-purple-500/20',
        bgColor: 'bg-purple-950/10',
        gridColsClass: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4',
        pillars: [
            {
                title: '🌐 7 Canonical Archetypes',
                description:
                    'Captures geopolitical chokepoints (Hormuz/Iran oil), government priorities (DoD/Replicator defense mass), sleeping giants (Google valuation reconnection), AI attack surface toll roads (CRWD/NET), and mega-events (2026 World Cup).',
            },
            {
                title: '⏳ 2 to 24 Month Floor',
                description:
                    'Minimum 60-day horizon filters out intraday/weekly headline chop, giving corporate earnings cycles, statutory appropriations, and real-world supply bottlenecks time to reflect in fundamentals.',
            },
            {
                title: '🛑 Adversarial Luna Sentinel',
                description:
                    'Daily headline monitoring powered by OpenAI Luna (gpt-5.6-luna) with thinking. If explicit thesis invalidation criteria are satisfied, positions are flagged for immediate liquidation.',
            },
            {
                title: '⚡ Live Market Hours & Alpaca Audit',
                description:
                    'Zero out-of-market fills and zero retroactive backfilling. Liquidations occur strictly during regular market hours (9:30–16:00 ET) and mirror to Alpaca paper broker for third-party verification.',
            },
        ],
    },
    'sys-smid-quality-compounder': {
        emoji: '🌱',
        title: 'Small/Mid-Cap Quality Compounder Strategy',
        badgeText: 'Zero-Ceiling Invariant',
        badgeColorScheme: 'success',
        subtitle:
            'Overcoming the Russell 2000 reconstitution bleed via quality filtering and multi-bagger retention.',
        borderColor: 'border-emerald-500/20',
        bgColor: 'bg-emerald-950/10',
        gridColsClass: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4',
        pillars: [
            {
                title: '📚 Academic Thesis',
                description: (
                    <>
                        Grounded in Asness et al. (2018){' '}
                        <em>"Size Matters, If You Control Your Junk"</em> and Chen, Noronha, &
                        Singal (2006). Eliminates the ~1.8% annual Russell reconstitution
                        front-running loss and weeds out unprofitable zombies.
                    </>
                ),
            },
            {
                title: '🎯 Entry Screen ($1B–$10B)',
                description:
                    'S&P 600 rule: 4 quarters positive GAAP Net Income + positive Free Cash Flow + ROIC > 10% + top quintile 12-month relative momentum. Target portfolio of 25 to 30 concentrated compounders.',
            },
            {
                title: '🚀 The Zero-Ceiling Rule',
                description: (
                    <>
                        When a holding grows into a large cap ($20B, $50B, $100B+), it is{' '}
                        <strong>never sold for size reasons</strong>. Bessembinder (2018) showed
                        that 4% of stocks generate all net market wealth; multi-baggers ride
                        indefinitely.
                    </>
                ),
            },
            {
                title: '🛑 Strict Exit Discipline',
                description:
                    'Positions are only liquidated if fundamentals break: trailing 12-month net income turns negative, 2 consecutive quarters of negative cash flow, or debt leverage spikes. Rebalances quarterly following SEC 10-Q deadlines.',
            },
        ],
    },
    'sys-frontier-tech': {
        emoji: '⚛️',
        title: 'Frontier Tech Supercycle Strategy',
        badgeText: '5-Point Rubric & Power-Law',
        badgeColorScheme: 'accent',
        subtitle:
            'Identifying pre-explosion technological gestations and accumulating small-cap pure plays before mainstream market mania.',
        borderColor: 'border-violet-500/20',
        bgColor: 'bg-violet-950/10',
        gridColsClass: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4',
        pillars: [
            {
                title: '🔬 5-Point Supercycle Rubric',
                description:
                    'Qualifies themes satisfying >= 3 of 5 criteria: cost deflation/scaling law, pure-play enabler bottleneck, talent migration, regulatory catalyst, and early pilot contracts.',
            },
            {
                title: '🛡️ Small-Cap Guardrails',
                description:
                    'Major US exchanges only (NASDAQ, NYSE, AMEX), minimum $100M market cap, and $1M daily trading volume to weed out illiquid penny stocks.',
            },
            {
                title: '🛑 Anti-Overpaying & Runway',
                description:
                    'Requires at least 18 months of cash runway (cash / burn) and strictly rejects stocks trading > 150% of their 200-day moving average to avoid buying the top of retail hype.',
            },
            {
                title: '🚀 Venture Power-Law Sizing',
                description:
                    'Allocates 2% to 4% stakes per stock across 5-8 themes. Zero tight stop-losses; holds through multi-year volatility, exiting only on fundamental thesis death.',
            },
        ],
    },
    'sys-sector-ls-consensus': {
        emoji: '⚖️',
        title: 'Weekly Sector Long/Short Consensus Strategy',
        badgeText: 'Market Neutral Tilt',
        badgeColorScheme: 'info',
        subtitle:
            'Mechanical sector rotation allocating 50% long to predicted best sectors and 50% short to predicted worst sectors.',
        borderColor: 'border-blue-500/20',
        bgColor: 'bg-blue-950/10',
        pillars: [
            {
                title: '📊 Consensus Signal',
                description:
                    'Aggregates weekly predictions from multi-model sector arenas across major US sector ETFs (XLE, XLF, XLK, XLI, XLP, XLY, XLU, XLV, XLB, XLC, XBI, XOP).',
            },
            {
                title: '⚔️ Conflict Netting',
                description:
                    'If any ETF appears simultaneously in both the predicted best and predicted worst sets across different models, it is netted out and dropped from both sides.',
            },
            {
                title: '⏱️ Disciplined Cadence',
                description:
                    'Positions are entered at Monday 9:30 AM ET open with 5 bps slippage and closed at Friday 4:00 PM ET close, with zero weekend overnight risk.',
            },
        ],
    },
    'sys-sector-ls-30d': {
        emoji: '📅',
        title: '30-Day Sector Long/Short Consensus Strategy',
        badgeText: 'Monthly Horizon',
        badgeColorScheme: 'info',
        subtitle:
            'Systematic multi-week sector allocation holding 50% long in consensus 30d top sectors and 50% short in 30d worst sectors.',
        borderColor: 'border-cyan-500/20',
        bgColor: 'bg-cyan-950/10',
        pillars: [
            {
                title: '📊 30-Day Multi-Model Consensus',
                description:
                    'Synthesizes 30-day forward sector ETF projections across DeepSeek, MiniMax, Gemini, and GPT inference arenas.',
            },
            {
                title: '⚔️ Conflict Cancellation',
                description:
                    'Tickers predicted simultaneously as both top and bottom performers across models are neutralized to avoid contradictory exposure.',
            },
            {
                title: '⏱️ Discrete 30-Day Holding',
                description:
                    'Positions are held across the full 30-day forecast window, capturing medium-term macroeconomic shifts and momentum drift.',
            },
        ],
    },
    'sys-sector-ls-90d': {
        emoji: '🏛️',
        title: '90-Day Sector Long/Short Consensus Strategy',
        badgeText: 'Quarterly Horizon',
        badgeColorScheme: 'accent',
        subtitle:
            'Quarterly macroeconomic sector dispersion strategy holding 50% long and 50% short across 90-day multi-model consensus predictions.',
        borderColor: 'border-indigo-500/20',
        bgColor: 'bg-indigo-950/10',
        pillars: [
            {
                title: '📈 Quarterly Macro Consensus',
                description:
                    'Aggregates 90-day forward outlooks from multi-model sector predictors, identifying structural quarterly sector rotations.',
            },
            {
                title: '⚔️ Factor Neutral Netting',
                description:
                    'Eliminates cross-model disagreements by dropping disputed sectors from both long and short buckets.',
            },
            {
                title: '⏱️ 90-Day Holding Horizon',
                description:
                    'Holds positions across the complete 90-day cycle to isolate multi-month earnings and monetary policy dispersion.',
            },
        ],
    },
    'sys-sector-uncorr-20d': {
        emoji: '🛡️',
        title: '20-Day Uncorrelated Sector Momentum',
        badgeText: 'Low-Beta Barbell',
        badgeColorScheme: 'success',
        subtitle:
            'Systematic weekly rotation selecting the top-performing pair of US sector ETFs with rolling 90-day correlation |ρ| < 0.30 and trailing 20-day returns.',
        borderColor: 'border-emerald-500/20',
        bgColor: 'bg-emerald-950/10',
        pillars: [
            {
                title: '🛡️ Uncorrelated Filter',
                description:
                    'Requires pairwise Pearson correlation |ρ| < 0.30 over 90 days, eliminating single-factor concentration and significantly dampening max drawdowns.',
            },
            {
                title: '📈 20-Day Momentum',
                description:
                    'Evaluates trailing 20-day (~1 month) returns to filter out 1-week whipsaws and ride persistent institutional sector rotations.',
            },
            {
                title: '⚖️ 50/50 Execution',
                description:
                    'Rebalances 50% capital into each ETF at Monday open and liquidates at Friday close with 5 bps execution friction.',
            },
        ],
    },
    'sys-sector-uncorr-7d': {
        emoji: '⚡',
        title: '7-Day Uncorrelated Sector Momentum',
        badgeText: 'Rapid Rotation',
        badgeColorScheme: 'info',
        subtitle:
            'Weekly rebalance selecting the top uncorrelated sector ETF pair (|ρ| < 0.30) based on trailing 7-day returns.',
        borderColor: 'border-teal-500/20',
        bgColor: 'bg-teal-950/10',
        pillars: [
            {
                title: '⚡ Weekly Pulse',
                description:
                    'Directly tracks the Sunday correlation matrix snapshot and the Uncorrelated Pairs with Positive Momentum screener.',
            },
            {
                title: '🛡️ Low-Beta Pairing',
                description:
                    'Constrains assets to |ρ| < 0.30, forcing the portfolio to pick independent rallies rather than concentrated factor bets.',
            },
            {
                title: '⚖️ 50/50 Allocation',
                description:
                    'Equal capital split between both ETFs entered at Monday open and liquidated at Friday close.',
            },
        ],
    },
    'sys-sector-naive-momentum': {
        emoji: '🚀',
        title: '20-Day Unconstrained Momentum',
        badgeText: 'Control Benchmark',
        badgeColorScheme: 'accent',
        subtitle:
            'Benchmark control holding the top 2 highest-returning sectors over the past 20 days regardless of pairwise correlation.',
        borderColor: 'border-purple-500/20',
        bgColor: 'bg-purple-950/10',
        pillars: [
            {
                title: '🚀 Maximum Beta Momentum',
                description:
                    'Selects top 2 winners unconstrained by correlation, allowing concentration in surging high-beta clusters (e.g. XLK + SMH).',
            },
            {
                title: '🔬 Scientific Control',
                description:
                    'Provides a direct baseline to quantify the exact risk-adjusted alpha provided by correlation filters versus raw momentum.',
            },
            {
                title: '⚖️ 50/50 Weekly Split',
                description:
                    'Equal weight across both top winners, rebalanced weekly with 5 bps friction.',
            },
        ],
    },
    'sys-sector-mean-reversion': {
        emoji: '🔄',
        title: '7-Day Sector Mean Reversion',
        badgeText: 'Contrarian Bounce',
        badgeColorScheme: 'warning',
        subtitle:
            'Systematic contrarian strategy buying the bottom 2 worst-performing sector ETFs of the prior week to capture oversold mean-reversion bounces.',
        borderColor: 'border-amber-500/20',
        bgColor: 'bg-amber-950/10',
        pillars: [
            {
                title: '🔄 Oversold Rebound',
                description:
                    'Exploits the short-term 1-week overreaction anomaly where heavily dumped sectors consistently bounce the following week.',
            },
            {
                title: '📉 Bottom 2 Selection',
                description:
                    'Systematically selects the 2 sector ETFs with the lowest trailing 7-day returns across the US sector universe.',
            },
            {
                title: '⚖️ 50/50 Weekly Holding',
                description: 'Equal weight entered at Monday open and liquidated at Friday close.',
            },
        ],
    },
};

const DAILY_SPY_CONFIG: ExplainerConfig = {
    emoji: '⚡',
    title: 'Daily S&P 500 Intraday Trader',
    badgeText: 'Intraday 100% Equity',
    badgeColorScheme: 'warning',
    subtitle:
        'Systematic day trading on SPY executing at 9:30 AM ET open with profit target limit orders and 3:30 PM time exits.',
    borderColor: 'border-amber-500/20',
    bgColor: 'bg-amber-950/10',
    pillars: [
        {
            title: '🎯 Profit Target Exit',
            description:
                'If intraday high/low touches the expected return percentage during regular trading hours, position closes immediately at the profit target price.',
        },
        {
            title: '⏱️ Time Exit Fallback',
            description:
                'If profit target is not reached during regular trading hours, position closes systematically at 3:30 PM ET price to avoid overnight gap risk.',
        },
        {
            title: '⛽ Zero Leverage / Slippage',
            description:
                'Allocates 100% available cash per session with 5 bps slippage modeling on both entry and exit legs.',
        },
    ],
};

const DAILY_SPY_CLOSE_CONFIG: ExplainerConfig = {
    emoji: '🕒',
    title: 'Daily S&P 500 Close Trader (3:50 PM Exit)',
    badgeText: 'Hold-to-Close 100% Equity',
    badgeColorScheme: 'warning',
    subtitle:
        'Systematic day trading on SPY executing at 9:30 AM ET open and holding until 3:50 PM ET close without intraday profit target exits.',
    borderColor: 'border-amber-500/20',
    bgColor: 'bg-amber-950/10',
    pillars: [
        {
            title: '⏱️ 3:50 PM Close Exit',
            description:
                'Position is held until 3:50 PM session close, avoiding premature intraday profit taking and capturing full-session trend continuation.',
        },
        {
            title: '📈 Full-Session Capture',
            description:
                'Disregards intraday price target touchpoints, riding entire morning and afternoon market trends to the closing bell.',
        },
        {
            title: '⛽ 0.02% Liquid Friction',
            description:
                'Allocates 100% available cash per session with ultra-tight 0.02% (2 bps) slippage reflecting SPY deep market liquidity.',
        },
    ],
};

function ExplainerCard({ config }: { config: ExplainerConfig }) {
    return (
        <Card
            variant="glass"
            padding="md"
            className={`border ${config.borderColor} ${config.bgColor}`}
        >
            <div className="flex items-center gap-2.5">
                <span className="text-xl">{config.emoji}</span>
                <div>
                    <h3 className="text-base font-bold text-zinc-900 dark:text-white flex items-center gap-2">
                        {config.title}
                        <Badge variant="glass" size="xs" colorScheme={config.badgeColorScheme}>
                            {config.badgeText}
                        </Badge>
                    </h3>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400">{config.subtitle}</p>
                </div>
            </div>

            <div
                className={`mt-4 pt-4 border-t border-zinc-200/20 dark:border-zinc-800 grid ${
                    config.gridColsClass ?? 'grid-cols-1 md:grid-cols-3'
                } gap-4 text-xs`}
            >
                {config.pillars.map((p) => (
                    <div
                        key={p.title}
                        className="space-y-1.5 p-3 rounded-lg bg-zinc-100/50 dark:bg-zinc-900/50"
                    >
                        <span className="font-semibold text-zinc-700 dark:text-zinc-200 flex items-center gap-1.5">
                            {p.title}
                        </span>
                        <div className="text-zinc-600 dark:text-zinc-400 leading-relaxed">
                            {p.description}
                        </div>
                    </div>
                ))}
            </div>
        </Card>
    );
}

export function StrategyExplainer({ ownerId }: StrategyExplainerProps) {
    const config =
        STRATEGY_CONFIGS[ownerId] ??
        (ownerId.startsWith('sys-daily-spy-close-')
            ? DAILY_SPY_CLOSE_CONFIG
            : ownerId.startsWith('sys-daily-spy-')
              ? DAILY_SPY_CONFIG
              : null);

    if (!config) {
        return null;
    }

    return <ExplainerCard config={config} />;
}
