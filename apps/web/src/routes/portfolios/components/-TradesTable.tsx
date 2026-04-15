import * as React from 'react'
import { useState } from 'react'
import type { TradeWithReasoning } from '@llm-market-bench/database'

export type Trade = TradeWithReasoning

interface TradesTableProps {
    trades: Trade[]
}

export function TradesTable({ trades }: TradesTableProps) {
    const [expandedId, setExpandedId] = useState<string | null>(null)

    return (
        <div className="overflow-x-auto border border-zinc-200 rounded-xl bg-white shadow-sm">
            <table className="w-full text-left border-collapse min-w-[700px]">
                <thead>
                    <tr className="bg-zinc-50 border-bottom border-zinc-200">
                        <th className="px-3 sm:px-6 py-3 sm:py-4 text-xs font-bold uppercase tracking-wider text-zinc-500">Date</th>
                        <th className="px-3 sm:px-6 py-3 sm:py-4 text-xs font-bold uppercase tracking-wider text-zinc-500">Ticker</th>
                        <th className="px-3 sm:px-6 py-3 sm:py-4 text-xs font-bold uppercase tracking-wider text-zinc-500">Signal</th>
                        <th className="px-3 sm:px-6 py-3 sm:py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right">Qty</th>
                        <th className="px-3 sm:px-6 py-3 sm:py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right">Price</th>
                        <th className="px-3 sm:px-6 py-3 sm:py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right">Total</th>
                        <th className="px-3 sm:px-6 py-3 sm:py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right">PnL</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100">
                    {trades?.map((trade) => (
                        <React.Fragment key={trade.id}>
                            <tr
                                className="hover:bg-zinc-50/50 transition-colors cursor-pointer select-none group"
                                onClick={() => setExpandedId(expandedId === trade.id ? null : trade.id)}
                            >
                                <td className="px-3 sm:px-6 py-3 sm:py-4 text-zinc-500 cursor-pointer text-sm">
                                    {trade.executed_at ? new Date(trade.executed_at).toLocaleDateString() : '-'}
                                </td>
                                <td className="px-3 sm:px-6 py-3 sm:py-4 font-bold text-zinc-900 cursor-pointer">
                                    <div className="flex items-center gap-2">
                                        <span className={`transition-transform duration-200 ${expandedId === trade.id ? 'rotate-90' : ''}`}>
                                            <svg className="w-4 h-4 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                            </svg>
                                        </span>
                                        {trade.ticker}
                                    </div>
                                </td>
                                <td className="px-3 sm:px-6 py-3 sm:py-4 cursor-pointer">
                                    <span className={`px-2 py-1 rounded-md text-xs font-bold uppercase tracking-tight ${trade.signal.toUpperCase() === 'BUY'
                                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-100'
                                            : 'bg-rose-50 text-rose-700 border border-rose-100'
                                        }`}>
                                        {trade.signal}
                                    </span>
                                </td>
                                <td className="px-3 sm:px-6 py-3 sm:py-4 text-right text-zinc-700 cursor-pointer">{trade.quantity}</td>
                                <td className="px-3 sm:px-6 py-3 sm:py-4 text-right text-zinc-700 cursor-pointer">
                                    ${Number(trade.price).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </td>
                                <td className="px-3 sm:px-6 py-3 sm:py-4 text-right text-zinc-900 font-medium cursor-pointer">
                                    ${Number(trade.total_cost).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </td>
                                <td className="px-3 sm:px-6 py-3 sm:py-4 text-right cursor-pointer">
                                    {trade.realized_pnl !== null && trade.realized_pnl !== undefined ? (
                                        <div className="flex flex-col items-end">
                                            <span className={`font-bold ${trade.realized_pnl >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                                                {trade.realized_pnl >= 0 ? '+' : ''}
                                                ${Math.abs(trade.realized_pnl).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                            </span>
                                            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${trade.realized_pnl >= 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>
                                                {trade.realized_pnl >= 0 ? '+' : ''}
                                                {trade.realized_pnl_pct?.toFixed(2)}%
                                            </span>
                                        </div>
                                    ) : (
                                        <span className="text-zinc-300">—</span>
                                    )}
                                </td>
                            </tr>
                            {expandedId === trade.id && (
                                <tr className="bg-zinc-50/30">
                                    <td colSpan={7} className="px-4 sm:px-12 py-4 sm:py-6">
                                        <div className="flex flex-col gap-4">
                                            <h4 className="flex items-center gap-2 text-sm font-bold text-zinc-900 uppercase tracking-tight">
                                                <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                                                Thinking Process
                                            </h4>
                                            <div className="bg-white border border-zinc-200 rounded-xl p-4 sm:p-6 shadow-sm">
                                                <p className="text-zinc-600 leading-relaxed whitespace-pre-wrap text-sm sm:text-base">
                                                    {trade.reasoning}
                                                </p>
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                            )}
                        </React.Fragment>
                    ))}
                    {(!trades || trades.length === 0) && (
                        <tr>
                            <td colSpan={7} className="px-6 py-12 text-center text-zinc-500">
                                No recent trades found for this agent.
                            </td>
                        </tr>
                    )}
                </tbody>
            </table>
        </div>
    )
}
