import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { fetchMemories } from '~/features/memories/api/fetch-memories';
import { MemoriesPage } from '~/features/memories/pages/MemoriesPage';

const getMemories = createServerFn({ method: 'GET' })
    .inputValidator((d: { cursor?: string; category?: string }) => d)
    .handler(async ({ data: { cursor, category } }) => {
        return fetchMemories(cursor, undefined, category);
    });

export const Route = createFileRoute('/memories/')({ component: RouteComponent });
function RouteComponent() {
    const getMemoriesFn = useServerFn(getMemories);
    return (
        <MemoriesPage
            fetchFn={(cursor, category) => getMemoriesFn({ data: { cursor, category } })}
        />
    );
}
