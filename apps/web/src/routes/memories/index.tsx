import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { fetchMemories } from '~/features/memories/api/fetch-memories';
import { MemoriesPage } from '~/features/memories/pages/MemoriesPage';

const getMemories = (createServerFn({ method: 'GET' }) as any)
    .inputValidator((d: string | undefined) => d)
    .handler(async ({ data: cursor }: { data: string | undefined }) => {
        return fetchMemories(cursor);
    });

export const Route = createFileRoute('/memories/')({ component: RouteComponent });
function RouteComponent() {
    const getMemoriesFn = useServerFn(getMemories);
    return <MemoriesPage fetchFn={(pageParam) => getMemoriesFn({ data: pageParam })} />;
}
