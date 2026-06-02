import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { fetchMemories } from '~/features/memories/api/fetch-memories';
import { MemoriesPage } from '~/features/memories/pages/MemoriesPage';

const getMemories = createServerFn({ method: 'GET' })
    .inputValidator((d: { cursor?: string; category?: string; limit?: number } | undefined) => d)
    .handler(async ({ data }) => {
        const cursor = data?.cursor;
        const category = data?.category;
        const limit = data?.limit ?? 50;
        return fetchMemories(cursor, limit, category);
    });

export const Route = createFileRoute('/memories/')({
    loader: async () => {
        const categories = ['MARKET_EVENT', 'CALENDAR_EVENT', 'POST_MORTEM', 'ACADEMIC_PAPER'];

        const [allRes, ...catResults] = await Promise.all([
            getMemories({ data: { cursor: undefined, category: undefined, limit: 5 } }),
            ...categories.map((cat) =>
                getMemories({ data: { cursor: undefined, category: cat, limit: 5 } }),
            ),
        ]);

        // Merge all memories into a single list
        const mergedMemories = [
            ...(allRes?.data || []),
            ...catResults.flatMap((res) => res?.data || []),
        ];

        // Deduplicate by ID
        const seen = new Set<string>();
        const deduplicated = mergedMemories.filter((m) => {
            if (!m.id) return true;
            if (seen.has(m.id)) return false;
            seen.add(m.id);
            return true;
        });

        // Sort chronologically descending (newest first)
        deduplicated.sort((a, b) => {
            const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
            const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
            return dateB - dateA;
        });

        return {
            data: deduplicated,
            hasMore: allRes?.hasMore ?? false,
            nextCursor: allRes?.nextCursor ?? null,
        };
    },
    component: RouteComponent,
});

function RouteComponent() {
    const initialData = Route.useLoaderData();
    const getMemoriesFn = useServerFn(getMemories);

    return (
        <MemoriesPage
            initialMemories={initialData.data}
            initialHasMore={initialData.hasMore}
            initialCursor={initialData.nextCursor}
            fetchFn={(cursor, category) => getMemoriesFn({ data: { cursor, category, limit: 50 } })}
        />
    );
}
