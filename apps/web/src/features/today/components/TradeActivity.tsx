import { Badge, MetricTile, SectionHeading, StatPill } from '@llm-market-bench/ui-design-system';
import * as React from 'react';
import { getAgentInfo } from '../lib/agent-info';
import { ExecutionTraceView } from './ExecutionTraceView';

interface TradeItem {
    id: string;
    decision_id?: string | null;
    executed_at: string | null;
    signal: string;
    ticker: string;
    quantity?: number;
    price: number | string;
    portfolios?: { owner_id?: string };
    decisions?: DecisionItem | DecisionItem[] | null;
    reasoning?: string | null;
    // biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
    metadata?: Record<string, any> | null;
    formattedTime?: string;
}

interface DecisionItem {
    id: string;
    trade_id?: string | null;
    status?: string | null;
    created_at: string | null;
    reasoning?: string;
    model_name?: string;
    confidence_score?: number;
    // biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
    metadata?: Record<string, any> | null;
    ticker: string;
    formattedTime?: string;
}

interface TradeActivityProps {
    trades: TradeItem[];
    decisions: DecisionItem[];
}

type ActivityItem =
    | (TradeItem & {
          type: 'TRADE';
          timestamp: string | null;
          reasoning: string;
          model_name?: string;
          confidence?: number;
          // biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
          metadata?: Record<string, any> | null;
      })
    | (DecisionItem & {
          type: 'REJECTION';
          timestamp: string | null;
          formattedTime?: string;
          reasoning?: string;
          model_name?: string;
          confidence?: number;
      });

type FilterType = 'ALL' | 'BUY' | 'SELL' | 'REJECTED' | 'EXECUTED';

export function TradeActivity({ trades, decisions }: TradeActivityProps) {
    const [expandedIdx, setExpandedIdx] = React.useState<number | null>(null);
    const [filter, setFilter] = React.useState<FilterType>('ALL');

    // Include rejections from decisions
    const rejections = decisions.filter((d) => d.status?.startsWith('REJECTED'));

    // Normalize and sort all activity
    const allActivity = React.useMemo(() => {
        const activity: ActivityItem[] = [
            ...trades.map((t) => {
                const nestedDec = Array.isArray(t.decisions) ? t.decisions[0] : t.decisions;
                const decision =
                    nestedDec ||
                    decisions.find(
                        (d) => d.id === t.decision_id || (d.trade_id && d.trade_id === t.id),
                    );
                return {
                    ...t,
                    type: 'TRADE' as const,
                    timestamp: t.executed_at,
                    reasoning:
                        decision?.reasoning ||
                        t.reasoning ||
                        'No reasoning found for this execution.',
                    model_name: decision?.model_name || t.portfolios?.owner_id,
                    confidence: decision?.confidence_score,
                    metadata: decision?.metadata || t.metadata,
                    formattedTime: t.formattedTime,
                };
            }),
            ...rejections.map((r) => ({
                ...r,
                type: 'REJECTION' as const,
                timestamp: r.created_at,
                formattedTime: r.formattedTime,
            })),
        ].sort((a, b) => (b.timestamp || '').localeCompare(a.timestamp || ''));

        // Apply filter
        if (filter === 'ALL') return activity;
        if (filter === 'BUY')
            return activity.filter((item) => item.type === 'TRADE' && item.signal === 'BUY');
        if (filter === 'SELL')
            return activity.filter((item) => item.type === 'TRADE' && item.signal === 'SELL');
        if (filter === 'REJECTED') return activity.filter((item) => item.type === 'REJECTION');
        if (filter === 'EXECUTED') return activity.filter((item) => item.type === 'TRADE');

        return activity;
    }, [trades, decisions, rejections, filter]);

    // Calculate stats
    const totalActivity = trades.length + rejections.length;
    const totalTrades = trades.length;
    const buyTrades = trades.filter((t) => t.signal === 'BUY').length;
    const sellTrades = trades.filter((t) => t.signal === 'SELL').length;
    const rejectionCount = rejections.length;

    return (
        <section className="flex flex-col gap-6 animate-slide-up">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <SectionHeading gradient="success">Market Execution & Guardrails</SectionHeading>

                {/* Activity Stats */}
                <div className="flex flex-wrap items-center gap-3">
                    <StatPill
                        label="Total"
                        value={totalActivity}
                        colorScheme="neutral"
                        isActive={filter === 'ALL'}
                        onClick={() => setFilter('ALL')}
                    />
                    <StatPill
                        label="Buys"
                        value={buyTrades}
                        colorScheme="success"
                        isActive={filter === 'BUY'}
                        onClick={() => setFilter('BUY')}
                    />
                    <StatPill
                        label="Sells"
                        value={sellTrades}
                        colorScheme="danger"
                        isActive={filter === 'SELL'}
                        onClick={() => setFilter('SELL')}
                    />
                    <StatPill
                        label="Rejected"
                        value={rejectionCount}
                        colorScheme="warning"
                        isActive={filter === 'REJECTED'}
                        onClick={() => setFilter('REJECTED')}
                    />
                    <StatPill
                        label="Executed"
                        value={totalTrades}
                        colorScheme="accent"
                        isActive={filter === 'EXECUTED'}
                        onClick={() => setFilter('EXECUTED')}
                    />
                </div>
            </div>

            {allActivity.length > 0 ? (
                <div className="space-y-4">
                    {allActivity.map((item, idx) => {
                        const isExpanded = expandedIdx === idx;
                        const agentInfo = getAgentInfo(item.model_name);
                        const rejectionReason =
                            item.type === 'REJECTION'
                                ? item.metadata?.reason || 'Reason not provided.'
                                : null;

                        return (
                            <div
                                key={idx}
                                onClick={() => setExpandedIdx(isExpanded ? null : idx)}
                                className={`group flex flex-col p-6 border rounded-none bg-white dark:bg-zinc-900 shadow-sm cursor-pointer transition-all duration-300 ${
                                    item.type === 'REJECTION'
                                        ? 'border-rose-200 dark:border-rose-900/50 hover:border-rose-500/50 hover:shadow-rose-500/10'
                                        : 'border-zinc-200 dark:border-zinc-800 hover:border-neon-green-500/50 hover:shadow-neon-green-500/10'
                                } ${
                                    isExpanded
                                        ? item.type === 'REJECTION'
                                            ? 'ring-2 ring-rose-500/20 shadow-lg'
                                            : 'ring-2 ring-neon-green-500/20 shadow-lg'
                                        : ''
                                }`}
                            >
                                {/* Main Row */}
                                <div className="flex items-center gap-4">
                                    {/* Signal Badge */}
                                    <div
                                        className={`w-12 h-12 rounded-none voxel-card flex items-center justify-center font-bold text-sm transition-all duration-300 ${
                                            item.type === 'TRADE'
                                                ? item.signal === 'BUY'
                                                    ? 'bg-success text-zinc-950'
                                                    : 'bg-danger text-white'
                                                : 'bg-warning text-zinc-950'
                                        }`}
                                    >
                                        {item.type === 'TRADE' ? item.signal : 'REJ'}
                                    </div>

                                    {/* Info */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex justify-between items-center mb-1">
                                            <div className="flex items-center gap-3 flex-wrap">
                                                <span className="font-bold text-boxel-ink text-lg uppercase tracking-tight text-display">
                                                    {item.ticker}
                                                </span>
                                                {item.type === 'TRADE' && (
                                                    <>
                                                        <div className="flex items-center gap-1.5 px-2 py-0.5 voxel-trough rounded-none">
                                                            <span className="text-sm">
                                                                {agentInfo.emoji}
                                                            </span>
                                                            <span className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                                                                {agentInfo.name}
                                                            </span>
                                                        </div>
                                                        {item.confidence && (
                                                            <Badge
                                                                size="xs"
                                                                variant="soft"
                                                                colorScheme={
                                                                    item.confidence > 0.7
                                                                        ? 'success'
                                                                        : item.confidence > 0.4
                                                                          ? 'warning'
                                                                          : 'accent'
                                                                }
                                                            >
                                                                {(item.confidence * 100).toFixed(0)}
                                                                % conf
                                                            </Badge>
                                                        )}
                                                    </>
                                                )}
                                                {item.type === 'REJECTION' && (
                                                    <>
                                                        <Badge
                                                            colorScheme="danger"
                                                            variant="soft"
                                                            size="xs"
                                                        >
                                                            Rejected
                                                        </Badge>
                                                        <div className="flex items-center gap-1.5 px-2 py-0.5 voxel-trough rounded-none">
                                                            <span className="text-sm">
                                                                {agentInfo.emoji}
                                                            </span>
                                                            <span className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                                                                {agentInfo.name}
                                                            </span>
                                                        </div>
                                                    </>
                                                )}
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <span className="text-xs font-normal text-boxel-muted font-mono uppercase tracking-wider tabular-nums">
                                                    {item.formattedTime
                                                        ? `${item.formattedTime} ET`
                                                        : 'Pending'}
                                                </span>
                                                <div
                                                    className={`transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}
                                                >
                                                    <svg
                                                        xmlns="http://www.w3.org/2000/svg"
                                                        width="20"
                                                        height="20"
                                                        viewBox="0 0 24 24"
                                                        fill="none"
                                                        stroke="currentColor"
                                                        strokeWidth="3"
                                                        strokeLinecap="round"
                                                        strokeLinejoin="round"
                                                        className="text-zinc-300 group-hover:text-zinc-400 transition-colors"
                                                    >
                                                        <title>SVG</title>
                                                        <path d="m6 9 6 6 6-6" />
                                                    </svg>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex flex-wrap items-center gap-4">
                                            <p
                                                className={`text-xs font-normal ${
                                                    item.type === 'REJECTION'
                                                        ? 'text-rose-600 dark:text-rose-400 font-bold'
                                                        : 'text-zinc-500 dark:text-zinc-400'
                                                }`}
                                            >
                                                {item.type === 'TRADE'
                                                    ? `${item.quantity?.toLocaleString('en-US') || 'N/A'} shares • $${Number(item.price).toFixed(2)}`
                                                    : (item.status || '').replace(/_/g, ' ')}
                                            </p>
                                            {item.type === 'TRADE' && item.portfolios?.owner_id && (
                                                <span className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                                                    {item.portfolios.owner_id.replace(/-/g, ' ')}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {/* Expanded Content */}
                                {isExpanded && (
                                    <div className="mt-4 pt-4 border-t border-boxel-bevel-hi animate-slide-up space-y-3">
                                        {item.type === 'REJECTION' && (
                                            <div className="space-y-1.5">
                                                <div className="flex items-center gap-1.5">
                                                    <div className="w-1.5 h-1.5 bg-danger rounded-none" />
                                                    <span className="text-xs font-normal text-danger uppercase tracking-wider">
                                                        Guardrail Rejection Detail
                                                    </span>
                                                </div>
                                                <div className="voxel-trough p-3 rounded-none border border-danger/30">
                                                    <p className="text-xs font-normal text-danger leading-relaxed">
                                                        {rejectionReason}
                                                    </p>
                                                </div>
                                            </div>
                                        )}

                                        {/* Thought Process */}
                                        <div className="space-y-1.5">
                                            <div className="flex items-center gap-1.5">
                                                <div className="w-1.5 h-1.5 bg-accent rounded-none" />
                                                <span className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                                                    Thought Process & Reasoning
                                                </span>
                                            </div>
                                            <div className="voxel-trough p-3 rounded-none">
                                                <p className="text-xs font-normal text-boxel-ink leading-relaxed whitespace-pre-wrap">
                                                    {item.reasoning}
                                                </p>
                                            </div>
                                        </div>

                                        {/* Execution Provenance Trace */}
                                        <ExecutionTraceView
                                            trace={item.metadata?.execution_trace}
                                        />

                                        {/* Trade Details for Executed Trades */}
                                        {item.type === 'TRADE' && (
                                            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,10rem),1fr))] gap-4 items-stretch">
                                                <MetricTile
                                                    label="Quantity"
                                                    value={
                                                        item.quantity?.toLocaleString('en-US') ||
                                                        'N/A'
                                                    }
                                                    icon="📊"
                                                />
                                                <MetricTile
                                                    label="Price"
                                                    value={`$${Number(item.price).toFixed(2)}`}
                                                    icon="💰"
                                                />
                                                <MetricTile
                                                    label="Total Value"
                                                    value={`$${((item.quantity || 0) * Number(item.price)).toLocaleString('en-US', { maximumFractionDigits: 0 })}`}
                                                    icon="💵"
                                                />
                                                {item.confidence && (
                                                    <MetricTile
                                                        label="Confidence"
                                                        value={`${(item.confidence * 100).toFixed(0)}%`}
                                                        icon="🎯"
                                                    />
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            ) : (
                <div className="text-center py-12 bg-zinc-50 dark:bg-zinc-900/50 rounded-none border border-dashed border-zinc-200 dark:border-zinc-800">
                    <p className="text-xs font-normal text-zinc-500 dark:text-zinc-300">
                        No {filter === 'ALL' ? 'activity' : filter.toLowerCase()} found
                    </p>
                </div>
            )}
        </section>
    );
}
