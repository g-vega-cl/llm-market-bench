import type { MarketBarometer } from '@llm-market-bench/database';
import { Card, PageLayout, SectionHeading } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import * as React from 'react';
import { isRegularMarketHours } from '../api/fetch-intraday-tape';
import { LiveAgentConsole, type LiveAgentState } from '../components/LiveAgentConsole';
import type { CandlestickBar, ChartTradeMarker } from '../components/SPYCandlestickChart';

export interface HomePageData {
    portfolios: {
        name: string;
        todayPct: number;
        weekPct: number;
        totalEquity: number;
        isActive: boolean;
        isAutoResearch: boolean;
        isSystem?: boolean;
    }[];
    benchmark: { todayPct: number; weekPct: number };
    bars?: CandlestickBar[];
    trades?: ChartTradeMarker[];
    agentState?: LiveAgentState;
    isMarketOpen?: boolean;
    feeling?: {
        sentiment: string;
        summary: string;
        sentimentLabel?: string;
        sentimentEmoji?: string;
        confidence?: number;
        primaryConcern?: string;
        secondaryConcern?: string;
        modelUsed?: string;
        lastAnalyzed?: string;
        buyCount?: number;
        sellCount?: number;
    };
    barometer?: MarketBarometer | null;
}

function PortfolioRow({ portfolio }: { portfolio: HomePageData['portfolios'][number] }) {
    const formatMoney = (val: number) => {
        const sign = val < 0 ? '-' : '';
        return `${sign}$${Math.abs(val).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        })}`;
    };

    return (
        <tr className="hover:bg-boxel-elevated transition-colors">
            <td className="px-4 py-3 font-medium">
                <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-bold text-boxel-ink tracking-tight">
                        {portfolio.name}
                    </span>
                    <div className="flex items-center gap-2 text-xs font-mono text-boxel-muted">
                        <span className="flex items-center gap-1">
                            <span
                                className={`h-2 w-2 rounded-none ${
                                    portfolio.isActive ? 'bg-success' : 'bg-boxel-muted'
                                }`}
                            />
                            {portfolio.isActive ? 'Active' : 'Inactive'}
                        </span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                            <span
                                className={`h-2 w-2 rounded-none ${
                                    portfolio.isAutoResearch ? 'bg-accent' : 'bg-info'
                                }`}
                            />
                            {portfolio.isAutoResearch ? 'Auto-Res' : 'Manual'}
                        </span>
                    </div>
                </div>
            </td>
            <td className="px-4 py-3 text-right font-mono text-sm font-bold text-boxel-ink align-middle">
                {formatMoney(portfolio.totalEquity)}
            </td>
            <td className="px-4 py-3 text-right font-mono text-sm align-middle">
                <div className="flex flex-col items-end gap-0.5">
                    <span
                        className={`font-bold ${
                            portfolio.todayPct >= 0 ? 'text-success' : 'text-danger'
                        }`}
                    >
                        {portfolio.todayPct > 0 ? '+' : ''}
                        {portfolio.todayPct}%
                    </span>
                    <span
                        className={`text-xs ${
                            portfolio.weekPct >= 0 ? 'text-success' : 'text-danger'
                        }`}
                    >
                        {portfolio.weekPct > 0 ? '+' : ''}
                        {portfolio.weekPct}% wk
                    </span>
                </div>
            </td>
        </tr>
    );
}

function SPInlineRow({ benchmark }: { benchmark: HomePageData['benchmark'] }) {
    const spToday = benchmark.todayPct;
    const spWeek = benchmark.weekPct;

    return (
        <div className="voxel-trough flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 text-xs">
            <span className="font-black text-accent tracking-widest uppercase">
                S&P 500 Benchmark
            </span>
            <div className="flex items-center gap-4 font-mono">
                <div>
                    <span className="text-boxel-muted mr-1.5">Today</span>
                    <span
                        className={
                            spToday >= 0 ? 'text-success font-bold' : 'text-danger font-bold'
                        }
                    >
                        {spToday > 0 ? '+' : ''}
                        {spToday}%
                    </span>
                </div>
                <span className="text-boxel-bevel-hi">|</span>
                <div>
                    <span className="text-boxel-muted mr-1.5">Week</span>
                    <span
                        className={spWeek >= 0 ? 'text-success font-bold' : 'text-danger font-bold'}
                    >
                        {spWeek > 0 ? '+' : ''}
                        {spWeek}%
                    </span>
                </div>
            </div>
        </div>
    );
}

function PortfoliosBlock({
    portfolios,
    benchmark,
}: {
    portfolios: HomePageData['portfolios'];
    benchmark: HomePageData['benchmark'];
}) {
    const llmPortfolios = portfolios.filter((p) => !p.isSystem);

    return (
        <Card
            data-testid="home-block-portfolios"
            padding="md"
            className="flex-1 basis-96 min-w-0 flex flex-col gap-4"
        >
            <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b-2 border-boxel-bevel-hi">
                <SectionHeading className="text-lg">Active Agent Portfolios</SectionHeading>
                <Link
                    to="/portfolios"
                    className="voxel-btn bg-boxel-elevated text-boxel-ink hover:text-accent px-3 py-1 text-xs font-black uppercase tracking-widest"
                >
                    All Portfolios →
                </Link>
            </div>

            <SPInlineRow benchmark={benchmark} />

            <div className="voxel-trough overflow-x-auto">
                <table className="w-full border-collapse text-left text-sm">
                    <thead>
                        <tr className="border-b-2 border-boxel-bevel-hi bg-boxel-surface font-black text-boxel-muted">
                            <th className="px-4 py-2.5 text-xs uppercase tracking-wider">Model</th>
                            <th className="px-4 py-2.5 text-right text-xs uppercase tracking-wider">
                                Equity
                            </th>
                            <th className="px-4 py-2.5 text-right text-xs uppercase tracking-wider">
                                Today / Wk
                            </th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-boxel-bevel-hi/40">
                        {llmPortfolios.map((portfolio) => (
                            <PortfolioRow key={portfolio.name} portfolio={portfolio} />
                        ))}
                    </tbody>
                </table>
            </div>
        </Card>
    );
}

export function HomePage({ data }: { data: HomePageData }) {
    const bars = React.useMemo(
        () => (data.bars && data.bars.length > 0 ? data.bars.slice(-60) : []),
        [data.bars],
    );

    const agentState: LiveAgentState = data.agentState || {
        action: (data.feeling?.buyCount ?? 0) > (data.feeling?.sellCount ?? 0) ? 'BUY' : 'HOLD',
        conviction: data.feeling?.confidence ?? 75,
        thought:
            data.feeling?.summary ||
            'Scanning 120-minute intraday tape and evaluating risk parameters.',
        marketDirection:
            (data.feeling?.sentiment as 'BULLISH' | 'BEARISH' | 'NEUTRAL') || 'NEUTRAL',
        sentimentLabel: data.feeling?.sentimentLabel || 'Live Surveillance',
        modelUsed: data.feeling?.modelUsed || 'Strata Orca',
        lastUpdated: data.feeling?.lastAnalyzed || '09:30 ET',
        technicals: {
            vwap: 582.4,
            rsi_14: 54.2,
            trend: data.feeling?.sentiment || 'NEUTRAL',
        },
        memoriesConsulted: data.feeling?.primaryConcern ? [data.feeling.primaryConcern] : [],
    };

    const isMarketOpen =
        data.isMarketOpen !== undefined ? data.isMarketOpen : isRegularMarketHours();

    return (
        <div className="min-h-screen w-full bg-boxel-canvas text-boxel-ink overflow-x-hidden">
            <PageLayout maxWidth="xl">
                <header className="mb-6 pb-4 border-b-2 border-boxel-bevel-hi flex flex-wrap items-baseline justify-between gap-4">
                    <div>
                        <h1 className="text-3xl font-black tracking-tight text-boxel-ink uppercase">
                            Market Overview
                        </h1>
                        <p className="text-xs text-boxel-muted font-mono mt-1">
                            LIVE AUTONOMOUS LLM BENCHMARK • 24/7 TRADER &amp; SESSION LEADERBOARD
                        </p>
                    </div>
                </header>

                <div data-testid="dashboard" className="flex flex-wrap gap-6 items-start w-full">
                    <div
                        data-testid="home-block-feeling"
                        className="flex-1 basis-96 min-w-0 flex flex-col"
                    >
                        <LiveAgentConsole
                            bars={bars}
                            trades={data.trades}
                            agentState={agentState}
                            isMarketOpen={isMarketOpen}
                        />
                    </div>
                    <PortfoliosBlock portfolios={data.portfolios} benchmark={data.benchmark} />
                </div>
            </PageLayout>
        </div>
    );
}
