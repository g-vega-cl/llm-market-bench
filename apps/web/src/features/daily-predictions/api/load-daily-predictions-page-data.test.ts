import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { DailyPrediction } from './fetch-daily-predictions';
import type { DailyStockBasket } from './fetch-stock-picks';

const mockFetchDailyPredictions = vi.fn();
const mockFetchDailyPredictorExperiments = vi.fn();
const mockFetchDailyStockBaskets = vi.fn();

vi.mock('./fetch-daily-predictions', () => ({
    fetchDailyPredictions: () => mockFetchDailyPredictions(),
    fetchDailyPredictorExperiments: () => mockFetchDailyPredictorExperiments(),
}));

vi.mock('./fetch-stock-picks', () => ({
    fetchDailyStockBaskets: () => mockFetchDailyStockBaskets(),
}));

const { loadDailyPredictionsPageData } = await import('./load-daily-predictions-page-data');

const mockPrediction = {
    id: 'pred-1',
    ticker: 'SPY',
} as DailyPrediction;

const mockBasket = {
    id: 'basket-consensus',
    target_date: '2026-11-13',
    model_name: 'consensus',
    status: 'pending',
    picks: [{ id: 'pick-1', ticker: 'NVDA', direction: 'UP', rank: 1, confidence: 80 }],
} as unknown as DailyStockBasket;

describe('loadDailyPredictionsPageData', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('returns predictions, experiments and stock pick baskets in one payload', async () => {
        mockFetchDailyPredictions.mockResolvedValue([mockPrediction]);
        mockFetchDailyPredictorExperiments.mockResolvedValue([]);
        mockFetchDailyStockBaskets.mockResolvedValue([mockBasket]);

        const data = await loadDailyPredictionsPageData();

        expect(data.predictions).toEqual([mockPrediction]);
        expect(data.experiments).toEqual([]);
        expect(data.baskets).toEqual([mockBasket]);
    });

    it('fetches stock pick baskets so the 3 UP / 3 DOWN tab is populated', async () => {
        mockFetchDailyPredictions.mockResolvedValue([]);
        mockFetchDailyPredictorExperiments.mockResolvedValue([]);
        mockFetchDailyStockBaskets.mockResolvedValue([mockBasket]);

        await loadDailyPredictionsPageData();

        expect(mockFetchDailyStockBaskets).toHaveBeenCalledTimes(1);
    });

    it('degrades to empty baskets instead of failing the page', async () => {
        const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
        mockFetchDailyPredictions.mockResolvedValue([mockPrediction]);
        mockFetchDailyPredictorExperiments.mockResolvedValue([]);
        mockFetchDailyStockBaskets.mockRejectedValue(
            new Error("Could not find the table 'public.daily_stock_baskets'"),
        );

        const data = await loadDailyPredictionsPageData();

        expect(data.predictions).toEqual([mockPrediction]);
        expect(data.baskets).toEqual([]);
        expect(consoleError).toHaveBeenCalled();
        consoleError.mockRestore();
    });

    it('still fails when the predictions read fails', async () => {
        mockFetchDailyPredictions.mockRejectedValue(new Error('predictions down'));
        mockFetchDailyPredictorExperiments.mockResolvedValue([]);
        mockFetchDailyStockBaskets.mockResolvedValue([]);

        await expect(loadDailyPredictionsPageData()).rejects.toThrow('predictions down');
    });
});
