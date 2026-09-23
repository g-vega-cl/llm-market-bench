import { createClient } from '@supabase/supabase-js';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
    fetchDailyPredictions,
    fetchDailyPredictorBacktestExperiments,
    fetchDailyPredictorBacktestPredictions,
    fetchDailyPredictorExperiments,
} from './fetch-daily-predictions';

vi.mock('@supabase/supabase-js', () => ({
    createClient: vi.fn(),
}));

describe('fetch-daily-predictions', () => {
    const mockChain = {
        from: vi.fn().mockReturnThis(),
        select: vi.fn().mockReturnThis(),
        eq: vi.fn().mockReturnThis(),
        or: vi.fn().mockReturnThis(),
        ilike: vi.fn().mockReturnThis(),
        order: vi.fn().mockResolvedValue({ data: [], error: null }),
    };

    beforeEach(() => {
        vi.clearAllMocks();
        process.env.VITE_SUPABASE_URL = 'http://mock-url.supabase.co';
        process.env.VITE_SUPABASE_ANON_KEY = 'mock-anon-key';
        vi.mocked(createClient).mockReturnValue(
            mockChain as unknown as ReturnType<typeof createClient>,
        );
    });

    it('fetchDailyPredictions excludes backtest predictions via or-filter and in-memory fallback', async () => {
        const mockData = [
            {
                id: '1',
                prompt_variant_tag: 'daily-pred-live-1',
                model_name: 'deepseek-v4-flash',
            },
            {
                id: '2',
                prompt_variant_tag: 'daily-pred-backtest-1234',
                model_name: 'deepseek-v4-flash',
            },
            {
                id: '3',
                prompt_variant_tag: null,
                model_name: 'MiniMax-M3',
            },
        ];
        mockChain.order.mockResolvedValueOnce({ data: mockData, error: null });

        const result = await fetchDailyPredictions();

        expect(mockChain.from).toHaveBeenCalledWith('daily_predictions');
        expect(mockChain.select).toHaveBeenCalledWith('*');
        expect(mockChain.or).toHaveBeenCalledWith(
            'prompt_variant_tag.is.null,prompt_variant_tag.not.ilike.%backtest%',
        );
        expect(mockChain.order).toHaveBeenCalledWith('created_at', { ascending: false });
        expect(result).toHaveLength(2);
        expect(result.map((r) => r.id)).toEqual(['1', '3']);
    });

    it('fetchDailyPredictorExperiments queries non-backtest prompt experiments', async () => {
        const mockExperiments = [{ id: 'exp-1', is_backtest: false }];
        mockChain.order.mockResolvedValueOnce({ data: mockExperiments, error: null });

        const result = await fetchDailyPredictorExperiments();

        expect(mockChain.from).toHaveBeenCalledWith('prompt_experiments');
        expect(mockChain.eq).toHaveBeenCalledWith('prompt_name', 'DAILY_PREDICTOR_PROMPT');
        expect(mockChain.eq).toHaveBeenCalledWith('is_backtest', false);
        expect(result).toEqual(mockExperiments);
    });

    it('fetchDailyPredictorBacktestPredictions queries backtest predictions', async () => {
        const mockBacktestPredictions = [
            { id: 'bt-1', prompt_variant_tag: 'daily-pred-backtest-1' },
        ];
        mockChain.order.mockResolvedValueOnce({ data: mockBacktestPredictions, error: null });

        const result = await fetchDailyPredictorBacktestPredictions();

        expect(mockChain.from).toHaveBeenCalledWith('daily_predictions');
        expect(mockChain.ilike).toHaveBeenCalledWith('prompt_variant_tag', '%backtest%');
        expect(result).toEqual(mockBacktestPredictions);
    });

    it('fetchDailyPredictorBacktestExperiments queries backtest prompt experiments', async () => {
        const mockExperiments = [{ id: 'exp-bt-1', is_backtest: true }];
        mockChain.order.mockResolvedValueOnce({ data: mockExperiments, error: null });

        const result = await fetchDailyPredictorBacktestExperiments();

        expect(mockChain.from).toHaveBeenCalledWith('prompt_experiments');
        expect(mockChain.eq).toHaveBeenCalledWith('prompt_name', 'DAILY_PREDICTOR_PROMPT');
        expect(mockChain.eq).toHaveBeenCalledWith('is_backtest', true);
        expect(result).toEqual(mockExperiments);
    });
});
