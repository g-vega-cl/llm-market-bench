import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { fetchReasoningLogs } from '~/features/reasoning/api/fetch-reasoning-logs';
import { ReasoningPage } from '~/features/reasoning/pages/ReasoningPage';

const getReasoningLogs = createServerFn({ method: 'GET' })
    .inputValidator((d: { cursor?: string; limit?: number } | undefined) => d)
    .handler(async ({ data }) => {
        return fetchReasoningLogs(data?.cursor, data?.limit ?? 50);
    });

export const Route = createFileRoute('/reasoning/')({
    loader: async () => await getReasoningLogs({ data: { limit: 5 } }),
    component: RouteComponent,
});

function RouteComponent() {
    const initialData = Route.useLoaderData();
    const getReasoningLogsFn = useServerFn(getReasoningLogs);
    return (
        <ReasoningPage
            initialData={initialData}
            fetchFn={(pageParam) => getReasoningLogsFn({ data: { cursor: pageParam, limit: 50 } })}
        />
    );
}
