import { expect, test, vi } from 'vitest';

interface MockSupabaseChain {
    rpc: ReturnType<typeof vi.fn>;
}

let mockSupabaseClient: MockSupabaseChain | null = null;

vi.mock('~/lib/supabase', () => ({
    getSupabaseServerClient: vi.fn(() => mockSupabaseClient),
}));

import { fetchLeaderboard } from './fetch-leaderboard';

test('fetchLeaderboard calls get_llm_leaderboard_metrics RPC with correct params and filters old models', async () => {
    const mockData = [
        {
            model_name: 'deepseek-v4-pro',
            total_equity: 10820,
            return_pct: 8.2,
            realized_pnl: 820,
            win_rate: 68.2,
            total_trades: 15,
            verifier_approval_rate: 95.4,
            average_confidence: 85.0,
            api_success_rate: 100.0,
            trading_activity_rate: 90.0,
            trading_performance_score: 85.2,
            reasoning_quality_score: 92.3,
            consistency_score: 97.0,
            composite_score: 89.5,
        },
        {
            model_name: 'old-gpt-model-v1',
            total_equity: 10000,
            return_pct: 0.0,
            realized_pnl: 0,
            win_rate: 0,
            total_trades: 0,
            verifier_approval_rate: 50.0,
            average_confidence: 50.0,
            api_success_rate: 100.0,
            trading_activity_rate: 50.0,
            trading_performance_score: 50.0,
            reasoning_quality_score: 50.0,
            consistency_score: 50.0,
            composite_score: 50.0,
        },
    ];

    mockSupabaseClient = {
        rpc: vi.fn().mockResolvedValue({ data: mockData, error: null }),
    };

    const result = await fetchLeaderboard(30);

    expect(mockSupabaseClient.rpc).toHaveBeenCalledWith('get_llm_leaderboard_metrics', {
        time_window_days: 30,
    });
    // The old model 'old-gpt-model-v1' should be filtered out
    expect(result).toHaveLength(1);
    expect(result[0].model_name).toBe('deepseek-v4-pro');
    expect(result[0].composite_score).toBe(89.5);
});

test('fetchLeaderboard passes null time window when specified', async () => {
    mockSupabaseClient = {
        rpc: vi.fn().mockResolvedValue({ data: [], error: null }),
    };

    await fetchLeaderboard(null);

    expect(mockSupabaseClient.rpc).toHaveBeenCalledWith('get_llm_leaderboard_metrics', {
        time_window_days: null,
    });
});

test('fetchLeaderboard propagates database errors', async () => {
    const dbError = new Error('Database connection failed');
    mockSupabaseClient = {
        rpc: vi.fn().mockResolvedValue({ data: null, error: dbError }),
    };

    await expect(fetchLeaderboard(7)).rejects.toThrow('Database connection failed');
});
