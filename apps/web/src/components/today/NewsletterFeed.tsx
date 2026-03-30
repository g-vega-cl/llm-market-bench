import * as React from 'react'

interface NewsletterFeedProps {
    newsletters: any[]
}

export function NewsletterFeed({ newsletters }: NewsletterFeedProps) {
    if (!newsletters.length) return null

    return (
        <section className="space-y-8 animate-slide-up">
            <div className="flex items-center justify-between">
                <h2 className="text-3xl font-black text-zinc-900 dark:text-white flex items-center gap-4 text-display">
                    <span className="w-3 h-10 bg-gradient-to-b from-electric-blue-500 to-blue-600 rounded-full" />
                    <span className="text-gradient text-gradient-electric">Daily Intelligence Briefing</span>
                </h2>

                <div className="flex items-center gap-2 px-4 py-2 bg-electric-blue-50 dark:bg-electric-blue-950/20 border border-electric-blue-200 dark:border-electric-blue-900/30 rounded-xl">
                    <span className="text-[10px] font-black text-electric-blue-600 dark:text-electric-blue-400 uppercase tracking-widest">
                        📰 {newsletters.length} Brief{newsletters.length !== 1 ? 's' : ''}
                    </span>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {newsletters.map((news, idx) => (
                    <div
                        key={news.id}
                        className="group relative p-6 border border-zinc-200 dark:border-zinc-800 rounded-3xl bg-white dark:bg-zinc-900 shadow-sm hover:shadow-xl transition-all duration-300 card-lift overflow-hidden animate-slide-up"
                        style={{ animationDelay: `${idx * 100}ms` }}
                    >
                        {/* Gradient Hover Border */}
                        <div className="absolute inset-0 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none border-2 border-electric-blue-500/30" />

                        {/* Header */}
                        <div className="flex justify-between items-start mb-4 relative">
                            <div className="flex items-center gap-2">
                                <span className="px-3 py-1.5 bg-gradient-to-r from-electric-blue-100 to-blue-100 dark:from-electric-blue-900/30 dark:to-blue-900/30 text-electric-blue-700 dark:text-electric-blue-300 text-[9px] font-black uppercase tracking-widest rounded-xl border border-electric-blue-200 dark:border-electric-blue-800">
                                    {news.sender}
                                </span>
                                {news.has_attachments && (
                                    <span className="px-2 py-1 bg-zinc-100 dark:bg-zinc-800 text-zinc-500 text-[9px] font-bold rounded-lg uppercase tracking-wider">
                                        📎
                                    </span>
                                )}
                            </div>
                            <span className="text-[10px] text-zinc-400 font-mono flex items-center gap-1">
                                <span className="w-1.5 h-1.5 bg-electric-blue-400 rounded-full" />
                                {new Date(news.date).toLocaleTimeString([], {
                                    hour: '2-digit',
                                    minute: '2-digit'
                                })}
                            </span>
                        </div>

                        {/* Content */}
                        <h3 className="text-lg font-bold text-zinc-900 dark:text-white mb-3 group-hover:text-electric-blue-500 transition-colors line-clamp-2 leading-snug">
                            {news.subject}
                        </h3>
                        <p className="text-sm text-zinc-500 dark:text-zinc-400 line-clamp-4 font-light leading-relaxed">
                            {news.content}
                        </p>

                        {/* Footer */}
                        <div className="mt-4 pt-4 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
                            <span className="text-[9px] font-black text-zinc-400 uppercase tracking-widest">
                                {news.content?.length || 0} characters
                            </span>
                            <span className="text-[9px] font-bold text-electric-blue-500 uppercase tracking-wider group-hover:translate-x-1 transition-transform inline-flex items-center gap-1">
                                Read More
                                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M5 12h14M12 5l7 7-7 7" />
                                </svg>
                            </span>
                        </div>
                    </div>
                ))}
            </div>
        </section>
    )
}
