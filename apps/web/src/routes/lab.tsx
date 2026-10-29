import type { Portfolio } from '@llm-market-bench/database';
import { Badge, Card, PageLayout, SectionHeading } from '@llm-market-bench/ui-design-system';
import { createFileRoute, Link } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import { fetchPortfolios } from '~/features/portfolios/api/fetch-portfolios';
import { seo } from '~/lib/seo';

export interface LabLinkItem {
    to: string;
    label: string;
    description: string;
}

export interface LabCategory {
    id: string;
    title: string;
    subtitle: string;
    items: LabLinkItem[];
}

export const LAB_CATEGORIES: LabCategory[] = [
    {
        id: 'research-engines',
        title: 'Research & Prediction Engines',
        subtitle: 'Autonomous prompt evolution, backtest harnesses, and sector forecasting',
        items: [
            {
                to: '/autoresearch',
                label: 'Auto-Research',
                description:
                    'Double-ratchet tournament loop where LLMs mutate and test trading prompts.',
            },
            {
                to: '/daily-predictions',
                label: 'Daily Predictor',
                description: 'Next-session S&P 500 directional forecasts and calibration scoring.',
            },
            {
                to: '/ai-predictions',
                label: 'AI Sector Predictions',
                description:
                    'Multi-horizon conviction calls on semiconductor and AI infrastructure tickers.',
            },
            {
                to: '/autoresearch-backtest',
                label: 'Backtests',
                description:
                    'Historical replay telemetry for prompt blocks and tournament generations.',
            },
            {
                to: '/daily-predictions-backtest',
                label: 'Daily Backtest',
                description: 'Walk-forward validation of daily market direction predictors.',
            },
            {
                to: '/renko',
                label: 'LIN Renko Agent',
                description: 'Brick-based momentum and noise-filtered price action sandbox.',
            },
        ],
    },
    {
        id: 'cognition-telemetry',
        title: 'Cognition & Market Telemetry',
        subtitle: 'Episodic memory banks, decision traces, concept graphs, and dispatches',
        items: [
            {
                to: '/memories',
                label: 'Memories',
                description:
                    'Episodic lessons, macro events, and post-trade reflections stored by agents.',
            },
            {
                to: '/reasoning',
                label: 'Reasoning',
                description:
                    'Step-by-step tool calls and chain-of-thought logs from pre-market sessions.',
            },
            {
                to: '/concepts',
                label: 'Concepts',
                description:
                    'Semantic cluster map of macro themes and recurring market narratives.',
            },
            {
                to: '/cause-and-effect',
                label: 'Cause & Effect',
                description:
                    'Causal attribution chains linking macro catalysts to portfolio trades.',
            },
            {
                to: '/generated-newsletters',
                label: 'Newsletters',
                description:
                    'Synthesized daily market dispatches and morning intelligence briefings.',
            },
            {
                to: '/chat',
                label: 'AI Chat Gateway',
                description:
                    'Interactive terminal for querying agent memories and live portfolio state.',
            },
        ],
    },
    {
        id: 'audits-archives',
        title: 'Audits, Benchmarks & Retired Archives',
        subtitle: 'Execution verification, regime barometers, methodology, and retired models',
        items: [
            {
                to: '/leaderboard',
                label: 'Leaderboard',
                description:
                    'Full comparative rankings across Sharpe, drawdown, and win-rate metrics.',
            },
            {
                to: '/market-overview',
                label: 'Market Overview',
                description:
                    'Cross-asset macro indicators, sector breadth, and volatility telemetry.',
            },
            {
                to: '/barometer-audit',
                label: 'Barometer Audit',
                description: 'Historical S&P 500 regime classification and breadth audit trail.',
            },
            {
                to: '/audits',
                label: 'Audits',
                description:
                    'System integrity checks, execution slippage logs, and pipeline health.',
            },
            {
                to: '/how-it-works',
                label: 'How it Works',
                description:
                    'Architectural overview of the autonomous benchmark and capital rules.',
            },
        ],
    },
];

const getRetiredPortfolios = createServerFn({ method: 'GET' }).handler(async () => {
    const portfolios = await fetchPortfolios().catch(() => []);
    return portfolios.filter((p) => !p.is_active);
});

export const Route = createFileRoute('/lab')({
    loader: async () => {
        const retiredPortfolios = await getRetiredPortfolios();
        return { retiredPortfolios };
    },
    head: () => ({
        meta: [
            ...seo({
                title: 'Lab Directory | Benchify',
                description:
                    'Index of experimental research modules, telemetry views, audits, and retired agent portfolios.',
            }),
        ],
    }),
    component: LabRouteComponent,
});

function LabRouteComponent() {
    const { retiredPortfolios } = Route.useLoaderData();
    return <LabDirectoryView retiredPortfolios={retiredPortfolios} />;
}

export function LabDirectoryView({ retiredPortfolios }: { retiredPortfolios: Portfolio[] }) {
    return (
        <div className="min-h-screen bg-boxel-canvas text-boxel-ink">
            <PageLayout maxWidth="xl">
                <header className="mb-8 pb-4 border-b-2 border-boxel-bevel-hi flex flex-wrap items-baseline justify-between gap-4">
                    <div>
                        <h1 className="text-3xl font-black text-boxel-ink uppercase tracking-tight">
                            Lab & Experimental Directory
                        </h1>
                        <p className="text-sm text-boxel-muted mt-1">
                            Direct access to research modules, telemetry inspectors, audits, and
                            archived models while we streamline the core benchmark.
                        </p>
                    </div>
                    <Badge colorScheme="accent" variant="solid" size="sm">
                        3-Block Index
                    </Badge>
                </header>

                {/* Strictly 3 Category Blocks using intrinsic flex-wrap */}
                <div className="flex flex-wrap gap-6 items-start">
                    {LAB_CATEGORIES.map((category) => (
                        <Card
                            key={category.id}
                            padding="md"
                            className="flex-1 basis-80 min-w-0 flex flex-col gap-4"
                        >
                            <div className="pb-3 border-b-2 border-boxel-bevel-hi">
                                <SectionHeading className="text-lg">
                                    {category.title}
                                </SectionHeading>
                                <p className="text-xs text-boxel-muted mt-1">{category.subtitle}</p>
                            </div>

                            <div className="flex flex-col gap-2.5">
                                {category.items.map((item) => (
                                    <Link
                                        key={item.to}
                                        to={item.to}
                                        className="voxel-trough p-3 block hover:bg-boxel-elevated transition-colors group"
                                    >
                                        <div className="flex items-center justify-between gap-2 mb-1">
                                            <span className="font-bold text-sm text-boxel-ink group-hover:text-accent transition-colors">
                                                {item.label}
                                            </span>
                                            <span className="font-mono text-xs text-accent">
                                                {item.to}
                                            </span>
                                        </div>
                                        <p className="text-xs text-boxel-muted leading-relaxed">
                                            {item.description}
                                        </p>
                                    </Link>
                                ))}
                            </div>

                            {/* Append Retired Portfolios inside Block 3 (Audits, Benchmarks & Retired Archives) */}
                            {category.id === 'audits-archives' && retiredPortfolios.length > 0 && (
                                <div className="pt-3 border-t-2 border-boxel-bevel-hi">
                                    <div className="flex items-center justify-between gap-2 mb-2">
                                        <span className="text-xs font-black uppercase tracking-widest text-boxel-muted">
                                            Retired Agent Archive
                                        </span>
                                        <Badge colorScheme="neutral" variant="soft" size="xs">
                                            {retiredPortfolios.length} Frozen
                                        </Badge>
                                    </div>
                                    <div className="flex flex-col gap-2">
                                        {retiredPortfolios.map((p) => (
                                            <Link
                                                key={p.id}
                                                to="/portfolios/$portfolioId"
                                                params={{ portfolioId: p.id }}
                                                className="voxel-trough px-3 py-2 flex items-center justify-between gap-2 hover:bg-boxel-elevated transition-colors"
                                            >
                                                <span className="text-xs font-bold text-boxel-ink truncate">
                                                    {p.owner_id ?? 'Retired Agent'}
                                                </span>
                                                <span className="font-mono text-xs text-boxel-muted shrink-0">
                                                    $
                                                    {Number(p.total_equity ?? 0).toLocaleString(
                                                        'en-US',
                                                        {
                                                            maximumFractionDigits: 0,
                                                        },
                                                    )}
                                                </span>
                                            </Link>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </Card>
                    ))}
                </div>
            </PageLayout>
        </div>
    );
}
