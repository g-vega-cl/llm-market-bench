import { createFileRoute } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import {
    fetchMarketBarometerDates,
    fetchMarketBarometerForDate,
} from '~/features/home/api/fetch-barometer';
import { BarometerAuditPage } from '~/features/home/pages/BarometerAuditPage';

const getBarometerAuditData = createServerFn({ method: 'GET' })
    .inputValidator((d: { date?: string } | undefined) => d)
    .handler(async ({ data }) => {
        const dates = await fetchMarketBarometerDates();
        const selectedDate = data?.date || dates[0] || null;
        const barometer = selectedDate ? await fetchMarketBarometerForDate(selectedDate) : null;

        return {
            dates,
            selectedDate,
            barometer,
        };
    });

export const Route = createFileRoute('/barometer-audit')({
    validateSearch: (search: Record<string, unknown>): { date?: string } => {
        return {
            date: (search.date as string) || undefined,
        };
    },
    loaderDeps: ({ search: { date } }) => ({ date }),
    loader: async ({ deps: { date } }) => await getBarometerAuditData({ data: { date } }),
    component: RouteComponent,
});

function RouteComponent() {
    const data = Route.useLoaderData();

    return (
        <BarometerAuditPage
            dates={data.dates}
            selectedDate={data.selectedDate}
            barometer={data.barometer}
        />
    );
}
