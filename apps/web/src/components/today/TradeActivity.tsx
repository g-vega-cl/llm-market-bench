import * as React from 'react'

interface TradeActivityProps {
    trades: any[]
    decisions: any[]
}

const agentConfig: Record<string, { name: string; color: string; bgColor: string; emoji: string }> = {
    'gpt-5.4-nano': { name: 'OpenAI', color: 'text-emerald-500', bgColor: 'bg-emerald-500', emoji: '🟢' },
    'claude-haiku-4-5': { name: 'Claude', color: 'text-amber-600', bgColor: 'bg-amber-600', emoji: '🟠' },
    'gemini-3.1-flash-lite-preview': { name: 'Gemini', color: 'text-blue-500', bgColor: 'bg-blue-500', emoji: '🔵' },
    'deepseek-reasoner': { name: 'DeepSeek', color: 'text-purple-500', bgColor: 'bg-purple-500', emoji: '🟣' },
    'contrarian_agent': { name: 'Contrarian', color: 'text-rose-500', bgColor: 'bg-rose-500', emoji: '🔴' },
}

function getAgentInfo(ownerId: string) {
    if (!ownerId) return { name: 'Unknown', color: 'text-zinc-500', bgColor: 'bg-zinc-500', emoji: '⚪' }
    const normalized = ownerId.toLowerCase().replace(/_/g, '-').replace(/-/g, '-')
    for (const [key, config] of Object.entries(agentConfig)) {
        if (normalized.includes(key.replace(/-/g, '')) || key.includes(normalized.replace(/-/g, ''))) {
            return config
        }
    }
    return { name: ownerId, color: 'text-zinc-500', bgColor: 'bg-zinc-500', emoji: '⚪' }
}

type FilterType = 'ALL' | 'BUY' | 'SELL' | 'REJECTED'

export function TradeActivity({ trades, decisions }: TradeActivityProps) {
    const [expandedIdx, setExpandedIdx] = React.useState<number | null>(null)
    const [filter, setFilter] = React.useState<FilterType>('ALL')

    // Include rejections from decisions
    const rejections = decisions.filter(d => d.status && d.status.startsWith('REJECTED'))

    // Normalize and sort all activity
    const allActivity = React.useMemo(() => {
        const activity = [
            ...trades.map(t => {
                const decision = decisions.find(d => d.id === t.decision_id || d.trade_id === t.id)
                return {
                    ...t,
                    type: 'TRADE',
                    timestamp: t.executed_at,
                    reasoning: decision?.reasoning || 'No reasoning found for this execution.',
                    model_name: decision?.model_name || t.portfolios?.owner_id,
                    confidence: decision?.confidence_score,
                }
            }),
            ...rejections.map(r => ({
                ...r,
                type: 'REJECTION',
                timestamp: r.created_at,
            }))
        ].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

        // Apply filter
        if (filter === 'ALL') return activity
        if (filter === 'BUY') return activity.filter(item => item.type === 'TRADE' && item.signal === 'BUY')
        if (filter === 'SELL') return activity.filter(item => item.type === 'TRADE' && item.signal === 'SELL')
        if (filter === 'REJECTED') return activity.filter(item => item.type === 'REJECTION')
        
        return activity
    }, [trades, decisions, rejections, filter])

    // Calculate stats
    const totalTrades = trades.length
    const buyTrades = trades.filter(t => t.signal === 'BUY').length
    const sellTrades = trades.filter(t => t.signal === 'SELL').length
    const rejectionCount = rejections.length

    return (
        <section className="space-y-8 animate-slide-up">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <h2 className="text-3xl font-black text-zinc-900 dark:text-white flex items-center gap-4 text-display">
                    <span className="w-3 h-10 bg-gradient-to-b from-neon-green-500 to-emerald-600 rounded-full shadow-lg" />
                    <span className="text-gradient text-gradient-success">Market Execution & Guardrails</span>
                </h2>

                {/* Activity Stats */}
                <div className="flex flex-wrap items-center gap-3">
                    <StatPill 
                        label="Total" 
                        value={totalTrades} 
                        color="bg-zinc-500" 
                        isActive={filter === 'ALL'}
                        onClick={() => setFilter('ALL')}
                    />
                    <StatPill 
                        label="Buys" 
                        value={buyTrades} 
                        color="bg-neon-green-500" 
                        isActive={filter === 'BUY'}
                        onClick={() => setFilter('BUY')}
                    />
                    <StatPill 
                        label="Sells" 
                        value={sellTrades} 
                        color="bg-alert-red-500" 
                        isActive={filter === 'SELL'}
                        onClick={() => setFilter('SELL')}
                    />
                    <StatPill 
                        label="Rejected" 
                        value={rejectionCount} 
                        color="bg-amber-500" 
                        isActive={filter === 'REJECTED'}
                        onClick={() => setFilter('REJECTED')}
                    />
                </div>
            </div>

            {allActivity.length > 0 ? (
                <div className="space-y-4">
                    {allActivity.map((item, idx) => {
                    const isTrade = item.type === 'TRADE'
                    const isRejection = item.type === 'REJECTION'
                    const isExpanded = expandedIdx === idx
                    const agentInfo = getAgentInfo(item.model_name)
                    const rejectionReason = isRejection ? item.metadata?.reason || 'Reason not provided.' : null

                    return (
                        <div
                            key={idx}
                            onClick={() => setExpandedIdx(isExpanded ? null : idx)}
                            className={`group flex flex-col p-6 border rounded-3xl bg-white dark:bg-zinc-900 shadow-sm cursor-pointer transition-all duration-300 card-lift ${
                                isRejection
                                    ? 'border-rose-200 dark:border-rose-900/50 hover:border-rose-500/50 hover:shadow-rose-500/10'
                                    : 'border-zinc-200 dark:border-zinc-800 hover:border-neon-green-500/50 hover:shadow-neon-green-500/10'
                            } ${isExpanded ? (isRejection ? 'ring-2 ring-rose-500/20 shadow-lg' : 'ring-2 ring-neon-green-500/20 shadow-lg') : ''
                            }`}
                        >
                            {/* Main Row */}
                            <div className="flex items-center gap-4">
                                {/* Signal Badge */}
                                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center font-black text-sm transition-all duration-300 group-hover:scale-110 shadow-lg ${
                                    isTrade
                                        ? item.signal === 'BUY'
                                            ? 'bg-gradient-to-br from-neon-green-400 to-emerald-500 text-white glow-success'
                                            : 'bg-gradient-to-br from-alert-red-400 to-rose-500 text-white glow-alert'
                                        : 'bg-gradient-to-br from-amber-400 to-orange-500 text-white'
                                }`}>
                                    {isTrade ? item.signal : 'REJ'}
                                </div>

                                {/* Info */}
                                <div className="flex-1 min-w-0">
                                    <div className="flex justify-between items-center mb-1">
                                        <div className="flex items-center gap-3 flex-wrap">
                                            <span className="font-black text-zinc-900 dark:text-white text-2xl uppercase tracking-tight text-display">
                                                {item.ticker}
                                            </span>
                                            {isTrade && (
                                                <>
                                                    <div className="flex items-center gap-1.5 px-2.5 py-1 bg-zinc-100 dark:bg-zinc-800 rounded-lg border border-zinc-200 dark:border-zinc-700">
                                                        <span className="text-lg">{agentInfo.emoji}</span>
                                                        <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">
                                                            {agentInfo.name}
                                                        </span>
                                                    </div>
                                                    {item.confidence && (
                                                        <span className={`px-2.5 py-1 rounded-lg text-[9px] font-black uppercase tracking-wider border ${
                                                            item.confidence > 0.7
                                                                ? 'bg-neon-green-100 dark:bg-neon-green-900/30 text-neon-green-600 dark:text-neon-green-400 border-neon-green-200 dark:border-neon-green-800'
                                                                : item.confidence > 0.4
                                                                ? 'bg-cyber-yellow-100 dark:bg-cyber-yellow-900/30 text-cyber-yellow-600 dark:text-cyber-yellow-400 border-cyber-yellow-200 dark:border-cyber-yellow-800'
                                                                : 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-800'
                                                        }`}>
                                                            {(item.confidence * 100).toFixed(0)}% conf
                                                        </span>
                                                    )}
                                                </>
                                            )}
                                            {isRejection && (
                                                <>
                                                    <span className="px-2.5 py-1 bg-rose-50 dark:bg-rose-950/30 text-rose-500 text-[9px] font-bold rounded-lg uppercase tracking-wider border border-rose-200 dark:border-rose-900/50">
                                                        Rejected
                                                    </span>
                                                    <div className="flex items-center gap-1.5 px-2.5 py-1 bg-zinc-100 dark:bg-zinc-800 rounded-lg border border-zinc-200 dark:border-zinc-700">
                                                        <span className="text-lg">{agentInfo.emoji}</span>
                                                        <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">
                                                            {agentInfo.name}
                                                        </span>
                                                    </div>
                                                </>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <span className="text-[9px] text-zinc-400 font-mono uppercase tracking-widest tabular-nums">
                                                {new Date(item.timestamp).toLocaleTimeString([], {
                                                    hour: '2-digit',
                                                    minute: '2-digit'
                                                })}
                                            </span>
                                            <div className={`transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}>
                                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="text-zinc-300 group-hover:text-zinc-400 transition-colors">
                                                    <path d="m6 9 6 6 6-6" />
                                                </svg>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex flex-wrap items-center gap-4">
                                        <p className={`text-sm font-medium ${
                                            isRejection ? 'text-rose-600/80 dark:text-rose-400/80' : 'text-zinc-500 dark:text-zinc-400'
                                        }`}>
                                            {isTrade
                                                ? `${item.quantity?.toLocaleString() || 'N/A'} shares • $${Number(item.price).toFixed(2)}`
                                                : item.status.replace(/_/g, ' ')
                                            }
                                        </p>
                                        {isTrade && item.portfolios?.owner_id && (
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
                                    {isRejection && (
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
                                    {isTrade && (
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                            <DetailCard
                                                label="Quantity"
                                                value={item.quantity?.toLocaleString() || 'N/A'}
                                                icon="📊"
                                            />
                                            <DetailCard
                                                label="Price"
                                                value={`$${Number(item.price).toFixed(2)}`}
                                                icon="💰"
                                            />
                                            <DetailCard
                                                label="Total Value"
                                                value={`$${((item.quantity || 0) * Number(item.price)).toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
                                                icon="💵"
                                            />
                                            {item.confidence && (
                                                <DetailCard
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
                    )
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
    )
}

function StatPill({ 
    label, 
    value, 
    color,
    isActive,
    onClick 
}: { 
    label: string
    value: number
    color: string
    isActive?: boolean
    onClick?: () => void
}) {
    return (
        <button
            onClick={onClick}
            className={`flex items-center gap-2 px-3 py-1.5 bg-white dark:bg-zinc-900 border rounded-full shadow-sm transition-all duration-300 ${
                isActive
                    ? 'border-zinc-900 dark:border-white shadow-md scale-105'
                    : 'border-zinc-200 dark:border-zinc-800 hover:shadow-md hover:scale-105'
            } cursor-pointer`}
        >
            <div className={`w-2 h-2 rounded-full ${color} shadow-lg`} />
            <span className={`text-[10px] font-black uppercase tracking-wider ${
                isActive ? 'text-zinc-900 dark:text-white' : 'text-zinc-400'
            }`}>
                {label}
            </span>
            <span className={`text-sm font-black tabular-nums ${
                isActive ? 'text-zinc-900 dark:text-white' : 'text-zinc-500 dark:text-zinc-400'
            }`}>
                {value}
            </span>
        </button>
    )
}

function DetailCard({ label, value, icon }: { label: string; value: string; icon: string }) {
    return (
        <div className="p-3 bg-zinc-50 dark:bg-zinc-950/50 rounded-xl border border-zinc-100 dark:border-zinc-900 hover:border-electric-blue-300 dark:hover:border-electric-blue-700 transition-colors duration-300">
            <div className="flex items-center gap-1.5 mb-1">
                <span className="text-lg">{icon}</span>
                <span className="text-[9px] font-black text-zinc-400 uppercase tracking-wider">{label}</span>
            </div>
            <div className="text-lg font-black text-zinc-900 dark:text-white text-display tabular-nums">{value}</div>
        </div>
    )
}
