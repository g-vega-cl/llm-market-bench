import * as React from 'react'
import { useState } from 'react'

export type Position = {
    ticker: string
    quantity: number
    average_cost_basis: number
    current_price?: number
    unrealized_pnl_usd: number
    unrealized_pnl_pct: number
    reasoning: string
}

interface PositionsTableProps {
    positions: Position[]
}

export function PositionsTable({ positions }: PositionsTableProps) {
    const [expandedTicker, setExpandedTicker] = useState<string | null>(null)

    // Calculate total invested cash for the portfolio
    const totalInvestedCash = positions.reduce((sum, pos) => sum + pos.quantity * pos.average_cost_basis, 0)

    return (
        <div className="overflow-x-auto border border-zinc-200 rounded-xl bg-white shadow-sm">
            <table className="w-full text-left border-collapse">
                <thead>
                    <tr className="bg-zinc-50 border-bottom border-zinc-200">
                        <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500">Ticker</th>
                        <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right">Quantity</th>
                        <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right">Avg Cost</th>
                        <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right">Price</th>
                        <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right">Invested</th>
                        <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right">% of Portfolio</th>
                        <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right">P/L (USD)</th>
                        <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right">P/L (%)</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100">
                    {positions?.map((pos) => (
                        <React.Fragment key={pos.ticker}>
                            <tr
                                className="hover:bg-zinc-50/50 transition-colors cursor-pointer select-none group"
                                onClick={() => setExpandedTicker(expandedTicker === pos.ticker ? null : pos.ticker)}
                                data-testid={`position-row-${pos.ticker}`}
                            >
                                <td className="px-6 py-4 font-bold text-zinc-900 cursor-pointer">
                                    <div className="flex items-center gap-2">
                                        <span className={`transition-transform duration-200 ${expandedTicker === pos.ticker ? 'rotate-90' : ''}`}>
                                            <svg className="w-4 h-4 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                            </svg>
                                        </span>
                                        {pos.ticker}
                                    </div>
                                </td>
                                <td className="px-6 py-4 text-right text-zinc-700 cursor-pointer">{pos.quantity}</td>
                                <td className="px-6 py-4 text-right text-zinc-700 cursor-pointer">
                                    ${Number(pos.average_cost_basis).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </td>
                                <td className="px-6 py-4 text-right text-zinc-700 cursor-pointer">
                                    ${Number(pos.current_price || pos.average_cost_basis).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </td>
                                <td className="px-6 py-4 text-right text-zinc-700 cursor-pointer">
                                    ${(pos.quantity * pos.average_cost_basis).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </td>
                                <td className="px-6 py-4 text-right text-zinc-700 cursor-pointer">
                                    {totalInvestedCash ? ((pos.quantity * pos.average_cost_basis) / totalInvestedCash * 100).toFixed(2) + '%' : '0%'}
                                </td>
                                <td className={`px-6 py-4 text-right font-medium cursor-pointer ${Number(pos.unrealized_pnl_usd) >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}
                                >
                                    {Number(pos.unrealized_pnl_usd) >= 0 ? '+' : ''}
                                    ${Number(pos.unrealized_pnl_usd).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </td>
                                <td className={`px-6 py-4 text-right font-medium cursor-pointer ${Number(pos.unrealized_pnl_pct) >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}
                                >
                                    {Number(pos.unrealized_pnl_pct) >= 0 ? '+' : ''}
                                    {Number(pos.unrealized_pnl_pct).toFixed(2)}%
                                </td>
                            </tr>
                            {expandedTicker === pos.ticker && (
                                <tr className="bg-zinc-50/30" data-testid={`reasoning-row-${pos.ticker}`}>
                                    <td colSpan={8} className="px-12 py-6">
                                        <div className="flex flex-col gap-4 max-w-4xl">
                                            <h4 className="flex items-center gap-2 text-sm font-bold text-zinc-900 uppercase tracking-tight">
                                                <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                                                Thinking Process
                                            </h4>
                                            <div className="bg-white border border-zinc-200 rounded-xl p-6 shadow-sm">
                                                <p className="text-zinc-600 leading-relaxed whitespace-pre-wrap">
                                                    {pos.reasoning}
                                                </p>
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                            )}
                        </React.Fragment>
                    ))}
                    {(!positions || positions.length === 0) && (
                        <tr>
                            <td colSpan={8} className="px-6 py-12 text-center text-zinc-500">
                                No active positions in this portfolio.
                            </td>
                        </tr>
                    )}
                </tbody>
            </table>
        </div>
    )
}
