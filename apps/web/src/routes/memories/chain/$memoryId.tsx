import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { fetchMemories } from '~/features/memories/api/fetch-memories';
import { EventChainPage } from '~/features/memories/pages/EventChainPage';

const getEventChain = createServerFn({ method: 'GET' })
    .inputValidator((d: string) => d)
    .handler(async ({ data: memoryId }: { data: string }) => {
        // Fetch all memories and build the chain
        const allMemories: any[] = [];
        let cursor: string | undefined;

        // Fetch all memories (could optimize with specific query)
        while (true) {
            const result = await fetchMemories(cursor, 100);
            allMemories.push(...result.data);
            if (!result.hasMore) break;
            cursor = result.nextCursor || undefined;
        }

        // Build the chain starting from the given memory
        const chain: any[] = [];
        let currentId = memoryId;
        const memoryMap = new Map(allMemories.map((m) => [m.id, m]));

        // Traverse backwards through the chain, INCLUDING the target memory
        while (currentId) {
            const memory = memoryMap.get(currentId);
            if (!memory) break;
            chain.unshift(memory); // Add to beginning to maintain chronological order
            currentId = memory.parent_id;
        }

        return { chain, targetMemory: memoryMap.get(memoryId) ?? null };
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
            fetchFn={() => getEventChainFn({ data: memoryId } as any)}
        />
    );
}
