import type { Memory } from '@llm-market-bench/database';
import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { fetchMemories } from '~/features/memories/api/fetch-memories';
import { EventChainPage } from '~/features/memories/pages/EventChainPage';
import { buildChain } from '~/features/memories/utils/build-chain';

const getEventChain = createServerFn({ method: 'GET' })
    .inputValidator((d: string) => d)
    .handler(async ({ data: memoryId }: { data: string }) => {
        // Fetch all memories and build the chain
        const allMemories: Memory[] = [];
        let cursor: string | undefined;

        // Fetch all memories (could optimize with specific query)
        while (true) {
            const result = await fetchMemories(cursor, 100);
            allMemories.push(...result.data);
            if (!result.hasMore) break;
            cursor = result.nextCursor || undefined;
        }

        return buildChain(memoryId, allMemories);
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
