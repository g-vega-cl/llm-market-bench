import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { loadDailyPredictionsPageData } from '~/features/daily-predictions/api/load-daily-predictions-page-data';
import { DailyPredictionsPage } from '~/features/daily-predictions/pages/DailyPredictionsPage';

const getDailyPredictionsData = createServerFn({ method: 'GET' }).handler(async () =>
    loadDailyPredictionsPageData(),
);

export const Route = createFileRoute('/daily-predictions/')({
    validateSearch: (search: Record<string, unknown>): { ticker?: 'SPY' | 'TLT' | 'PICKS' } => {
        const raw = typeof search.ticker === 'string' ? search.ticker.toUpperCase() : '';
        if (raw === 'TLT') return { ticker: 'TLT' };
        if (raw === 'PICKS') return { ticker: 'PICKS' };
        return { ticker: undefined };
    },
    loader: async () => await getDailyPredictionsData(),
    component: RouteComponent,
});

function RouteComponent() {
    const initialData = Route.useLoaderData();
    const { ticker } = Route.useSearch();
    const getPredictionsFn = useServerFn(getDailyPredictionsData);

    return (
        <DailyPredictionsPage
            initialPredictions={initialData.predictions}
            experiments={initialData.experiments}
            initialBaskets={initialData.baskets}
            initialTicker={ticker || 'SPY'}
            refreshFn={async () => {
                const res = await getPredictionsFn();
                return res;
            }}
        />
    );
}
