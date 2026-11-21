import { createServerFn } from '@tanstack/react-start';
import {
    isAllowedLlmLogsEmail,
    type LlmLogEntry,
    type LlmLogsFilter,
    type LlmLogsResponse,
    type LlmMetricsSummary,
} from './llm-logs-types';

const DEFAULT_PROXY_URL = 'https://llm.clvg.uk/v1';

function resolveProxyConfig(): { baseUrl: string; apiKey: string } {
    const baseUrl = (process.env.FREE_LLM_PROXY_URL || DEFAULT_PROXY_URL).replace(/\/$/, '');
    const apiKey = process.env.FREE_PROXY_MASTER_KEY || process.env.STRATA_API_KEY || '';
    return { baseUrl, apiKey };
}

function normalizeFailoverChain(raw: unknown): string[] {
    if (Array.isArray(raw)) {
        return raw.map((item) => String(item));
    }
    if (typeof raw === 'string' && raw.trim()) {
        try {
            const parsed = JSON.parse(raw);
            if (Array.isArray(parsed)) {
                return parsed.map((item) => String(item));
            }
        } catch {
            return [raw];
        }
    }
    return [];
}

function str(val: unknown, fallback = ''): string {
    return val == null ? fallback : String(val);
}

function nullableStr(val: unknown): string | null {
    return val ? String(val) : null;
}

function num(val: unknown, fallback = 0): number {
    return val == null ? fallback : Number(val);
}

function normalizeLogEntry(row: Record<string, unknown>): LlmLogEntry {
    const latency = num(row.latency_ms);
    return {
        id: str(row.id),
        timestamp: str(row.timestamp),
        requested_model: str(row.requested_model),
        routed_provider: str(row.routed_provider, 'none'),
        routed_model: str(row.routed_model, 'none'),
        prompt_tokens: num(row.prompt_tokens),
        completion_tokens: num(row.completion_tokens),
        total_tokens: num(row.total_tokens),
        latency_ms: latency,
        status_code: num(row.status_code),
        failover_chain: normalizeFailoverChain(row.failover_chain),
        error_message: nullableStr(row.error_message),
        client_ip: nullableStr(row.client_ip),
        user_agent: nullableStr(row.user_agent),
        purpose: nullableStr(row.purpose),
        prompt_preview: nullableStr(row.prompt_preview),
        is_stream: num(row.is_stream),
        usage_available: num(row.usage_available),
        ttft_ms: num(row.ttft_ms),
        duration_ms: num(row.duration_ms, latency),
        stream_completed: num(row.stream_completed),
        billing: str(row.billing, 'free'),
    };
}

export async function fetchLlmLogsData(filter: LlmLogsFilter = {}): Promise<LlmLogsResponse> {
    const { getAuthServerClient } = await import('~/lib/auth');
    const authClient = getAuthServerClient();
    const { data, error } = await authClient.auth.getUser();

    if (error || !data?.user) {
        throw new Error('Authentication required');
    }
    if (!isAllowedLlmLogsEmail(data.user.email)) {
        throw new Error('Restricted to authorized accounts');
    }

    const { baseUrl, apiKey } = resolveProxyConfig();
    if (!apiKey) {
        throw new Error('FREE_PROXY_MASTER_KEY is not configured on the server');
    }

    const headers = {
        Authorization: `Bearer ${apiKey}`,
    };

    const limit = Math.max(1, Math.min(filter.limit ?? 50, 200));
    const offset = Math.max(0, filter.offset ?? 0);
    const params = new URLSearchParams({
        limit: String(limit),
        offset: String(offset),
    });
    if (filter.status_code !== undefined) {
        params.set('status_code', String(filter.status_code));
    }
    if (filter.provider) {
        params.set('provider', filter.provider);
    }
    if (filter.billing) {
        params.set('billing', filter.billing);
    }

    const [metricsRes, logsRes] = await Promise.all([
        fetch(`${baseUrl}/metrics`, { headers, signal: AbortSignal.timeout(10_000) }),
        fetch(`${baseUrl}/logs?${params.toString()}`, {
            headers,
            signal: AbortSignal.timeout(10_000),
        }),
    ]);

    if (!metricsRes.ok) {
        throw new Error(`Free LLM proxy metrics failed (${metricsRes.status})`);
    }

    const rawMetrics = (await metricsRes.json()) as LlmMetricsSummary & {
        recent_calls?: Array<Record<string, unknown>>;
    };
    const { recent_calls: recentCalls, ...metrics } = rawMetrics;

    if (logsRes.ok) {
        const logsPayload = (await logsRes.json()) as {
            total?: number;
            logs?: Array<Record<string, unknown>>;
        };
        const logs = (logsPayload.logs ?? []).map(normalizeLogEntry);
        return {
            metrics,
            logs,
            total: Number(logsPayload.total ?? logs.length),
            isFallbackRecentOnly: false,
            proxyUrl: baseUrl,
        };
    }

    if (logsRes.status === 404) {
        const fallbackLogs = (recentCalls ?? []).map(normalizeLogEntry);
        return {
            metrics,
            logs: fallbackLogs,
            total: fallbackLogs.length,
            isFallbackRecentOnly: true,
            proxyUrl: baseUrl,
        };
    }

    throw new Error(`Free LLM proxy logs failed (${logsRes.status})`);
}

export const fetchLlmLogsFn = createServerFn({ method: 'GET' })
    .validator((d: LlmLogsFilter | undefined) => d ?? {})
    .handler(async ({ data }) => fetchLlmLogsData(data));
