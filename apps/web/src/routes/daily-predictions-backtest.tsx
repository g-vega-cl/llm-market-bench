import { createFileRoute } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import {
    fetchDailyPredictorBacktestExperiments,
    fetchDailyPredictorBacktestPredictions,
} from '~/features/daily-predictions/api/fetch-daily-predictions';
import { DailyPredictionsBacktestPage } from '~/features/daily-predictions/pages/DailyPredictionsBacktestPage';

const getDailyPredictionsBacktestData = createServerFn({ method: 'GET' }).handler(async () => {
    const [predictions, experiments] = await Promise.all([
        fetchDailyPredictorBacktestPredictions(),
        fetchDailyPredictorBacktestExperiments(),
    ]);
    return { predictions, experiments };
});

export const Route = createFileRoute('/daily-predictions-backtest')({
    loader: async () => await getDailyPredictionsBacktestData(),
    component: RouteComponent,
});

function RouteComponent() {
    const initialData = Route.useLoaderData();

    return (
        <DailyPredictionsBacktestPage
            initialPredictions={initialData.predictions}
            experiments={initialData.experiments}
        />
    );
}
