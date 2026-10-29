import type { MarketBarometer } from '@llm-market-bench/database';
import {
    Badge,
    Card,
    ConfidenceBar,
    PageLayout,
    SectionHeading,
} from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';

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
    feeling: {
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

function getConfidenceColor(score: number): 'success' | 'warning' | 'danger' {
    if (score >= 70) return 'success';
    if (score >= 40) return 'warning';
    return 'danger';
}

function FeelingConcerns({
    primaryConcern,
    secondaryConcern,
}: {
    primaryConcern?: string;
    secondaryConcern?: string;
}) {
    if (!primaryConcern && !secondaryConcern) return null;
    return (
        <div className="flex flex-wrap gap-3">
            {primaryConcern && (
                <div className="voxel-trough p-3 flex-1 basis-48 min-w-0">
                    <span className="block text-xs text-boxel-muted uppercase tracking-widest font-black mb-1">
                        Primary Concern
                    </span>
                    <span className="text-xs text-danger font-bold">{primaryConcern}</span>
                </div>
            )}
            {secondaryConcern && (
                <div className="voxel-trough p-3 flex-1 basis-48 min-w-0">
                    <span className="block text-xs text-boxel-muted uppercase tracking-widest font-black mb-1">
                        Secondary Concern
                    </span>
                    <span className="text-xs text-boxel-ink font-medium">{secondaryConcern}</span>
                </div>
            )}
        </div>
    );
}

function FeelingTradesSummary({ buyCount, sellCount }: { buyCount?: number; sellCount?: number }) {
    const hasTrades =
        (buyCount !== undefined && buyCount > 0) || (sellCount !== undefined && sellCount > 0);
    if (!hasTrades) return null;
    return (
        <div className="grid grid-cols-2 gap-3">
            <div className="voxel-trough p-2.5 flex items-center justify-between">
                <span className="text-xs font-black uppercase tracking-widest text-boxel-muted">
                    LLM Buys
                </span>
                <span className="font-mono text-sm font-black text-success">{buyCount ?? 0}</span>
            </div>
            <div className="voxel-trough p-2.5 flex items-center justify-between">
                <span className="text-xs font-black uppercase tracking-widest text-boxel-muted">
                    LLM Sells
                </span>
                <span className="font-mono text-sm font-black text-danger">{sellCount ?? 0}</span>
            </div>
        </div>
    );
}

function FeelingBlock({ feeling }: { feeling: HomePageData['feeling'] }) {
    const isBullish = feeling.sentiment === 'BULLISH';
    const isBearish = feeling.sentiment === 'BEARISH';
    const badgeScheme = isBullish ? 'success' : isBearish ? 'danger' : 'accent';

    return (
        <Card
            data-testid="home-block-feeling"
            padding="md"
            className="flex-1 basis-80 min-w-0 flex flex-col gap-4"
        >
            <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b-2 border-boxel-bevel-hi">
                <SectionHeading className="text-lg">AI Market Feeling</SectionHeading>
                <Badge colorScheme={badgeScheme} variant="solid" size="sm" showDot>
                    {feeling.sentiment}
                </Badge>
            </div>

            {feeling.sentimentLabel && (
                <div className="text-xl font-black text-boxel-ink tracking-tight">
                    {feeling.sentimentLabel}
                </div>
            )}

            {feeling.confidence !== undefined && (
                <ConfidenceBar
                    label="Confidence"
                    value={feeling.confidence}
                    colorScheme={getConfidenceColor(feeling.confidence)}
                    textStyle="hero"
                    className="w-full"
                />
            )}

            <div className="voxel-trough p-3.5 text-sm leading-relaxed text-boxel-ink">
                &quot;{feeling.summary}&quot;
            </div>

            <FeelingConcerns
                primaryConcern={feeling.primaryConcern}
                secondaryConcern={feeling.secondaryConcern}
            />

            <FeelingTradesSummary buyCount={feeling.buyCount} sellCount={feeling.sellCount} />

            <div className="flex flex-wrap items-center justify-between gap-2 border-t-2 border-boxel-bevel-hi pt-3 text-xs text-boxel-muted font-mono">
                <div className="flex flex-wrap items-center gap-2">
                    {feeling.lastAnalyzed && <span>Last: {feeling.lastAnalyzed}</span>}
                    {feeling.modelUsed && <span>• Model: {feeling.modelUsed}</span>}
                </div>
                <Link
                    to="/lab"
                    className="text-accent hover:text-accent-hover font-bold uppercase tracking-wider"
                >
                    Telemetry →
                </Link>
            </div>
        </Card>
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
    return (
        <div className="min-h-screen w-full bg-boxel-canvas text-boxel-ink overflow-x-hidden">
            <PageLayout maxWidth="xl">
                <header className="mb-6 pb-4 border-b-2 border-boxel-bevel-hi flex flex-wrap items-baseline justify-between gap-4">
                    <div>
                        <h1 className="text-3xl font-black tracking-tight text-boxel-ink uppercase">
                            Market Overview
                        </h1>
                        <p className="text-xs text-boxel-muted font-mono mt-1">
                            LIVE AUTONOMOUS LLM BENCHMARK • TODAY &amp; SESSION LEADERBOARD
                        </p>
                    </div>
                </header>

                <div data-testid="dashboard" className="flex flex-wrap gap-6 items-start w-full">
                    <FeelingBlock feeling={data.feeling} />
                    <PortfoliosBlock portfolios={data.portfolios} benchmark={data.benchmark} />
                </div>
            </PageLayout>
        </div>
    );
}
