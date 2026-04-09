import * as React from 'react'
import { useState } from 'react'
import type { PositionWithReasoning } from '@llm-market-bench/database'

export type Position = PositionWithReasoning

interface PositionsTableProps {
    positions: Position[]
}

type SortKey = 'invested' | 'portfolio_pct' | 'pnl_usd' | 'pnl_pct'
type SortDirection = 'asc' | 'desc'

export function PositionsTable({ positions }: PositionsTableProps) {
    const [expandedTicker, setExpandedTicker] = useState<string | null>(null)
    const [sortKey, setSortKey] = useState<SortKey | null>(null)
    const [sortDirection, setSortDirection] = useState<SortDirection>('desc')

    // Calculate total invested cash for the portfolio
    const totalInvestedCash = positions.reduce((sum, pos) => sum + (pos.quantity ?? 0) * (pos.average_cost_basis ?? 0), 0)

    const handleSort = (key: SortKey) => {
        if (sortKey === key) {
            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
        } else {
            setSortKey(key)
            setSortDirection('desc')
        }
    }

    const getSortIcon = (key: SortKey) => {
        if (sortKey !== key) return '↕'
        return sortDirection === 'asc' ? '↑' : '↓'
    }

    const sortedPositions = React.useMemo(() => {
        if (!sortKey) return positions

        const sorted = [...positions].sort((a, b) => {
            let aVal: number
            let bVal: number

            switch (sortKey) {
                case 'invested':
                    aVal = (a.quantity ?? 0) * (a.average_cost_basis ?? 0)
                    bVal = (b.quantity ?? 0) * (b.average_cost_basis ?? 0)
                    break
                case 'portfolio_pct':
                    aVal = totalInvestedCash ? ((a.quantity ?? 0) * (a.average_cost_basis ?? 0)) / totalInvestedCash * 100 : 0
                    bVal = totalInvestedCash ? ((b.quantity ?? 0) * (b.average_cost_basis ?? 0)) / totalInvestedCash * 100 : 0
                    break
                case 'pnl_usd':
                    aVal = a.unrealized_pnl_usd ?? 0
                    bVal = b.unrealized_pnl_usd ?? 0
                    break
                case 'pnl_pct':
                    aVal = a.unrealized_pnl_pct ?? 0
                    bVal = b.unrealized_pnl_pct ?? 0
                    break
                default:
                    return 0
            }

            return sortDirection === 'asc' ? aVal - bVal : bVal - aVal
        })

        return sorted
    }, [positions, sortKey, sortDirection, totalInvestedCash])

    return (
        <div className="overflow-x-auto border border-zinc-200 rounded-xl bg-white shadow-sm">
            <table className="w-full text-left border-collapse">
                <thead>
                    <tr className="bg-zinc-50 border-bottom border-zinc-200">
                        <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500">Ticker</th>
                        <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right">Quantity</th>
                        <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right">Avg Cost</th>
                        <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right">Price</th>
                        <th 
                            className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right cursor-pointer hover:bg-zinc-100 transition-colors select-none"
                            onClick={() => handleSort('invested')}
                            title="Click to sort by invested amount"
                        >
                            Invested {getSortIcon('invested')}
                        </th>
                        <th 
                            className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right cursor-pointer hover:bg-zinc-100 transition-colors select-none"
                            onClick={() => handleSort('portfolio_pct')}
                            title="Click to sort by portfolio percentage"
                        >
                            % of Portfolio {getSortIcon('portfolio_pct')}
                        </th>
                        <th 
                            className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right cursor-pointer hover:bg-zinc-100 transition-colors select-none"
                            onClick={() => handleSort('pnl_usd')}
                            title="Click to sort by profit/loss in USD"
                        >
                            P/L (USD) {getSortIcon('pnl_usd')}
                        </th>
                        <th 
                            className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right cursor-pointer hover:bg-zinc-100 transition-colors select-none"
                            onClick={() => handleSort('pnl_pct')}
                            title="Click to sort by profit/loss percentage"
                        >
                            P/L (%) {getSortIcon('pnl_pct')}
                        </th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100">
                    {sortedPositions?.map((pos) => (
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
                                    ${((pos.quantity ?? 0) * (pos.average_cost_basis ?? 0)).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </td>
                                <td className="px-6 py-4 text-right text-zinc-700 cursor-pointer">
                                    {totalInvestedCash ? (((pos.quantity ?? 0) * (pos.average_cost_basis ?? 0)) / totalInvestedCash * 100).toFixed(2) + '%' : '0%'}
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
                                        <div className="flex flex-col gap-4">
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
