import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { fetchReasoningLogs } from '~/features/reasoning/api/fetch-reasoning-logs';
import { ReasoningPage } from '~/features/reasoning/pages/ReasoningPage';

const getReasoningLogs = createServerFn({ method: 'GET' })
    .inputValidator((d: string | undefined) => d)
    .handler(async ({ data: cursor }) => {
        return fetchReasoningLogs(cursor);
    });

export const Route = createFileRoute('/reasoning/')({ component: RouteComponent });
function RouteComponent() {
    const getReasoningLogsFn = useServerFn(getReasoningLogs);
    return <ReasoningPage fetchFn={(pageParam) => getReasoningLogsFn({ data: pageParam })} />;
}
