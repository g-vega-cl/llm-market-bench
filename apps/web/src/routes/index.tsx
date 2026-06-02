import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { fetchTodayData } from '~/features/today/api/fetch-today-data';
import { TodayPage } from '~/features/today/pages/TodayPage';

const getTodayData = createServerFn({ method: 'GET' })
    .inputValidator((d: { limit?: number } | undefined) => d)
    .handler(async ({ data }) => {
        return fetchTodayData(data?.limit ?? 50);
    });

export const Route = createFileRoute('/')({
    loader: async () => await getTodayData({ data: { limit: 5 } }),
    component: RouteComponent,
});

function RouteComponent() {
    const initialData = Route.useLoaderData();
    const getTodayDataFn = useServerFn(getTodayData);

    return (
        <TodayPage
            initialData={initialData}
            fetchFn={() => getTodayDataFn({ data: { limit: 50 } })}
        />
    );
}
