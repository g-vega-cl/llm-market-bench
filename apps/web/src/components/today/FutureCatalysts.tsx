import * as React from 'react'

interface FutureCatalystsProps {
    events: any[]
}

function extractDate(content: string): string | null {
    const match = content.match(/(\d{4}-\d{2}-\d{2})/)
    return match ? match[1] : null
}

function getCountdown(targetDate: Date) {
    const now = new Date()
    const diff = targetDate.getTime() - now.getTime()

    if (diff <= 0) return { days: 0, hours: 0, minutes: 0, isPassed: true }

    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))

    return { days, hours, minutes, isPassed: false }
}

function getImportanceColor(score: number) {
    if (score >= 9) return 'from-alert-red-500 to-rose-600'
    if (score >= 8) return 'from-cyber-yellow-500 to-amber-600'
    if (score >= 6) return 'from-electric-blue-500 to-blue-600'
    return 'from-steel-400 to-zinc-500'
}

function getImportanceLabel(score: number) {
    if (score >= 9) return 'Critical'
    if (score >= 8) return 'High'
    if (score >= 6) return 'Medium'
    return 'Low'
}

export function FutureCatalysts({ events }: FutureCatalystsProps) {
    const [, forceUpdate] = React.useState({})

    // Update countdowns every minute
    React.useEffect(() => {
        const interval = setInterval(() => forceUpdate({}), 60 * 1000)
        return () => clearInterval(interval)
    }, [])

    if (!events.length) return null

    // Sort by date
    const sortedEvents = [...events].sort((a, b) => {
        const dateA = a.target_date || extractDate(a.content)
        const dateB = b.target_date || extractDate(b.content)
        if (!dateA && !dateB) return 0
        if (!dateA) return 1
        if (!dateB) return -1
        return new Date(dateA).getTime() - new Date(dateB).getTime()
    })

    // Filter out passed events and count only visible ones
    const visibleEvents = sortedEvents.filter(event => {
        const eventDate = event.target_date || extractDate(event.content)
        const dateObj = eventDate ? new Date(eventDate + 'T00:00:00') : null
        const countdown = dateObj ? getCountdown(dateObj) : null
        return !countdown?.isPassed
    })

    return (
        <section className="space-y-8 animate-slide-up">
            <div className="flex items-center justify-between">
                <h2 className="text-3xl font-black text-zinc-900 dark:text-white flex items-center gap-4 text-display">
                    <span className="w-3 h-10 bg-gradient-to-b from-cyber-yellow-500 to-amber-600 rounded-full" />
                    <span className="text-gradient text-gradient-catalyst">Horizon Watch: Pending Events</span>
                </h2>

                <div className="flex items-center gap-2 px-4 py-2 bg-cyber-yellow-50 dark:bg-cyber-yellow-950/20 border border-cyber-yellow-200 dark:border-cyber-yellow-900/30 rounded-xl">
                    <span className="text-[10px] font-black text-cyber-yellow-600 dark:text-cyber-yellow-400 uppercase tracking-widest">
                        📅 {visibleEvents.length} Catalyst{visibleEvents.length !== 1 ? 's' : ''}
                    </span>
                </div>
            </div>

            {/* Timeline View */}
            <div className="relative">
                {/* Timeline Line */}
                <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gradient-to-b from-cyber-yellow-500 via-amber-500 to-transparent opacity-30" />

                <div className="space-y-4">
                    {visibleEvents.map((event, idx) => {
                        const dateNote = event.metadata?.future_date_note
                        const eventDate = event.target_date || extractDate(event.content)
                        const dateObj = eventDate ? new Date(eventDate + 'T00:00:00') : null
                        const countdown = dateObj ? getCountdown(dateObj) : null
                        const importanceScore = event.metadata?.importance_score || 7

                        // Skip if passed
                        if (countdown?.isPassed) return null

                        return (
                            <div
                                key={event.id}
                                className="relative pl-20 animate-slide-up group"
                                style={{ animationDelay: `${idx * 100}ms` }}
                            >
                                {/* Timeline Dot */}
                                <div className={`absolute left-6 top-6 w-5 h-5 rounded-full border-4 border-white dark:border-zinc-950 shadow-lg bg-gradient-to-br ${getImportanceColor(importanceScore)} z-10 group-hover:scale-125 transition-transform`} />

                                {/* Card */}
                                <div className="p-6 border border-zinc-200 dark:border-zinc-800 rounded-3xl bg-white dark:bg-zinc-900 shadow-sm hover:shadow-xl transition-all duration-300 card-lift border-l-4" style={{ borderLeftColor: dateObj && countdown && countdown.days <= 3 ? '#ef4444' : '#eab308' }}>
                                    {/* Header */}
                                    <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
                                        <div className="flex-1 min-w-0">
                                            {/* Date & Time Badge */}
                                            <div className="flex flex-wrap items-center gap-2 mb-3">
                                                {dateObj && countdown && (
                                                    <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-cyber-yellow-100 to-amber-100 dark:from-cyber-yellow-900/30 dark:to-amber-900/30 text-cyber-yellow-700 dark:text-cyber-yellow-300 text-xs font-black rounded-lg border border-cyber-yellow-200 dark:border-cyber-yellow-800">
                                                        <span className="text-lg">⏱️</span>
                                                        <span className="font-mono">
                                                            {countdown.days}d {countdown.hours}h {countdown.minutes}m
                                                        </span>
                                                    </div>
                                                )}
                                                {dateNote && (
                                                    <span className="px-2.5 py-1 bg-zinc-100 dark:bg-zinc-800 text-zinc-500 text-[9px] font-bold uppercase tracking-wider rounded">
                                                        {dateNote}
                                                    </span>
                                                )}
                                                <span className={`px-2.5 py-1 rounded-lg text-[9px] font-black uppercase tracking-wider border ${
                                                    importanceScore >= 9
                                                        ? 'bg-alert-red-50 dark:bg-alert-red-950/20 text-alert-red-600 dark:text-alert-red-400 border-alert-red-200 dark:border-alert-red-900/30'
                                                        : importanceScore >= 8
                                                        ? 'bg-cyber-yellow-50 dark:bg-cyber-yellow-950/20 text-cyber-yellow-600 dark:text-cyber-yellow-400 border-cyber-yellow-200 dark:border-cyber-yellow-900/30'
                                                        : 'bg-electric-blue-50 dark:bg-electric-blue-950/20 text-electric-blue-600 dark:text-electric-blue-400 border-electric-blue-200 dark:border-electric-blue-900/30'
                                                }`}>
                                                    {getImportanceLabel(importanceScore)}
                                                </span>
                                            </div>

                                            {/* Event Time if available */}
                                            {event.metadata?.event_time && event.metadata.event_time !== 'N/A' && (
                                                <div className="flex items-center gap-1.5 text-xs text-zinc-500 dark:text-zinc-400 mb-2">
                                                    <span>🕐</span>
                                                    <span className="font-mono">{event.metadata.event_time}</span>
                                                </div>
                                            )}
                                        </div>

                                        {/* Date Display */}
                                        {dateObj && (
                                            <div className="text-right">
                                                <div className="text-2xl font-black text-zinc-900 dark:text-white text-display">
                                                    {dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                                                </div>
                                                <div className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider">
                                                    {dateObj.toLocaleDateString('en-US', { year: 'numeric' })}
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    {/* Content */}
                                    <p className="text-base text-zinc-800 dark:text-zinc-200 font-bold leading-relaxed mb-4">
                                        {event.content}
                                    </p>

                                    {/* Scenario Analysis */}
                                    {event.metadata?.scenario_analysis && (
                                        <div className="mt-4 pt-4 border-t border-zinc-100 dark:border-zinc-800">
                                            <div className="flex items-center gap-2 mb-3">
                                                <span className="text-lg">🔮</span>
                                                <h4 className="text-[10px] font-black text-cyber-yellow-600 dark:text-cyber-yellow-400 uppercase tracking-widest">
                                                    Scenarios & Trading Plans
                                                </h4>
                                            </div>
                                            <div className="bg-gradient-to-br from-cyber-yellow-50/50 via-amber-50/30 to-transparent dark:from-cyber-yellow-950/10 dark:via-amber-950/5 p-4 rounded-2xl border border-cyber-yellow-100 dark:border-cyber-yellow-900/30">
                                                <div className="text-[11px] text-zinc-700 dark:text-zinc-300 font-medium leading-relaxed whitespace-pre-wrap">
                                                    {event.metadata.scenario_analysis}
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {/* Tickers if available */}
                                    {event.metadata?.tickers && event.metadata.tickers.length > 0 && (
                                        <div className="mt-4 flex flex-wrap gap-2">
                                            {event.metadata.tickers.map((ticker: string, i: number) => (
                                                <span
                                                    key={i}
                                                    className="px-3 py-1.5 bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 text-[10px] font-bold rounded-lg uppercase tracking-wider border border-zinc-200 dark:border-zinc-700 hover:border-cyber-yellow-500 transition-colors"
                                                >
                                                    {ticker}
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        )
                    })}
                </div>
            </div>
        </section>
    )
}
