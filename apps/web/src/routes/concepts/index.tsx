import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { fetchConceptMemories, fetchConcepts } from '~/features/concepts/api/fetch-concepts';
import { ConceptsPage } from '~/features/concepts/pages/ConceptsPage';

const getConcepts = createServerFn({ method: 'GET' }).handler(async () => {
    return fetchConcepts();
});

const getConceptMemories = createServerFn({ method: 'GET' })
    .inputValidator((d: string) => d)
    .handler(async ({ data: conceptId }: { data: string }) => {
        return fetchConceptMemories(conceptId);
    });

export const Route = createFileRoute('/concepts/')({
    loader: () => getConcepts(),
    component: RouteComponent,
});

function RouteComponent() {
    const initialData = Route.useLoaderData();
    const fetchConceptsFn = useServerFn(getConcepts);
    const fetchMemoriesFn = useServerFn(getConceptMemories);

    return (
        <ConceptsPage
            initialData={initialData}
            fetchFn={() => fetchConceptsFn()}
            fetchMemoriesFn={(conceptId) => fetchMemoriesFn({ data: conceptId })}
        />
    );
}
