import { expect, test, vi } from 'vitest';

interface PriceHistoryRecord {
    ticker: string;
    price: number;
    fetched_at: string;
}

interface MockSupabaseChain {
    [key: string]: ReturnType<typeof vi.fn>;
}

let mockSupabaseClient: MockSupabaseChain | null = null;

vi.mock('~/lib/supabase', () => ({
    getSupabaseServerClient: vi.fn(() => mockSupabaseClient),
}));

import { fetchBenchmarkHistory, fetchPortfolios } from './fetch-portfolios';

vi.mock('../lib/config', () => ({
    getActiveOwnerIds: vi.fn(() => ['gemini-3.1-flash-lite', 'deepseek-v4-pro']),
    isAutoresearchPortfolio: vi.fn((id) =>
        ['gemini-3.1-flash-lite', 'deepseek-v4-pro'].includes(id),
    ),
    normalizeOwnerId: vi.fn((id) => id.toLowerCase().replace(/\s+/g, '-')),
}));

function createMockSupabaseClient(mockData: PriceHistoryRecord[]): MockSupabaseChain {
    const chain: MockSupabaseChain = {
        order: vi.fn(() => Promise.resolve({ data: mockData, error: null })),
        lte: vi.fn(() => chain),
        gte: vi.fn(() => chain),
        in: vi.fn(() => chain),
        select: vi.fn(() => chain),
        from: vi.fn(() => chain),
    };

    return chain;
}

test('fetchBenchmarkHistory deduplicates by date keeping latest price', async () => {
    const mockClient = createMockSupabaseClient([
        { ticker: 'SPY', price: 100.0, fetched_at: '2024-01-01T10:00:00Z' },
        { ticker: 'SPY', price: 101.5, fetched_at: '2024-01-01T14:30:00Z' },
        { ticker: 'SPY', price: 102.0, fetched_at: '2024-01-02T10:00:00Z' },
    ]);
    mockSupabaseClient = mockClient;

    const result = await fetchBenchmarkHistory(['SPY'], '2024-01-01', '2024-01-02');

    expect(mockClient.from).toHaveBeenCalledWith('price_history');

    expect(result.SPY).toHaveLength(2);
    expect(result.SPY[0].date).toBe('2024-01-01');
    // Should keep the later price from the same day
    expect(result.SPY[0].price).toBe(101.5);
    expect(result.SPY[1].date).toBe('2024-01-02');
    expect(result.SPY[1].price).toBe(102.0);
});

test('fetchBenchmarkHistory returns empty object for empty tickers', async () => {
    mockSupabaseClient = createMockSupabaseClient([]);
    const result = await fetchBenchmarkHistory([], '2024-01-01', '2024-01-02');
    expect(result).toEqual({});
});

test('fetchBenchmarkHistory keeps only last price per day for multiple tickers', async () => {
    const mockClient = createMockSupabaseClient([
        { ticker: 'SPY', price: 100.0, fetched_at: '2024-01-01T10:00:00Z' },
        { ticker: 'SPY', price: 101.0, fetched_at: '2024-01-01T15:00:00Z' },
        { ticker: 'QQQ', price: 200.0, fetched_at: '2024-01-01T10:00:00Z' },
        { ticker: 'QQQ', price: 202.0, fetched_at: '2024-01-01T15:00:00Z' },
    ]);
    mockSupabaseClient = mockClient;

    const result = await fetchBenchmarkHistory(['SPY', 'QQQ'], '2024-01-01', '2024-01-01');

    expect(result.SPY).toHaveLength(1);
    expect(result.SPY[0].price).toBe(101.0);
    expect(result.QQQ).toHaveLength(1);
    expect(result.QQQ[0].price).toBe(202.0);
});

test('fetchPortfolios tags portfolios with is_autoresearch correctly', async () => {
    const mockData = [
        { id: '1', owner_id: 'gemini-3.1-flash-lite', total_equity: 10000, cash_balance: 5000 },
        { id: '2', owner_id: 'deepseek-v4-pro', total_equity: 12000, cash_balance: 6000 },
        { id: '3', owner_id: 'gpt-5.4-nano', total_equity: 8000, cash_balance: 4000 },
    ];

    const chain = {
        order: vi.fn(() => Promise.resolve({ data: mockData, error: null })),
        select: vi.fn(() => chain),
        from: vi.fn(() => chain),
    };
    mockSupabaseClient = chain as unknown as MockSupabaseChain;

    const result = await fetchPortfolios();

    expect(result).toHaveLength(3);
    expect(result.find((p) => p.owner_id === 'gemini-3.1-flash-lite')?.is_autoresearch).toBe(true);
    expect(result.find((p) => p.owner_id === 'deepseek-v4-pro')?.is_autoresearch).toBe(true);
    expect(result.find((p) => p.owner_id === 'gpt-5.4-nano')?.is_autoresearch).toBe(false);
});
