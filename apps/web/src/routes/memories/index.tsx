import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import {
    fetchMemories,
    fetchNewMemories,
    searchMemories,
} from '~/features/memories/api/fetch-memories';
import { MemoriesPage } from '~/features/memories/pages/MemoriesPage';

interface MemoriesQueryParams {
    cursor?: string;
    category?: string;
    limit?: number;
}

interface SearchQueryParams {
    query?: string;
    limit?: number;
}

interface SyncQueryParams {
    since?: string;
}

const getMemories = createServerFn({ method: 'GET' })
    .inputValidator((d: MemoriesQueryParams | { data?: MemoriesQueryParams } | undefined) => d)
    .handler(async ({ data }) => {
        const payload: MemoriesQueryParams | undefined =
            data && 'data' in data && data.data ? data.data : (data as MemoriesQueryParams);
        const cursor = payload?.cursor;
        const category = payload?.category;
        const limit = payload?.limit ?? 50;
        return fetchMemories(cursor, limit, category);
    });

const syncMemories = createServerFn({ method: 'GET' })
    .inputValidator((d: SyncQueryParams | { data?: SyncQueryParams } | string | undefined) => d)
    .handler(async ({ data }) => {
        let since = '';
        if (typeof data === 'string') {
            since = data;
        } else if (data && 'data' in data && data.data) {
            since = data.data.since ?? '';
        } else if (data && 'since' in data) {
            since = data.since ?? '';
        }

        if (!since) return [];
        return fetchNewMemories(since);
    });

const queryMemories = createServerFn({ method: 'GET' })
    .inputValidator((d: SearchQueryParams | { data?: SearchQueryParams } | string | undefined) => d)
    .handler(async ({ data }) => {
        let queryStr = '';
        let limit = 50;

        if (typeof data === 'string') {
            queryStr = data;
        } else if (data && 'data' in data && data.data) {
            queryStr = data.data.query ?? '';
            limit = data.data.limit ?? 50;
        } else if (data && 'query' in data) {
            queryStr = data.query ?? '';
            limit = data.limit ?? 50;
        }

        if (!queryStr) return [];
        return searchMemories(queryStr, limit);
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
    const queryMemoriesFn = useServerFn(queryMemories);
    const syncMemoriesFn = useServerFn(syncMemories);

    return (
        <MemoriesPage
            initialMemories={initialData.data}
            initialHasMore={initialData.hasMore}
            initialCursor={initialData.nextCursor}
            fetchFn={(cursor, category) => getMemoriesFn({ data: { cursor, category, limit: 50 } })}
            searchFn={(query) => queryMemoriesFn({ data: { query } })}
            deltaSyncFn={(since) => syncMemoriesFn({ data: { since } })}
        />
    );
}
