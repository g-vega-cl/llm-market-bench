import * as React from 'react'

export function TradeActivity({ trades, decisions }: { trades: any[], decisions: any[] }) {
    // Also include rejections from decisions
    const rejections = decisions.filter(d => d.status && d.status.startsWith('REJECTED'));

    // Normalize and sort all activity
    const allActivity = [
        ...trades.map(t => ({
            ...t,
            type: 'TRADE',
            timestamp: t.executed_at
        })),
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
            <div className="space-y-3">
                {allActivity.map((item, idx) => {
                    const isTrade = item.type === 'TRADE';
                    return (
                        <div key={idx} className="flex items-center gap-4 p-4 border border-zinc-200 dark:border-zinc-800 rounded-2xl bg-white dark:bg-zinc-900 shadow-sm">
                            <div className={`w-12 h-12 rounded-xl flex items-center justify-center font-black text-sm ${
                                isTrade
                                    ? item.signal === 'BUY' ? 'bg-emerald-100 text-emerald-600' : 'bg-rose-100 text-rose-600'
                                    : 'bg-zinc-100 text-zinc-400'
                            }`}>
                                {isTrade ? item.signal : 'REJ'}
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="flex justify-between items-center mb-1">
                                    <span className="font-black text-zinc-900 dark:text-white text-lg">{item.ticker}</span>
                                    <span className="text-[10px] text-zinc-400 font-mono">
                                        {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </span>
                                </div>
                                <p className="text-xs text-zinc-500 dark:text-zinc-400 font-medium truncate">
                                    {isTrade
                                        ? `${item.quantity} shares @ $${Number(item.price).toFixed(2)} • Portfolio: ${item.portfolios?.owner_id?.replace(/-/g, ' ') || 'Unknown'}`
                                        : `${item.status.replace(/_/g, ' ')}: ${item.reasoning?.substring(0, 100)}...`
                                    }
                                </p>
                            </div>
                        </div>
                    )
                })}
            </div>
        </section>
    )
}
