import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { fetchMemoryChain } from '~/features/memories/api/fetch-memories';
import { EventChainPage } from '~/features/memories/pages/EventChainPage';
import { buildChain } from '~/features/memories/utils/build-chain';

const getEventChain = createServerFn({ method: 'GET' })
    .inputValidator((d: string) => d)
    .handler(async ({ data: memoryId }: { data: string }) => {
        const chainMemories = await fetchMemoryChain(memoryId);
        return buildChain(memoryId, chainMemories);
    });

export const Route = createFileRoute('/memories/chain/$memoryId')({
    loader: ({ params }) => getEventChain({ data: params.memoryId }),
    component: RouteComponent,
});

function RouteComponent() {
    const initialData = Route.useLoaderData();
    const getEventChainFn = useServerFn(getEventChain);
    const { memoryId } = Route.useParams();

    return (
        <EventChainPage
            memoryId={memoryId}
            initialData={initialData}
            fetchFn={() => getEventChainFn({ data: memoryId })}
        />
    );
}
