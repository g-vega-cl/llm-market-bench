import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchLlmLogsData } from './llm-logs-server';

const mockGetUser = vi.fn();

vi.mock('~/lib/auth', () => ({
    getAuthServerClient: () => ({
        auth: {
            getUser: mockGetUser,
        },
    }),
}));

describe('llm-logs server handler (fetchLlmLogsData)', () => {
    const originalEnv = process.env;

    beforeEach(() => {
        vi.clearAllMocks();
        global.fetch = vi.fn();
        process.env = {
            ...originalEnv,
            FREE_LLM_PROXY_URL: 'https://llm.clvg.uk/v1',
            FREE_PROXY_MASTER_KEY: 'test-master-key',
        };
    });

    it('rejects unauthenticated visitors without calling the proxy', async () => {
        mockGetUser.mockResolvedValue({ data: { user: null }, error: null });

        await expect(fetchLlmLogsData({})).rejects.toThrow('Authentication required');
        expect(global.fetch).not.toHaveBeenCalled();
    });

    it('rejects authenticated users other than g.vega.cl@gmail.com without calling the proxy', async () => {
        mockGetUser.mockResolvedValue({
            data: { user: { id: 'u2', email: 'other@example.com' } },
            error: null,
        });

        await expect(fetchLlmLogsData({})).rejects.toThrow('Restricted to authorized accounts');
        expect(global.fetch).not.toHaveBeenCalled();
    });

    it('fetches metrics and logs with Bearer auth for g.vega.cl@gmail.com', async () => {
        mockGetUser.mockResolvedValue({
            data: { user: { id: 'u1', email: 'g.vega.cl@gmail.com' } },
            error: null,
        });

        const mockMetrics = {
            total_requests: 42,
            successful_requests: 40,
            unauthorized_requests: 0,
            success_rate_pct: 95.2,
            total_tokens: 12000,
            avg_latency_ms: 320.5,
            avg_ttft_ms: 110.2,
            paid_calls_total: 1,
            paid_calls_24h: 0,
            paid_tokens_24h: 0,
            providers: { groq: { requests: 40, tokens: 12000, avg_latency_ms: 320.5 } },
            recent_calls: [],
            circuit_breaker: { groq: { status: 'healthy', cooldown_remaining_s: 0 } },
        };

        const mockLogs = {
            total: 1,
            limit: 50,
            offset: 0,
            logs: [
                {
                    id: 'call_abc123',
                    timestamp: '2026-11-21T18:00:00+00:00',
                    requested_model: 'auto-go',
                    routed_provider: 'groq',
                    routed_model: 'llama-3.3-70b',
                    prompt_tokens: 100,
                    completion_tokens: 50,
                    total_tokens: 150,
                    latency_ms: 210.5,
                    status_code: 200,
                    failover_chain: [],
                    error_message: null,
                    client_ip: '127.0.0.1',
                    user_agent: 'python-httpx/0.28',
                    purpose: 'recipe-builder',
                    prompt_preview: 'Build a momentum strategy',
                    is_stream: 0,
                    usage_available: 1,
                    ttft_ms: 0,
                    duration_ms: 210.5,
                    stream_completed: 0,
                    billing: 'free',
                },
            ],
        };

        (global.fetch as ReturnType<typeof vi.fn>)
            .mockResolvedValueOnce({ ok: true, status: 200, json: async () => mockMetrics })
            .mockResolvedValueOnce({ ok: true, status: 200, json: async () => mockLogs });

        const result = await fetchLlmLogsData({ limit: 50, provider: 'groq' });

        expect(global.fetch).toHaveBeenCalledTimes(2);
        const [metricsUrl, metricsInit] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
        const [logsUrl, logsInit] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[1];

        expect(metricsUrl).toBe('https://llm.clvg.uk/v1/metrics');
        expect(metricsInit.headers.Authorization).toBe('Bearer test-master-key');
        expect(logsUrl).toBe('https://llm.clvg.uk/v1/logs?limit=50&offset=0&provider=groq');
        expect(logsInit.headers.Authorization).toBe('Bearer test-master-key');

        expect(result.metrics.total_requests).toBe(42);
        expect(result.logs).toHaveLength(1);
        expect(result.logs[0].id).toBe('call_abc123');
    });

    it('falls back to metrics.recent_calls when /v1/logs returns 404', async () => {
        mockGetUser.mockResolvedValue({
            data: { user: { id: 'u1', email: 'G.Vega.Cl@gmail.com' } },
            error: null,
        });

        const mockMetrics = {
            total_requests: 1,
            successful_requests: 1,
            unauthorized_requests: 0,
            success_rate_pct: 100,
            total_tokens: 500,
            avg_latency_ms: 150,
            avg_ttft_ms: 0,
            paid_calls_total: 0,
            paid_calls_24h: 0,
            paid_tokens_24h: 0,
            providers: {},
            recent_calls: [
                {
                    id: 'call_fallback',
                    timestamp: '2026-11-21T18:00:00+00:00',
                    requested_model: 'auto-go',
                    routed_provider: 'cerebras',
                    routed_model: 'llama3.1-8b',
                    prompt_tokens: 300,
                    completion_tokens: 200,
                    total_tokens: 500,
                    latency_ms: 150,
                    status_code: 200,
                    failover_chain: '["groq (HTTP 429)"]',
                    error_message: null,
                    client_ip: '10.0.0.1',
                    user_agent: 'benchify',
                    purpose: 'auto-wiki',
                    prompt_preview: 'Diff summary',
                    is_stream: 0,
                    usage_available: 1,
                    ttft_ms: 0,
                    duration_ms: 150,
                    stream_completed: 0,
                    billing: 'free',
                },
            ],
        };

        (global.fetch as ReturnType<typeof vi.fn>)
            .mockResolvedValueOnce({ ok: true, status: 200, json: async () => mockMetrics })
            .mockResolvedValueOnce({ ok: false, status: 404 });

        const result = await fetchLlmLogsData({});
        expect(result.logs).toHaveLength(1);
        expect(result.logs[0].failover_chain).toEqual(['groq (HTTP 429)']);
        expect(result.isFallbackRecentOnly).toBe(true);
    });

    it('never exposes env var or API key names when proxy credentials are missing', async () => {
        mockGetUser.mockResolvedValue({
            data: { user: { id: 'u1', email: 'g.vega.cl@gmail.com' } },
            error: null,
        });
        delete process.env.FREE_PROXY_MASTER_KEY;
        delete process.env.STRATA_API_KEY;

        let caught: Error | null = null;
        try {
            await fetchLlmLogsData({});
        } catch (err) {
            caught = err as Error;
        }

        expect(caught).not.toBeNull();
        expect(caught?.message).toBe('Proxy authentication is not configured on the server');
        expect(caught?.message).not.toContain('FREE_PROXY_MASTER_KEY');
        expect(caught?.message).not.toContain('STRATA_API_KEY');
    });
});
