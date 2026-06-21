import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import {
    fetchAIPredictions,
    fetchPredictorExperiments,
} from '~/features/ai-predictions/api/fetch-predictions';
import { AIPredictionsPage } from '~/features/ai-predictions/pages/AIPredictionsPage';

const getPredictionsData = createServerFn({ method: 'GET' }).handler(async () => {
    const [predictions, experiments] = await Promise.all([
        fetchAIPredictions(),
        fetchPredictorExperiments(),
    ]);
    return { predictions, experiments };
});

export const Route = createFileRoute('/ai-predictions/')({
    loader: async () => await getPredictionsData(),
    component: RouteComponent,
});

function RouteComponent() {
    const initialData = Route.useLoaderData();
    const getPredictionsFn = useServerFn(getPredictionsData);

    return (
        <AIPredictionsPage
            initialData={initialData.predictions}
            experiments={initialData.experiments}
            refreshFn={async () => {
                const res = await getPredictionsFn();
                return res;
            }}
        />
    );
}
