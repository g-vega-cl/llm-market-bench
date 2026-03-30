import * as React from 'react'

interface MarketStatusHeroProps {
    data: {
        trades?: any[]
        decisions?: any[]
        memories?: any[]
        priceUpdates?: any[]
        futureEvents?: any[]
        newsletters?: any[]
    }
}

export function MarketStatusHero({ data }: MarketStatusHeroProps) {
    const now = new Date()
    const currentHour = now.getUTCHours()
    const currentMinutes = now.getUTCMinutes()
    const dayOfWeek = now.getUTCDay()

    // Market hours: 09:30 - 16:00 ET = 13:30 - 20:00 UTC
    const isMarketOpen = dayOfWeek >= 1 && dayOfWeek <= 5 &&
        ((currentHour > 13 || (currentHour === 13 && currentMinutes >= 30)) && currentHour < 20)

    const totalTrades = data.trades?.length || 0
    const totalDecisions = data.decisions?.length || 0
    const activeMemories = data.memories?.filter(m => m.status === 'ACTIVE').length || 0

    // Calculate simple sentiment from trades
    const buyCount = data.trades?.filter(t => t.signal === 'BUY').length || 0
    const sellCount = data.trades?.filter(t => t.signal === 'SELL').length || 0
    const sentiment = totalTrades > 0
        ? buyCount > sellCount ? 'bullish' : sellCount > buyCount ? 'bearish' : 'neutral'
        : 'neutral'

    const sentimentConfig = {
        bullish: {
            label: 'Bullish',
            color: 'text-neon-green-500',
            bgColor: 'bg-neon-green-500',
            gradient: 'from-neon-green-500 to-emerald-600',
            emoji: '📈'
        },
        bearish: {
            label: 'Bearish',
            color: 'text-alert-red-500',
            bgColor: 'bg-alert-red-500',
            gradient: 'from-alert-red-500 to-rose-600',
            emoji: '📉'
        },
        neutral: {
            label: 'Neutral',
            color: 'text-steel-500',
            bgColor: 'bg-steel-500',
            gradient: 'from-steel-400 to-zinc-500',
            emoji: '⚖️'
        }
    }

    const currentSentiment = sentimentConfig[sentiment]

    return (
        <div className="relative overflow-hidden gradient-electric">
            {/* Animated Background Pattern */}
            <div className="absolute inset-0 opacity-10">
                <div className="absolute inset-0" style={{
                    backgroundImage: `radial-gradient(circle at 2px 2px, white 1px, transparent 0)`,
                    backgroundSize: '40px 40px'
                }} />
            </div>

            {/* Gradient Overlay */}
            <div className="absolute inset-0 bg-gradient-to-br from-electric-blue-600/90 via-deep-purple-600/80 to-electric-blue-800/90" />

            {/* Animated Orbs */}
            <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-electric-blue-400/20 rounded-full blur-3xl animate-pulse" />
            <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-deep-purple-400/20 rounded-full blur-3xl animate-pulse animate-stagger-2" />

            <div className="relative max-w-7xl mx-auto px-6 md:px-12 py-16 md:py-24">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-center">
                    {/* Left: Title & Date */}
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

                        {/* Quick Stats */}
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

                    {/* Right: Market Status & Sentiment */}
                    <div className="lg:col-span-1 space-y-6 animate-slide-up animate-stagger-2">
                        {/* Market Status Card */}
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

                        {/* AI Sentiment Card */}
                        <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-3xl p-6 shadow-2xl hover:shadow-3xl transition-all duration-300 hover:scale-[1.02]">
                            <div className="flex items-center justify-between mb-4">
                                <span className="text-xs font-black text-electric-blue-200 uppercase tracking-widest">
                                    AI Sentiment
                                </span>
                                <span className="text-2xl animate-float">{currentSentiment.emoji}</span>
                            </div>

                            <div className={`text-4xl font-black mb-4 text-display drop-shadow ${currentSentiment.color}`}>
                                {currentSentiment.label}
                            </div>

                            {/* Sentiment Bar */}
                            <div className="relative h-3 bg-white/10 rounded-full overflow-hidden shadow-inner">
                                <div
                                    className={`absolute inset-y-0 left-0 h-full bg-gradient-to-r ${currentSentiment.gradient} transition-all duration-1000 ease-out shadow-lg`}
                                    style={{
                                        width: sentiment === 'bullish' ? '75%' : sentiment === 'bearish' ? '25%' : '50%'
                                    }}
                                />
                                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-shimmer" />
                            </div>

                            <div className="flex justify-between mt-2 text-xs text-electric-blue-200 font-medium">
                                <span>Bearish</span>
                                <span>Neutral</span>
                                <span>Bullish</span>
                            </div>

                            {/* Trade Breakdown */}
                            {totalTrades > 0 && (
                                <div className="flex gap-4 mt-4 pt-4 border-t border-white/10">
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
