import * as React from 'react'

export function TradeActivity({ trades, decisions }: { trades: any[], decisions: any[] }) {
    const [expandedIdx, setExpandedIdx] = React.useState<number | null>(null);

    // Also include rejections from decisions
    const rejections = decisions.filter(d => d.status && d.status.startsWith('REJECTED'));

    // Normalize and sort all activity
    const allActivity = [
        ...trades.map(t => {
            // Find the decision that triggered this trade
            const decision = decisions.find(d => d.id === t.decision_id || d.trade_id === t.id);
            return {
                ...t,
                type: 'TRADE',
                timestamp: t.executed_at,
                reasoning: decision?.reasoning || 'No reasoning found for this execution.'
            };
        }),
        ...rejections.map(r => ({
            ...r,
            type: 'REJECTION',
            timestamp: r.created_at
        }))
    ].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

    if (!allActivity.length) return null;

    return (
        <section className="space-y-6">
            <h2 className="text-2xl font-black text-zinc-900 dark:text-white flex items-center gap-3">
                <span className="w-2 h-8 bg-emerald-500 rounded-full" />
                Market Execution & Guardrails
            </h2>
            <div className="space-y-4">
                {allActivity.map((item, idx) => {
                    const isTrade = item.type === 'TRADE';
                    const isExpanded = expandedIdx === idx;

                    return (
                        <div
                            key={idx}
                            onClick={() => setExpandedIdx(isExpanded ? null : idx)}
                            className={`flex flex-col p-6 border border-zinc-200 dark:border-zinc-800 rounded-3xl bg-white dark:bg-zinc-900 shadow-sm cursor-pointer transition-all duration-300 hover:border-emerald-500/50 ${isExpanded ? 'ring-2 ring-emerald-500/20 shadow-lg' : ''
                                }`}
                        >
                            <div className="flex items-center gap-4">
                                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center font-black text-xs ${isTrade
                                        ? item.signal === 'BUY' ? 'bg-emerald-100 text-emerald-600' : 'bg-rose-100 text-rose-600'
                                        : 'bg-zinc-100 text-zinc-400'
                                    }`}>
                                    {isTrade ? item.signal : 'REJ'}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex justify-between items-center mb-1">
                                        <div className="flex items-center gap-3">
                                            <span className="font-black text-zinc-900 dark:text-white text-xl uppercase tracking-tight">{item.ticker}</span>
                                            {isTrade && (
                                                <span className="px-2 py-0.5 bg-zinc-100 dark:bg-zinc-800 text-zinc-500 text-[10px] font-bold rounded-lg uppercase">
                                                    {item.portfolios?.owner_id?.replace(/-/g, ' ') || 'Primary'}
                                                </span>
                                            )}
                                        </div>
                                        <span className="text-[10px] text-zinc-400 font-bold uppercase tracking-widest">
                                            {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </span>
                                    </div>
                                    <p className="text-sm text-zinc-500 dark:text-zinc-400 font-medium">
                                        {isTrade
                                            ? `${item.quantity} shares • $${Number(item.price).toFixed(2)}`
                                            : item.status.replace(/_/g, ' ')
                                        }
                                    </p>
                                </div>
                                <div className={`transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}>
                                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="text-zinc-300">
                                        <path d="m6 9 6 6 6-6" />
                                    </svg>
                                </div>
                            </div>

                            {isExpanded && (
                                <div className="mt-6 pt-6 border-t border-zinc-100 dark:border-zinc-800 animate-in fade-in slide-in-from-top-2 duration-300">
                                    <div className="flex items-center gap-2 mb-3">
                                        <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
                                        <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">Thought Process & Reasoning</span>
                                    </div>
                                    <div className="bg-zinc-50 dark:bg-zinc-950/50 p-6 rounded-2xl border border-zinc-100 dark:border-zinc-900">
                                        <p className="text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed font-medium">
                                            {item.reasoning}
                                        </p>
                                    </div>
                                </div>
                            )}
                        </div>
                    )
                })}
            </div>
        </section>
    )
}
