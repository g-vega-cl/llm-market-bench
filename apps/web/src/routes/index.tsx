import { createFileRoute } from '@tanstack/react-router';
import { isValidWorldId, type WorldId } from '~/features/home/backdrop/voxel-world';
import { HomeCtaPage } from '~/features/home/pages/HomeCtaPage';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/')({
    validateSearch: (search: Record<string, unknown>): { world?: WorldId } => ({
        world: isValidWorldId(search.world) ? search.world : undefined,
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
    const { world } = Route.useSearch();
    return <HomeCtaPage initialWorld={world} />;
}
