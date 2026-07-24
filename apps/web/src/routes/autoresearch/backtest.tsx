import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { fetchBacktestExperiments } from '~/features/autoresearch/api/fetch-experiments';
import { BacktestAutoresearchPage } from '~/features/autoresearch/pages/BacktestAutoresearchPage';

const getBacktestExperiments = createServerFn({ method: 'GET' }).handler(async () => {
    return fetchBacktestExperiments();
});

export const Route = createFileRoute('/autoresearch/backtest')({
    loader: async () => await getBacktestExperiments(),
    component: RouteComponent,
});

function RouteComponent() {
    const initialData = Route.useLoaderData();
    const getBacktestFn = useServerFn(getBacktestExperiments);

    return <BacktestAutoresearchPage initialData={initialData} fetchFn={() => getBacktestFn()} />;
}
