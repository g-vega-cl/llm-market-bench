import type { PromptExperiment } from '@llm-market-bench/database';
import {
    type DailyPrediction,
    fetchDailyPredictions,
    fetchDailyPredictorExperiments,
    fetchStockPickerExperiments,
} from './fetch-daily-predictions';
import { type DailyStockBasket, fetchDailyStockBaskets } from './fetch-stock-picks';

export interface DailyPredictionsPageData {
    predictions: DailyPrediction[];
    experiments: PromptExperiment[];
    baskets: DailyStockBasket[];
    stockExperiments: PromptExperiment[];
}

/**
 * Single server-side payload for /daily-predictions.
 *
 * The router loader must not hand-assemble fetches per route: the 3 UP / 3 DOWN
 * tab renders straight from `baskets`, so omitting it silently blanks the tab.
 * Baskets degrade to [] instead of failing the page — the SPY/TLT tabs must stay
 * reachable when the stock-pick tables are unavailable (e.g. a stale PostgREST
 * schema cache on the edge replica).
 */
export async function loadDailyPredictionsPageData(): Promise<DailyPredictionsPageData> {
    const [predictions, experiments, baskets, stockExperiments] = await Promise.allSettled([
        fetchDailyPredictions(),
        fetchDailyPredictorExperiments(),
        fetchDailyStockBaskets(),
        fetchStockPickerExperiments(),
    ]);

    if (predictions.status === 'rejected') {
        throw predictions.reason;
    }
    if (experiments.status === 'rejected') {
        throw experiments.reason;
    }
    if (baskets.status === 'rejected') {
        console.error(
            '[daily-predictions] stock pick baskets unavailable; 3 UP / 3 DOWN tab renders empty',
            baskets.reason,
        );
    }
    if (stockExperiments.status === 'rejected') {
        console.error(
            '[daily-predictions] stock picker experiments unavailable; degrading to empty list',
            stockExperiments.reason,
        );
    }

    return {
        predictions: predictions.value,
        experiments: experiments.value,
        baskets: baskets.status === 'fulfilled' ? baskets.value : [],
        stockExperiments: stockExperiments.status === 'fulfilled' ? stockExperiments.value : [],
    };
}
