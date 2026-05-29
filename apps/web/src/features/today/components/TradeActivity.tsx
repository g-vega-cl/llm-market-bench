import { Badge, MetricTile, SectionHeading, StatPill } from '@llm-market-bench/ui-design-system';
import * as React from 'react';
import { getAgentInfo } from '../lib/agent-info';

interface TradeItem {
    id: string;
    decision_id?: string | null;
    executed_at: string | null;
    signal: string;
    ticker: string;
    quantity?: number;
    price: number | string;
    portfolios?: { owner_id?: string };
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
      })
    | (DecisionItem & {
          type: 'REJECTION';
          timestamp: string | null;
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
                const decision = decisions.find(
                    (d) => d.id === t.decision_id || (d.trade_id && d.trade_id === t.id),
                );
                return {
                    ...t,
                    type: 'TRADE' as const,
                    timestamp: t.executed_at,
                    reasoning: decision?.reasoning || 'No reasoning found for this execution.',
                    model_name: decision?.model_name || t.portfolios?.owner_id,
                    confidence: decision?.confidence_score,
                };
            }),
            ...rejections.map((r) => ({
                ...r,
                type: 'REJECTION' as const,
                timestamp: r.created_at,
            })),
        ].sort(
            (a, b) => new Date(b.timestamp || 0).getTime() - new Date(a.timestamp || 0).getTime(),
        );

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
    const totalTrades = trades.length;
    const buyTrades = trades.filter((t) => t.signal === 'BUY').length;
    const sellTrades = trades.filter((t) => t.signal === 'SELL').length;
    const rejectionCount = rejections.length;

    return (
        <section className="space-y-8 animate-slide-up">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <SectionHeading gradient="success">Market Execution & Guardrails</SectionHeading>

                {/* Activity Stats */}
                <div className="flex flex-wrap items-center gap-3">
                    <StatPill
                        label="Total"
                        value={totalTrades}
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
                                className={`group flex flex-col p-6 border rounded-3xl bg-white dark:bg-zinc-900 shadow-sm cursor-pointer transition-all duration-300 card-lift ${
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
                                        className={`w-14 h-14 rounded-2xl flex items-center justify-center font-black text-sm transition-all duration-300 group-hover:scale-110 shadow-lg ${
                                            item.type === 'TRADE'
                                                ? item.signal === 'BUY'
                                                    ? 'bg-gradient-to-br from-neon-green-400 to-emerald-500 text-white glow-success'
                                                    : 'bg-gradient-to-br from-alert-red-400 to-rose-500 text-white glow-alert'
                                                : 'bg-gradient-to-br from-amber-400 to-orange-500 text-white'
                                        }`}
                                    >
                                        {item.type === 'TRADE' ? item.signal : 'REJ'}
                                    </div>

                                    {/* Info */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex justify-between items-center mb-1">
                                            <div className="flex items-center gap-3 flex-wrap">
                                                <span className="font-black text-zinc-900 dark:text-white text-2xl uppercase tracking-tight text-display">
                                                    {item.ticker}
                                                </span>
                                                {item.type === 'TRADE' && (
                                                    <>
                                                        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-zinc-100 dark:bg-zinc-800 rounded-lg border border-zinc-200 dark:border-zinc-700">
                                                            <span className="text-lg">
                                                                {agentInfo.emoji}
                                                            </span>
                                                            <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">
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
                                                                radius="lg"
                                                            >
                                                                {(item.confidence * 100).toFixed(0)}
                                                                % conf
                                                            </Badge>
                                                        )}
                                                    </>
                                                )}
                                                {item.type === 'REJECTION' && (
                                                    <>
                                                        <span className="px-2.5 py-1 bg-rose-50 dark:bg-rose-950/30 text-rose-500 text-[9px] font-bold rounded-lg uppercase tracking-wider border border-rose-200 dark:border-rose-900/50">
                                                            Rejected
                                                        </span>
                                                        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-zinc-100 dark:bg-zinc-800 rounded-lg border border-zinc-200 dark:border-zinc-700">
                                                            <span className="text-lg">
                                                                {agentInfo.emoji}
                                                            </span>
                                                            <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">
                                                                {agentInfo.name}
                                                            </span>
                                                        </div>
                                                    </>
                                                )}
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <span className="text-[9px] text-zinc-400 font-mono uppercase tracking-widest tabular-nums">
                                                    {item.timestamp
                                                        ? `${new Date(
                                                              item.timestamp,
                                                          ).toLocaleTimeString('en-US', {
                                                              timeZone: 'America/New_York',
                                                              hour: '2-digit',
                                                              minute: '2-digit',
                                                          })} ET`
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
                                                className={`text-sm font-medium ${
                                                    item.type === 'REJECTION'
                                                        ? 'text-rose-600/80 dark:text-rose-400/80'
                                                        : 'text-zinc-500 dark:text-zinc-400'
                                                }`}
                                            >
                                                {item.type === 'TRADE'
                                                    ? `${item.quantity?.toLocaleString('en-US') || 'N/A'} shares • $${Number(item.price).toFixed(2)}`
                                                    : (item.status || '').replace(/_/g, ' ')}
                                            </p>
                                            {item.type === 'TRADE' && item.portfolios?.owner_id && (
                                                <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
                                                    {item.portfolios.owner_id.replace(/-/g, ' ')}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {/* Expanded Content */}
                                {isExpanded && (
                                    <div className="mt-6 pt-6 border-t border-zinc-100 dark:border-zinc-800 animate-slide-up space-y-4">
                                        {item.type === 'REJECTION' && (
                                            <div className="space-y-2">
                                                <div className="flex items-center gap-2">
                                                    <div className="w-1.5 h-1.5 bg-rose-500 rounded-full shadow-lg" />
                                                    <span className="text-[10px] font-black text-rose-500 uppercase tracking-widest">
                                                        Guardrail Rejection Detail
                                                    </span>
                                                </div>
                                                <div className="bg-rose-50/50 dark:bg-rose-950/10 p-4 rounded-2xl border border-rose-100/50 dark:border-rose-900/30">
                                                    <p className="text-sm text-rose-700 dark:text-rose-300 leading-relaxed font-bold">
                                                        {rejectionReason}
                                                    </p>
                                                </div>
                                            </div>
                                        )}

                                        {/* Thought Process */}
                                        <div className="space-y-2">
                                            <div className="flex items-center gap-2">
                                                <div className="w-1.5 h-1.5 bg-electric-blue-500 rounded-full shadow-lg" />
                                                <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">
                                                    Thought Process & Reasoning
                                                </span>
                                            </div>
                                            <div className="bg-zinc-50 dark:bg-zinc-950/50 p-6 rounded-2xl border border-zinc-100 dark:border-zinc-900">
                                                <p className="text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed font-medium whitespace-pre-wrap">
                                                    {item.reasoning}
                                                </p>
                                            </div>
                                        </div>

                                        {/* Trade Details for Executed Trades */}
                                        {item.type === 'TRADE' && (
                                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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
                <div className="text-center py-12 bg-zinc-50 dark:bg-zinc-900/50 rounded-3xl border border-dashed border-zinc-200 dark:border-zinc-800">
                    <p className="text-zinc-400 dark:text-zinc-500 font-medium">
                        No {filter === 'ALL' ? 'activity' : filter.toLowerCase()} found
                    </p>
                </div>
            )}
        </section>
    );
}
