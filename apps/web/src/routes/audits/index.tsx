import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { fetchAudits } from '~/features/audits/api/fetch-audits';
import { AuditsPage } from '~/features/audits/pages/AuditsPage';

const getAudits = createServerFn({ method: 'GET' })
    .inputValidator((d?: string) => d)
    .handler(async ({ data }) => {
        return fetchAudits(data);
    });

export const Route = createFileRoute('/audits/')({
    component: RouteComponent,
});

function RouteComponent() {
    const getAuditsFn = useServerFn(getAudits);

    return (
        <AuditsPage fetchFn={(pageParam: string | undefined) => getAuditsFn({ data: pageParam })} />
    );
}
