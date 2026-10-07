import { createFileRoute } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import {
    fetchEarningsAlphaSnapshots,
    fetchSectorBellwethers,
} from '~/features/earnings/api/fetch-earnings-audit';
import { fetchEarningsPredictions } from '~/features/earnings/api/fetch-earnings-predictions';
import { EarningsAuditPage } from '~/features/earnings/pages/EarningsAuditPage';

const getEarningsAuditData = createServerFn({ method: 'GET' }).handler(async () => {
    const [snapshots, bellwethers, predictions] = await Promise.all([
        fetchEarningsAlphaSnapshots(),
        fetchSectorBellwethers(),
        fetchEarningsPredictions(),
    ]);

    return {
        snapshots,
        bellwethers,
        predictions,
    };
});

export const Route = createFileRoute('/earnings-audit')({
    loader: async () => await getEarningsAuditData(),
    component: RouteComponent,
});

function RouteComponent() {
    const data = Route.useLoaderData();

    return (
        <EarningsAuditPage
            snapshots={data?.snapshots ?? []}
            bellwethers={data?.bellwethers ?? []}
            predictions={data?.predictions ?? []}
        />
    );
}
