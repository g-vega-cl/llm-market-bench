import { resolveAtmospherePhase } from '@llm-market-bench/ui-design-system';
import { createFileRoute } from '@tanstack/react-router';
import { HomeCtaPage } from '~/features/home/pages/HomeCtaPage';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/')({
    loader: () => ({
        initialAtmosphere: resolveAtmospherePhase(new Date(), 'market-et'),
    }),
    head: () => ({
        meta: [
            ...seo({
                title: 'Benchify — build and backtest trading bots',
                description:
                    'Benchify helps you describe a trading bot, backtest it on point-in-time news, and see how it holds up. Paper cash only, with the results left on the record.',
            }),
        ],
    }),
    component: RouteComponent,
});

function RouteComponent() {
    const { initialAtmosphere } = Route.useLoaderData();
    return <HomeCtaPage initialAtmosphere={initialAtmosphere} />;
}
