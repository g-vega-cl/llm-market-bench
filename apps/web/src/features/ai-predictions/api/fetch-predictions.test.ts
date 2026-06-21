import { createClient } from '@supabase/supabase-js';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchAIPredictions, fetchPredictorExperiments } from './fetch-predictions';

vi.mock('@supabase/supabase-js', () => ({
    createClient: vi.fn(),
}));

describe('fetch-predictions (TDD)', () => {
    const mockChain = {
        from: vi.fn().mockReturnThis(),
        select: vi.fn().mockReturnThis(),
        eq: vi.fn().mockReturnThis(),
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

    it('fetchAIPredictions queries sector_predictions ordered by created_at desc', async () => {
        const mockPredictions = [{ id: '1', predicted_sector: 'XLK' }];
        mockChain.order.mockResolvedValueOnce({ data: mockPredictions, error: null });

        const result = await fetchAIPredictions();

        expect(createClient).toHaveBeenCalled();
        expect(mockChain.from).toHaveBeenCalledWith('sector_predictions');
        expect(mockChain.select).toHaveBeenCalledWith('*');
        expect(mockChain.order).toHaveBeenCalledWith('created_at', { ascending: false });
        expect(result).toEqual(mockPredictions);
    });

    it('fetchPredictorExperiments queries prompt_experiments scoped to SECTOR_PREDICTOR_PROMPT', async () => {
        const mockExperiments = [{ id: '2', prompt_name: 'SECTOR_PREDICTOR_PROMPT' }];
        mockChain.order.mockResolvedValueOnce({ data: mockExperiments, error: null });

        const result = await fetchPredictorExperiments();

        expect(createClient).toHaveBeenCalled();
        expect(mockChain.from).toHaveBeenCalledWith('prompt_experiments');
        expect(mockChain.eq).toHaveBeenCalledWith('prompt_name', 'SECTOR_PREDICTOR_PROMPT');
        expect(mockChain.order).toHaveBeenCalledWith('created_at', { ascending: false });
        expect(result).toEqual(mockExperiments);
    });
});
