import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import {
    fetchDailyPredictions,
    fetchDailyPredictorExperiments,
} from '~/features/daily-predictions/api/fetch-daily-predictions';
import { DailyPredictionsPage } from '~/features/daily-predictions/pages/DailyPredictionsPage';

const getDailyPredictionsData = createServerFn({ method: 'GET' }).handler(async () => {
    const [predictions, experiments] = await Promise.all([
        fetchDailyPredictions(),
        fetchDailyPredictorExperiments(),
    ]);
    return { predictions, experiments };
});

export const Route = createFileRoute('/daily-predictions/')({
    validateSearch: (search: Record<string, unknown>): { ticker?: 'SPY' | 'TLT' } => ({
        ticker:
            typeof search.ticker === 'string' && search.ticker.toUpperCase() === 'TLT'
                ? 'TLT'
                : undefined,
    }),
    loader: async () => await getDailyPredictionsData(),
    component: RouteComponent,
});

function RouteComponent() {
    const initialData = Route.useLoaderData();
    const { ticker } = Route.useSearch();
    const getPredictionsFn = useServerFn(getDailyPredictionsData);

    return (
        <DailyPredictionsPage
            initialPredictions={initialData.predictions}
            experiments={initialData.experiments}
            initialTicker={ticker || 'SPY'}
            refreshFn={async () => {
                const res = await getPredictionsFn();
                return res;
            }}
        />
    );
}
