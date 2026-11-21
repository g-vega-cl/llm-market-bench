import {
    Badge,
    Button,
    Card,
    EmptyState,
    ErrorCard,
    MetricTile,
    PageLayout,
    SectionHeading,
    Select,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@llm-market-bench/ui-design-system';
import { Fragment } from 'react';
import type { LlmLogEntry, LlmLogsFilter, LlmLogsResponse } from './llm-logs-types';

interface LlmLogsPageProps {
    data: LlmLogsResponse | null;
    errorMessage?: string | null;
    isLoading?: boolean;
    filter: LlmLogsFilter;
    onFilterChange: (next: LlmLogsFilter) => void;
    onRefresh: () => void;
}

function statusBadgeColor(statusCode: number): 'success' | 'warning' | 'danger' | 'neutral' {
    if (statusCode >= 200 && statusCode < 300) return 'success';
    if (statusCode === 429) return 'warning';
    if (statusCode >= 400) return 'danger';
    return 'neutral';
}

function formatTimestamp(iso: string): string {
    if (!iso) return '-';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toISOString().replace('T', ' ').slice(0, 19);
}

function formatNumber(n: number): string {
    return new Intl.NumberFormat('en-US').format(Math.round(n));
}

function LogRowDetail({ entry }: { entry: LlmLogEntry }) {
    const hasDetail =
        entry.prompt_preview ||
        entry.error_message ||
        entry.failover_chain.length > 0 ||
        entry.purpose ||
        entry.client_ip;

    if (!hasDetail) return null;

    return (
        <TableRow>
            <TableCell colSpan={7}>
                <div className="voxel-trough rounded-none p-3 flex flex-col gap-2">
                    <div className="flex flex-wrap items-center gap-4 text-xs font-normal text-voxel-muted">
                        {entry.purpose && (
                            <span className="whitespace-nowrap">purpose: {entry.purpose}</span>
                        )}
                        {entry.client_ip && (
                            <span className="whitespace-nowrap font-mono">
                                ip: {entry.client_ip}
                            </span>
                        )}
                        <span className="whitespace-nowrap font-mono">
                            model: {entry.routed_model}
                        </span>
                        {entry.is_stream === 1 && (
                            <span className="whitespace-nowrap font-mono tabular-nums">
                                ttft: {Math.round(entry.ttft_ms)}ms
                            </span>
                        )}
                        {entry.failover_chain.length > 0 && (
                            <span>failover: {entry.failover_chain.join(' -> ')}</span>
                        )}
                    </div>
                    {entry.prompt_preview && (
                        <div className="text-xs font-normal text-voxel-ink font-mono whitespace-pre-wrap break-words">
                            {entry.prompt_preview}
                        </div>
                    )}
                    {entry.error_message && (
                        <div className="text-xs font-normal text-danger font-mono whitespace-pre-wrap break-words">
                            {entry.error_message}
                        </div>
                    )}
                </div>
            </TableCell>
        </TableRow>
    );
}

function LlmLogsHeader({
    data,
    isLoading,
    filter,
    onFilterChange,
    onRefresh,
}: {
    data: LlmLogsResponse | null;
    isLoading: boolean;
    filter: LlmLogsFilter;
    onFilterChange: (next: LlmLogsFilter) => void;
    onRefresh: () => void;
}) {
    const metrics = data?.metrics;
    const providerNames = metrics ? Object.keys(metrics.providers ?? {}).sort() : [];

    return (
        <Card className="p-4 flex flex-col gap-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex flex-col gap-1">
                    <div className="flex flex-wrap items-center gap-2">
                        <h1 className="text-lg font-bold text-voxel-ink uppercase tracking-wider">
                            Free LLM Proxy Logs
                        </h1>
                        <Badge colorScheme="accent" variant="solid" size="xs">
                            PRIVATE
                        </Badge>
                        {metrics?.connector_id && (
                            <Badge colorScheme="info" variant="soft" size="xs">
                                {metrics.connector_id}
                            </Badge>
                        )}
                        {metrics?.security_alert_active && (
                            <Badge colorScheme="danger" variant="solid" size="xs">
                                401 SPIKE
                            </Badge>
                        )}
                    </div>
                    <p className="text-xs font-normal text-voxel-muted font-mono">
                        {data?.proxyUrl ?? 'https://llm.clvg.uk/v1'}
                        {data?.isFallbackRecentOnly ? ' (showing recent 10 from /v1/metrics)' : ''}
                    </p>
                </div>
                <Button
                    type="button"
                    variant="solid"
                    size="sm"
                    onClick={onRefresh}
                    disabled={isLoading}
                >
                    {isLoading ? 'Refreshing...' : 'Refresh'}
                </Button>
            </div>

            <div className="flex flex-wrap items-center gap-4">
                <div className="w-44">
                    <Select
                        aria-label="Filter by status"
                        value={filter.status_code !== undefined ? String(filter.status_code) : ''}
                        onChange={(e) =>
                            onFilterChange({
                                ...filter,
                                offset: 0,
                                status_code: e.target.value ? Number(e.target.value) : undefined,
                            })
                        }
                        options={[
                            { label: 'All Statuses', value: '' },
                            { label: '200 OK', value: '200' },
                            { label: '401 Unauthorized', value: '401' },
                            { label: '429 Rate Limited', value: '429' },
                            { label: '502/503 Error', value: '503' },
                        ]}
                    />
                </div>
                <div className="w-44">
                    <Select
                        aria-label="Filter by provider"
                        value={filter.provider ?? ''}
                        onChange={(e) =>
                            onFilterChange({
                                ...filter,
                                offset: 0,
                                provider: e.target.value || undefined,
                            })
                        }
                        options={[
                            { label: 'All Providers', value: '' },
                            ...providerNames.map((p) => ({ label: p, value: p })),
                        ]}
                    />
                </div>
                <div className="w-40">
                    <Select
                        aria-label="Filter by billing"
                        value={filter.billing ?? ''}
                        onChange={(e) =>
                            onFilterChange({
                                ...filter,
                                offset: 0,
                                billing: e.target.value || undefined,
                            })
                        }
                        options={[
                            { label: 'All Billing', value: '' },
                            { label: 'Free Tier', value: 'free' },
                            { label: 'Paid Fallback', value: 'paid' },
                        ]}
                    />
                </div>
                <div className="w-36">
                    <Select
                        aria-label="Rows per page"
                        value={String(filter.limit ?? 50)}
                        onChange={(e) =>
                            onFilterChange({
                                ...filter,
                                offset: 0,
                                limit: Number(e.target.value),
                            })
                        }
                        options={[
                            { label: '25 rows', value: '25' },
                            { label: '50 rows', value: '50' },
                            { label: '100 rows', value: '100' },
                            { label: '200 rows', value: '200' },
                        ]}
                    />
                </div>
            </div>
        </Card>
    );
}

export function LlmLogsPage({
    data,
    errorMessage,
    isLoading = false,
    filter,
    onFilterChange,
    onRefresh,
}: LlmLogsPageProps) {
    const metrics = data?.metrics;

    return (
        <PageLayout maxWidth="xl" className="flex flex-col gap-6">
            {/* Block 1: Header & Filters */}
            <LlmLogsHeader
                data={data}
                isLoading={isLoading}
                filter={filter}
                onFilterChange={onFilterChange}
                onRefresh={onRefresh}
            />

            {/* Block 2: Summary Telemetry */}
            {errorMessage && <ErrorCard title="Proxy Telemetry Error" message={errorMessage} />}

            {metrics && (
                <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,12rem),1fr))] gap-4 items-stretch">
                    <MetricTile
                        label="Total Requests"
                        value={formatNumber(metrics.total_requests)}
                    />
                    <MetricTile
                        label="Success Rate"
                        value={`${metrics.success_rate_pct.toFixed(1)}%`}
                    />
                    <MetricTile label="Total Tokens" value={formatNumber(metrics.total_tokens)} />
                    <MetricTile
                        label="Avg Latency"
                        value={`${Math.round(metrics.avg_latency_ms)}ms`}
                    />
                    <MetricTile
                        label="Paid Calls (24h)"
                        value={formatNumber(metrics.paid_calls_24h)}
                    />
                </div>
            )}

            {/* Block 3: Call Logs Table */}
            <Card className="p-4 flex flex-col gap-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                    <SectionHeading>Call Audit Stream</SectionHeading>
                    {data && (
                        <span className="text-xs font-normal text-voxel-muted font-mono tabular-nums">
                            {data.logs.length} of {formatNumber(data.total)} calls
                        </span>
                    )}
                </div>

                {!data || data.logs.length === 0 ? (
                    <EmptyState
                        title="No proxy calls recorded"
                        subtitle="No call_logs matched the active filters."
                    />
                ) : (
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Timestamp (UTC)</TableHead>
                                <TableHead>Requested</TableHead>
                                <TableHead>Provider</TableHead>
                                <TableHead>Billing</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead align="right">Tokens</TableHead>
                                <TableHead align="right">Latency</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {data.logs.map((entry) => (
                                <Fragment key={entry.id}>
                                    <TableRow>
                                        <TableCell className="font-mono whitespace-nowrap">
                                            {formatTimestamp(entry.timestamp)}
                                        </TableCell>
                                        <TableCell className="font-mono">
                                            {entry.requested_model}
                                        </TableCell>
                                        <TableCell className="font-mono">
                                            {entry.routed_provider}
                                        </TableCell>
                                        <TableCell>
                                            <Badge
                                                colorScheme={
                                                    entry.billing === 'paid' ? 'warning' : 'neutral'
                                                }
                                                variant="soft"
                                                size="xs"
                                            >
                                                {entry.billing}
                                            </Badge>
                                        </TableCell>
                                        <TableCell>
                                            <Badge
                                                colorScheme={statusBadgeColor(entry.status_code)}
                                                variant="soft"
                                                size="xs"
                                            >
                                                {entry.status_code}
                                            </Badge>
                                        </TableCell>
                                        <TableCell align="right" className="font-mono tabular-nums">
                                            {formatNumber(entry.total_tokens)}
                                        </TableCell>
                                        <TableCell align="right" className="font-mono tabular-nums">
                                            {Math.round(entry.latency_ms)}ms
                                        </TableCell>
                                    </TableRow>
                                    <LogRowDetail entry={entry} />
                                </Fragment>
                            ))}
                        </TableBody>
                    </Table>
                )}
            </Card>
        </PageLayout>
    );
}
