export const ALLOWED_LLM_LOGS_EMAILS = ['g.vega.cl@gmail.com'] as const;

export function isAllowedLlmLogsEmail(email: string | null | undefined): boolean {
    if (!email) return false;
    const normalized = email.trim().toLowerCase();
    return ALLOWED_LLM_LOGS_EMAILS.some((allowed) => allowed.toLowerCase() === normalized);
}

export interface LlmLogEntry {
    id: string;
    timestamp: string;
    requested_model: string;
    routed_provider: string;
    routed_model: string;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    latency_ms: number;
    status_code: number;
    failover_chain: string[];
    error_message: string | null;
    client_ip: string | null;
    user_agent: string | null;
    purpose: string | null;
    prompt_preview: string | null;
    is_stream: number;
    usage_available: number;
    ttft_ms: number;
    duration_ms: number;
    stream_completed: number;
    billing: string;
}

export interface LlmProviderStats {
    requests: number;
    tokens: number;
    avg_latency_ms: number;
}

export interface LlmCircuitStatus {
    status: string;
    cooldown_remaining_s?: number;
}

export interface LlmMetricsSummary {
    total_requests: number;
    successful_requests: number;
    unauthorized_requests: number;
    success_rate_pct: number;
    total_tokens: number;
    avg_latency_ms: number;
    avg_ttft_ms: number;
    paid_calls_total: number;
    paid_calls_24h: number;
    paid_tokens_24h: number;
    connector_id?: string;
    security_alert_active?: boolean;
    providers: Record<string, LlmProviderStats>;
    circuit_breaker?: Record<string, LlmCircuitStatus>;
}

export interface LlmLogsFilter {
    limit?: number;
    offset?: number;
    status_code?: number;
    provider?: string;
    billing?: string;
}

export interface LlmLogsResponse {
    metrics: LlmMetricsSummary;
    logs: LlmLogEntry[];
    total: number;
    isFallbackRecentOnly: boolean;
    proxyUrl: string;
}
