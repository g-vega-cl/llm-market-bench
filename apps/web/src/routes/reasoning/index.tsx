import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { fetchReasoningLogs } from '~/features/reasoning/api/fetch-reasoning-logs';
import { ReasoningPage } from '~/features/reasoning/pages/ReasoningPage';

const getReasoningLogs = createServerFn({ method: 'GET' }).handler(
    async ({ data }: { data?: string }) => {
        return fetchReasoningLogs(data);
    },
);

export const Route = createFileRoute('/reasoning/')({
    component: RouteComponent,
});

function RouteComponent() {
    const getReasoningLogsFn = useServerFn(getReasoningLogs);

    return (
        <ReasoningPage fetchFn={(pageParam) => getReasoningLogsFn({ data: pageParam } as any)} />
    );
}
