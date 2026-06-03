import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { fetchMemoryById, fetchMemoryChain } from '~/features/memories/api/fetch-memories';
import { EventChainPage } from '~/features/memories/pages/EventChainPage';
import { buildChain } from '~/features/memories/utils/build-chain';
import { formatEasternDateTimeWithYear } from '~/utils/date';

const getFocusMemory = createServerFn({ method: 'GET' })
    .inputValidator((d: string) => d)
    .handler(async ({ data: memoryId }: { data: string }) => {
        return fetchMemoryById(memoryId);
    });

const getEventChain = createServerFn({ method: 'GET' })
    .inputValidator((d: string) => d)
    .handler(async ({ data: memoryId }: { data: string }) => {
        const chainMemories = await fetchMemoryChain(memoryId);
        return buildChain(memoryId, chainMemories);
    });

export const Route = createFileRoute('/memories/chain/$memoryId')({
    loader: ({ params }) => getFocusMemory({ data: params.memoryId }),
    component: RouteComponent,
});

function RouteComponent() {
    const focusMemory = Route.useLoaderData();
    const getEventChainFn = useServerFn(getEventChain);
    const { memoryId } = Route.useParams();

    // Map the single loaded focus memory into the initial shape required by EventChainPage
    const initialData = {
        chain: focusMemory
            ? [
                  {
                      ...focusMemory,
                      formattedDate: formatEasternDateTimeWithYear(focusMemory.created_at),
                  },
              ]
            : [],
        targetMemory: focusMemory
            ? {
                  ...focusMemory,
                  formattedDate: formatEasternDateTimeWithYear(focusMemory.created_at),
              }
            : null,
    };

    return (
        <EventChainPage
            memoryId={memoryId}
            initialData={initialData}
            fetchFn={() => getEventChainFn({ data: memoryId })}
        />
    );
}
