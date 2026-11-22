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
                title: 'Benchify — build your own trading bot',
                description:
                    'Describe a trading bot in one sentence, run it on point-in-time news, and switch it Live to decide every 30 minutes during market hours. Paper cash only, and the losers stay on the record.',
            }),
        ],
    }),
    component: RouteComponent,
});

function RouteComponent() {
    const { initialAtmosphere } = Route.useLoaderData();
    return <HomeCtaPage initialAtmosphere={initialAtmosphere} />;
}
