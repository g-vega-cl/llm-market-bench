import { expect, test, vi } from 'vitest';

interface MockSupabaseChain {
    rpc: ReturnType<typeof vi.fn>;
}

let mockSupabaseClient: MockSupabaseChain | null = null;

vi.mock('~/lib/db', () => ({
    getDbServerClient: vi.fn(() => mockSupabaseClient),
}));

import { fetchLeaderboard, fetchLeaderboardPage } from './fetch-leaderboard';

test('fetchLeaderboardPage calls STABLE GET get_leaderboard_page RPC and parses rows, podium, counts, and totalCount', async () => {
    const row1 = {
        model_name: 'deepseek-flash',
        display_name: 'deepseek-flash',
        entity_type: 'llm',
        portfolio_id: 'port-1',
        recipe_id: null,
        is_live: true,
        total_equity: 10820,
        return_pct: 8.2,
        realized_pnl: 820,
        win_rate: 68.2,
        total_trades: 15,
        average_confidence: 85.0,
        conviction_score: 62.5,
        api_success_rate: 100.0,
        trading_activity_rate: 90.0,
        trading_performance_score: 85.2,
        reasoning_quality_score: 62.5,
        consistency_score: 64.0,
        up_days: 7,
        active_days: 10,
        composite_score: 89.5,
        rank: 1,
        total_count: 14,
        all_count: 14,
        llm_count: 5,
        system_count: 6,
        user_bot_count: 3,
        is_podium: true,
        is_page_row: true,
    };
    const row2 = {
        ...row1,
        model_name: 'sys-pead-drift',
        display_name: 'sys-pead-drift',
        entity_type: 'system',
        portfolio_id: 'port-sys-1',
        conviction_score: null,
        average_confidence: null,
        reasoning_quality_score: null,
        composite_score: 70.3,
        rank: 2,
    };
    const podiumOnlyRow = {
        ...row1,
        model_name: 'user-bot:rec-123',
        display_name: 'Momentum Scanner',
        entity_type: 'user_bot',
        portfolio_id: null,
        recipe_id: 'rec-123',
        conviction_score: null,
        average_confidence: null,
        reasoning_quality_score: null,
        composite_score: 65.0,
        rank: 3,
        is_podium: true,
        is_page_row: false,
    };

    mockSupabaseClient = {
        rpc: vi.fn().mockResolvedValue({ data: [row1, row2, podiumOnlyRow], error: null }),
    };

    const result = await fetchLeaderboardPage({
        timeWindowDays: 30,
        category: 'all',
        sortBy: 'composite_score',
        sortDir: 'desc',
        page: 1,
        pageSize: 10,
    });

    expect(mockSupabaseClient.rpc).toHaveBeenCalledWith(
        'get_leaderboard_page',
        {
            p_time_window_days: 30,
            p_category: 'all',
            p_sort_by: 'composite_score',
            p_sort_dir: 'desc',
            p_limit: 10,
            p_offset: 0,
        },
        { get: true },
    );

    expect(result.rows).toHaveLength(2);
    expect(result.podium).toHaveLength(3);
    expect(result.totalCount).toBe(14);
    expect(result.counts).toEqual({
        all: 14,
        llm: 5,
        system: 6,
        user_bot: 3,
    });
});

test('fetchLeaderboard calls STABLE GET get_llm_leaderboard_metrics RPC directly without redundant JS filtering', async () => {
    const mockData = [
        {
            model_name: 'deepseek-flash',
            display_name: 'deepseek-flash',
            entity_type: 'llm',
            portfolio_id: 'port-1',
            recipe_id: null,
            is_live: true,
            total_equity: 10820,
            return_pct: 8.2,
            realized_pnl: 820,
            win_rate: 68.2,
            total_trades: 15,
            average_confidence: 85.0,
            conviction_score: 62.5,
            api_success_rate: 100.0,
            trading_activity_rate: 90.0,
            trading_performance_score: 85.2,
            reasoning_quality_score: 62.5,
            consistency_score: 64.0,
            up_days: 7,
            active_days: 10,
            composite_score: 89.5,
        },
    ];

    mockSupabaseClient = {
        rpc: vi.fn().mockResolvedValue({ data: mockData, error: null }),
    };

    const result = await fetchLeaderboard(null);

    expect(mockSupabaseClient.rpc).toHaveBeenCalledWith(
        'get_llm_leaderboard_metrics',
        { time_window_days: null },
        { get: true },
    );
    expect(result).toHaveLength(1);
});

test('fetchLeaderboardPage propagates database errors', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const dbError = new Error('Database connection failed');
    mockSupabaseClient = {
        rpc: vi.fn().mockResolvedValue({ data: null, error: dbError }),
    };

    await expect(fetchLeaderboardPage({ timeWindowDays: 7 })).rejects.toThrow(
        'Database connection failed',
    );
    consoleSpy.mockRestore();
});
