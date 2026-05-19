import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { fetchExperiments } from '~/features/autoresearch/api/fetch-experiments';
import { AutoresearchPage } from '~/features/autoresearch/pages/AutoresearchPage';

const getExperiments = createServerFn({ method: 'GET' }).handler(async () => {
    return fetchExperiments();
});

export const Route = createFileRoute('/autoresearch/')({
    loader: async () => await getExperiments(),
    component: RouteComponent,
});

function RouteComponent() {
    const initialData = Route.useLoaderData();
    const getExperimentsFn = useServerFn(getExperiments);

    return <AutoresearchPage initialData={initialData} fetchFn={() => getExperimentsFn()} />;
}
