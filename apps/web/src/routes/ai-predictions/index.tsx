import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { fetchAIPredictions } from '~/features/ai-predictions/api/fetch-predictions';
import { AIPredictionsPage } from '~/features/ai-predictions/pages/AIPredictionsPage';

const getPredictions = createServerFn({ method: 'GET' }).handler(async () => {
    return fetchAIPredictions();
});

export const Route = createFileRoute('/ai-predictions/')({
    loader: async () => await getPredictions(),
    component: RouteComponent,
});

function RouteComponent() {
    const initialData = Route.useLoaderData();
    const refreshFn = useServerFn(getPredictions);

    return <AIPredictionsPage initialData={initialData} refreshFn={() => refreshFn()} />;
}
