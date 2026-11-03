import type { Portfolio } from '@llm-market-bench/database';
import { Badge, Card, PageLayout, SectionHeading } from '@llm-market-bench/ui-design-system';
import { createFileRoute, Link } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import { fetchPortfolios } from '~/features/portfolios/api/fetch-portfolios';
import { seo } from '~/lib/seo';

const getRetiredPortfolios = createServerFn({ method: 'GET' }).handler(async () => {
    const portfolios = await fetchPortfolios().catch(() => []);
    return portfolios.filter((p) => !p.is_active);
});

export const Route = createFileRoute('/retired-agents')({
    loader: async () => ({ retiredPortfolios: await getRetiredPortfolios() }),
    head: () => ({
        meta: [
            ...seo({
                title: 'Retired Agents | Benchify',
                description: 'Archive of frozen, retired agent portfolios.',
            }),
        ],
    }),
    component: RetiredAgentsRouteComponent,
});

function RetiredAgentsRouteComponent() {
    const { retiredPortfolios } = Route.useLoaderData();
    return <RetiredAgentsView retiredPortfolios={retiredPortfolios} />;
}

export function RetiredAgentsView({ retiredPortfolios }: { retiredPortfolios: Portfolio[] }) {
    return (
        <div className="min-h-screen bg-boxel-canvas text-boxel-ink">
            <PageLayout maxWidth="xl" className="flex flex-col gap-6">
                <header className="pb-4 border-b-2 border-boxel-bevel-hi flex flex-wrap items-baseline justify-between gap-4">
                    <div className="flex flex-col gap-1">
                        <h1 className="text-lg font-bold text-boxel-ink uppercase tracking-tight">
                            Retired Agents
                        </h1>
                        <p className="text-xs font-normal text-boxel-muted">
                            Frozen portfolios of agents no longer trading.
                        </p>
                    </div>
                    <Badge colorScheme="neutral" variant="soft" size="xs">
                        {retiredPortfolios.length} Frozen
                    </Badge>
                </header>
                <Card padding="md" className="flex flex-col gap-4">
                    <SectionHeading className="text-lg">Archive</SectionHeading>
                    {retiredPortfolios.length === 0 ? (
                        <p className="text-xs font-normal text-boxel-muted">No retired agents.</p>
                    ) : (
                        <div className="flex flex-col gap-2">
                            {retiredPortfolios.map((p) => (
                                <Link
                                    key={p.id}
                                    to="/portfolios/$portfolioId"
                                    params={{ portfolioId: p.id }}
                                    className="voxel-trough px-3 py-2 flex items-center justify-between gap-2 hover:bg-boxel-elevated transition-colors"
                                >
                                    <span className="text-xs font-normal text-boxel-ink truncate">
                                        {p.owner_id ?? 'Retired Agent'}
                                    </span>
                                    <span className="font-mono text-xs font-normal text-boxel-muted shrink-0">
                                        $
                                        {Number(p.total_equity ?? 0).toLocaleString('en-US', {
                                            maximumFractionDigits: 0,
                                        })}
                                    </span>
                                </Link>
                            ))}
                        </div>
                    )}
                </Card>
            </PageLayout>
        </div>
    );
}
