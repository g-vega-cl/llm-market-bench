import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { LlmLogsPage } from './LlmLogsPage';
import type { LlmLogsResponse } from './llm-logs-types';

describe('LlmLogsPage', () => {
    const sampleData: LlmLogsResponse = {
        proxyUrl: 'https://llm.clvg.uk/v1',
        total: 1,
        isFallbackRecentOnly: false,
        metrics: {
            total_requests: 120,
            successful_requests: 118,
            unauthorized_requests: 0,
            success_rate_pct: 98.3,
            total_tokens: 45200,
            avg_latency_ms: 280.4,
            avg_ttft_ms: 95.1,
            paid_calls_total: 0,
            paid_calls_24h: 0,
            paid_tokens_24h: 0,
            connector_id: 'minipc-edge',
            providers: {
                groq: { requests: 100, tokens: 40000, avg_latency_ms: 250 },
            },
        },
        logs: [
            {
                id: 'call_1',
                timestamp: '2026-11-21T18:10:00+00:00',
                requested_model: 'auto-go',
                routed_provider: 'groq',
                routed_model: 'llama-3.3-70b',
                prompt_tokens: 100,
                completion_tokens: 50,
                total_tokens: 150,
                latency_ms: 240,
                status_code: 200,
                failover_chain: ['cerebras (HTTP 429)'],
                error_message: null,
                client_ip: '100.64.0.2',
                user_agent: 'benchify',
                purpose: 'recipe-builder',
                prompt_preview: 'Build a momentum bot for NVDA',
                is_stream: 0,
                usage_available: 1,
                ttft_ms: 0,
                duration_ms: 240,
                stream_completed: 0,
                billing: 'free',
            },
        ],
    };

    it('renders summary telemetry, table rows, and in-flow trough details', () => {
        render(
            <LlmLogsPage
                data={sampleData}
                filter={{ limit: 50 }}
                onFilterChange={vi.fn()}
                onRefresh={vi.fn()}
            />,
        );

        expect(screen.getByText('Free LLM Proxy Logs')).toBeInTheDocument();
        expect(screen.getByText('98.3%')).toBeInTheDocument();
        expect(screen.getByText('45,200')).toBeInTheDocument();
        expect(screen.getByText('auto-go')).toBeInTheDocument();
        expect(screen.getByText('purpose: recipe-builder')).toBeInTheDocument();
        expect(screen.getByText('Build a momentum bot for NVDA')).toBeInTheDocument();
        expect(screen.getByText('failover: cerebras (HTTP 429)')).toBeInTheDocument();
    });
});
