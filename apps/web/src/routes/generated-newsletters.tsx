import { createFileRoute } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import { fetchGeneratedNewsletters } from '~/features/generated-newsletters/api/fetch-generated-newsletters';
import { GeneratedNewslettersPage } from '~/features/generated-newsletters/pages/GeneratedNewslettersPage';

const getGeneratedNewslettersData = createServerFn({ method: 'GET' }).handler(async () => {
    return fetchGeneratedNewsletters(30, 'all');
});

export const Route = createFileRoute('/generated-newsletters')({
    loader: async () => await getGeneratedNewslettersData(),
    component: RouteComponent,
});

function RouteComponent() {
    const initialData = Route.useLoaderData();
    return <GeneratedNewslettersPage initialNewsletters={initialData} />;
}
