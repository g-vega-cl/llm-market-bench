import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { fetchAudits } from '~/features/audits/api/fetch-audits';
import { AuditsPage } from '~/features/audits/pages/AuditsPage';

const getAudits = (createServerFn({ method: 'GET' }) as any).handler(
    async ({ data }: { data?: string }) => {
        return fetchAudits(data);
    },
);

export const Route = createFileRoute('/audits/')({
    component: RouteComponent,
});

function RouteComponent() {
    const getAuditsFn = useServerFn(getAudits);

    return <AuditsPage fetchFn={(pageParam) => getAuditsFn({ data: pageParam } as any)} />;
}
