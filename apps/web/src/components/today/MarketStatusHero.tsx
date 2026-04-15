import * as React from 'react'
import type { MarketFeeling } from '@llm-market-bench/database'

interface MarketStatusHeroProps {
    data: {
        trades?: any[]
        decisions?: any[]
        memories?: any[]
        priceUpdates?: any[]
        futureEvents?: any[]
        newsletters?: any[]
        marketFeeling?: MarketFeeling | null
    }
}

function formatTimeAgo(dateStr: string | null | undefined): string {
    if (!dateStr) return 'Unknown'
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: 'numeric' })
}

function getDirectionColor(direction: string | null | undefined): string {
    switch (direction?.toUpperCase()) {
        case 'BULLISH': return 'text-neon-green-400'
        case 'BEARISH': return 'text-alert-red-400'
        default: return 'text-steel-400'
    }
}

function getConfidenceColor(score: number | null | undefined): string {
    if (!score) return 'bg-steel-500'
    if (score >= 70) return 'bg-neon-green-500'
    if (score >= 40) return 'bg-amber-500'
    return 'bg-alert-red-500'
}

export function MarketStatusHero({ data }: MarketStatusHeroProps) {
    const now = new Date()
    const currentHour = now.getUTCHours()
    const currentMinutes = now.getUTCMinutes()
    const dayOfWeek = now.getUTCDay()

    const isMarketOpen = dayOfWeek >= 1 && dayOfWeek <= 5 &&
        ((currentHour > 13 || (currentHour === 13 && currentMinutes >= 30)) && currentHour < 20)

    const totalTrades = data.trades?.length || 0
    const activeMemories = data.memories?.filter(m => m.status === 'ACTIVE').length || 0

    const marketFeeling = data.marketFeeling

    const buyCount = data.trades?.filter(t => t.signal === 'BUY').length || 0
    const sellCount = data.trades?.filter(t => t.signal === 'SELL').length || 0

    const isStale = marketFeeling ? (() => {
        if (!marketFeeling.created_at) return true
        const created = new Date(marketFeeling.created_at)
        const ageHours = (now.getTime() - created.getTime()) / 3600000
        return ageHours > 4
    })() : true

    const fallbackSentiment = {
        label: marketFeeling?.sentiment_label || 'Analyzing...',
        emoji: marketFeeling?.sentiment_emoji || '🤔',
        direction: marketFeeling?.market_direction || null,
        confidence: marketFeeling?.confidence_score || null,
        why: marketFeeling?.why_explanation || null,
        primaryConcern: marketFeeling?.primary_concern || null,
    }

    return (
        <div className="relative overflow-hidden gradient-electric">
            <div className="absolute inset-0 opacity-10">
                <div className="absolute inset-0" style={{
                    backgroundImage: `radial-gradient(circle at 2px 2px, white 1px, transparent 0)`,
                    backgroundSize: '40px 40px'
                }} />
            </div>

            <div className="absolute inset-0 bg-gradient-to-br from-electric-blue-600/90 via-deep-purple-600/80 to-electric-blue-800/90" />

            <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-electric-blue-400/20 rounded-full blur-3xl animate-pulse" />
            <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-deep-purple-400/20 rounded-full blur-3xl animate-pulse animate-stagger-2" />

            <div className="relative max-w-7xl mx-auto px-6 md:px-12 py-16 md:py-24">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-center">
                    <div className="lg:col-span-2 space-y-6 animate-slide-up">
                        <div className="flex flex-col sm:flex-row sm:items-center gap-4 flex-wrap">
                            <h1 className="text-6xl sm:text-7xl md:text-8xl font-black text-white tracking-tighter text-display drop-shadow-lg">
                                TODAY
                            </h1>
                            <div className="px-4 py-2 bg-white/20 backdrop-blur-sm text-white text-sm font-bold rounded-full border border-white/30 shadow-lg">
                                {now.toLocaleDateString('en-US', {
                                    weekday: 'long',
                                    month: 'long',
                                    day: 'numeric',
                                    year: 'numeric'
                                })}
                            </div>
                        </div>

                        <p className="text-lg sm:text-xl text-electric-blue-100 font-light leading-relaxed max-w-2xl drop-shadow">
                            Six AI agents. One virtual market. Real-time benchmark of machine cognition vs. the S&P 500.
                        </p>

                        <div className="flex flex-wrap gap-4 sm:gap-6 pt-4">
                            <StatBadge
                                icon="📰"
                                label="Newsletters"
                                value={data.newsletters?.length || 0}
                            />
                            <StatBadge
                                icon="💼"
                                label="Trades"
                                value={totalTrades}
                            />
                            <StatBadge
                                icon="🧠"
                                label="Active Memories"
                                value={activeMemories}
                            />
                        </div>
                    </div>

                    <div className="lg:col-span-1 space-y-6 animate-slide-up animate-stagger-2">
                        <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-3xl p-6 glow-electric shadow-2xl hover:shadow-3xl transition-shadow duration-300">
                            <div className="flex items-center justify-between mb-4">
                                <span className="text-xs font-black text-electric-blue-200 uppercase tracking-widest">
                                    Market Status
                                </span>
                                <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold transition-all duration-300 ${
                                    isMarketOpen
                                        ? 'bg-neon-green-500/20 text-neon-green-300 border border-neon-green-500/30 shadow-lg shadow-neon-green-500/20'
                                        : 'bg-steel-500/20 text-steel-300 border border-steel-500/30'
                                }`}>
                                    <div className={`w-2 h-2 rounded-full ${
                                        isMarketOpen ? 'bg-neon-green-400 live-dot' : 'bg-steel-400'
                                    }`} />
                                    {isMarketOpen ? 'OPEN' : 'CLOSED'}
                                </div>
                            </div>

                            <div className="text-3xl font-black text-white mb-2 text-display drop-shadow">
                                {isMarketOpen ? 'Trading Live' : 'After Hours'}
                            </div>
                            <p className="text-sm text-electric-blue-200 leading-relaxed">
                                {isMarketOpen
                                    ? 'AI agents are actively analyzing and executing trades'
                                    : 'Next session at 09:30 ET'}
                            </p>
                        </div>

                        <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-3xl p-6 shadow-2xl hover:shadow-3xl transition-all duration-300 hover:scale-[1.02]">
                            <div className="flex items-center justify-between mb-4">
                                <span className="text-xs font-black text-electric-blue-200 uppercase tracking-widest">
                                    How I'm Feeling
                                </span>
                                <div className="flex items-center gap-2">
                                    <span className="text-2xl animate-float">{fallbackSentiment.emoji}</span>
                                    {isStale && marketFeeling && (
                                        <span className="text-xs px-2 py-0.5 bg-amber-500/20 text-amber-300 rounded-full" title="Data is older than 4 hours">
                                            ⚠
                                        </span>
                                    )}
                                </div>
                            </div>

                            <div className={`text-3xl sm:text-4xl font-black mb-3 text-display drop-shadow ${getDirectionColor(fallbackSentiment.direction)}`}>
                                {fallbackSentiment.label}
                            </div>

                            {fallbackSentiment.direction && (
                                <div className="flex items-center gap-2 mb-4">
                                    <span className={`text-xs font-bold px-2 py-1 rounded-full border ${
                                        fallbackSentiment.direction === 'BULLISH'
                                            ? 'bg-neon-green-500/20 text-neon-green-300 border-neon-green-500/30'
                                            : fallbackSentiment.direction === 'BEARISH'
                                            ? 'bg-alert-red-500/20 text-alert-red-300 border-alert-red-500/30'
                                            : 'bg-steel-500/20 text-steel-300 border-steel-500/30'
                                    }`}>
                                        {fallbackSentiment.direction}
                                    </span>
                                </div>
                            )}

                            {fallbackSentiment.confidence !== null && (
                                <div className="flex items-center gap-2 mb-4">
                                    <span className="text-[10px] text-electric-blue-200 uppercase tracking-wider">Confidence</span>
                                    <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden shadow-inner max-w-[120px]">
                                        <div
                                            className={`h-full ${getConfidenceColor(fallbackSentiment.confidence)} transition-all duration-1000`}
                                            style={{ width: `${fallbackSentiment.confidence}%` }}
                                        />
                                    </div>
                                    <span className="text-xs font-bold text-white tabular-nums">{fallbackSentiment.confidence}%</span>
                                </div>
                            )}

                            {fallbackSentiment.why && (
                                <p className="text-sm text-electric-blue-100 leading-relaxed mb-4 italic">
                                    "{fallbackSentiment.why}"
                                </p>
                            )}

                            {fallbackSentiment.primaryConcern && (
                                <div className="flex flex-wrap gap-2 mb-4">
                                    <span className="text-[10px] text-electric-blue-300 uppercase tracking-wider">Concern:</span>
                                    <span className="text-xs px-2 py-1 bg-white/5 rounded-lg text-electric-blue-100 border border-white/10">
                                        {fallbackSentiment.primaryConcern}
                                    </span>
                                </div>
                            )}

                            {totalTrades > 0 && (
                                <div className="flex gap-4 pt-4 border-t border-white/10">
                                    <div className="flex-1 text-center p-3 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10 hover:bg-white/10 transition-all duration-300">
                                        <div className="text-2xl font-black text-neon-green-400 drop-shadow">{buyCount}</div>
                                        <div className="text-[10px] text-electric-blue-200 uppercase tracking-wider font-bold">Buys</div>
                                    </div>
                                    <div className="flex-1 text-center p-3 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10 hover:bg-white/10 transition-all duration-300">
                                        <div className="text-2xl font-black text-alert-red-400 drop-shadow">{sellCount}</div>
                                        <div className="text-[10px] text-electric-blue-200 uppercase tracking-wider font-bold">Sells</div>
                                    </div>
                                </div>
                            )}

                            <div className="flex items-center gap-2 mt-4 pt-3 border-t border-white/10">
                                <span className="text-[10px] text-electric-blue-300">
                                    {marketFeeling?.created_at
                                        ? `Last analyzed: ${formatTimeAgo(marketFeeling.created_at)}`
                                        : 'Waiting for analysis...'}
                                </span>
                                {marketFeeling?.model_used && (
                                    <span className="text-[10px] text-electric-blue-400/50">• {marketFeeling.model_used}</span>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

function StatBadge({ icon, label, value }: { icon: string; label: string; value: number }) {
    return (
        <div className="group flex items-center gap-3 px-4 py-2.5 bg-white/10 backdrop-blur-sm rounded-xl border border-white/20 hover:bg-white/15 hover:scale-105 hover:border-white/30 transition-all duration-300 shadow-lg hover:shadow-xl cursor-default">
            <span className="text-2xl group-hover:scale-110 transition-transform duration-300">{icon}</span>
            <div>
                <div className="text-2xl font-black text-white drop-shadow">{value}</div>
                <div className="text-[10px] text-electric-blue-200 uppercase tracking-wider font-bold">{label}</div>
            </div>
        </div>
    )
}
