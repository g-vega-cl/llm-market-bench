import { createFileRoute } from '@tanstack/react-router';
import { createServerFn, useServerFn } from '@tanstack/react-start';
import { loadDailyPredictionsPageData } from '~/features/daily-predictions/api/load-daily-predictions-page-data';
import { DailyPredictionsPage } from '~/features/daily-predictions/pages/DailyPredictionsPage';

const getDailyPredictionsData = createServerFn({ method: 'GET' }).handler(async () =>
    loadDailyPredictionsPageData(),
);

export const Route = createFileRoute('/daily-predictions/')({
    /**
     * Canonical, round-tripping search.
     *
     * `loadServerRoute` (@tanstack/router-core) rebuilds the request URL from
     * this result with `_includeValidateSearch` and 307-redirects whenever it
     * differs from the requested href. Returning `{ ticker: undefined }` for a
     * ticker present in the URL therefore rewrote the URL on every SSR request,
     * and when the rewrite dropped the only param the target carried no query
     * at all — which is the shape of the production ERR_TOO_MANY_REDIRECTS loop
     * on `?ticker=SPY` (the edge is the likely reason the query-less target was
     * re-expanded back to the requested URL; that hop is not reproducible from
     * the repo).
     *
     * Keep every value the page can write in the URL: an absent param stays
     * absent (cold load renders SPY with a clean URL), and a present but
     * unrecognised value lands on SPY instead of a queryless redirect target.
     */
    validateSearch: (search: Record<string, unknown>): { ticker?: 'SPY' | 'TLT' | 'PICKS' } => {
        if (!('ticker' in search)) return {};
        const raw = typeof search.ticker === 'string' ? search.ticker.trim().toUpperCase() : '';
        if (raw === 'TLT') return { ticker: 'TLT' };
        if (raw === 'PICKS') return { ticker: 'PICKS' };
        return { ticker: 'SPY' };
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
            initialStockExperiments={initialData.stockExperiments}
            initialTicker={ticker || 'SPY'}
            refreshFn={async () => {
                const res = await getPredictionsFn();
                return res;
            }}
        />
    );
}
