import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { fetchConcepts } from '~/features/concepts/api/fetch-concepts';
import { ConceptsPage } from '~/features/concepts/pages/ConceptsPage';

const getConcepts = createServerFn({ method: 'GET' }).handler(async () => {
    return fetchConcepts();
});

export const Route = createFileRoute('/concepts/')({
    loader: () => getConcepts(),
    component: RouteComponent,
});

function RouteComponent() {
    const initialData = Route.useLoaderData();
    const fetchConceptsFn = useServerFn(getConcepts);

    return <ConceptsPage initialData={initialData} fetchFn={() => fetchConceptsFn()} />;
}
