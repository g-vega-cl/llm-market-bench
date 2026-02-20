import * as React from 'react'

export function NewsletterFeed({ newsletters }: { newsletters: any[] }) {
    if (!newsletters.length) return null;
    return (
        <section className="space-y-6">
            <h2 className="text-2xl font-black text-zinc-900 dark:text-white flex items-center gap-3">
                <span className="w-2 h-8 bg-blue-500 rounded-full" />
                Daily Intelligence Briefing
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {newsletters.map((news) => (
                    <div key={news.id} className="p-6 border border-zinc-200 dark:border-zinc-800 rounded-3xl bg-white dark:bg-zinc-900 shadow-sm hover:shadow-md transition-all group">
                        <div className="flex justify-between items-center mb-4">
                            <span className="px-3 py-1 bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 text-[10px] font-black uppercase tracking-widest rounded-lg border border-zinc-200 dark:border-zinc-700">
                                {news.sender}
                            </span>
                            <span className="text-[10px] text-zinc-400 font-mono">
                                {new Date(news.date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                        </div>
                        <h3 className="text-lg font-bold text-zinc-900 dark:text-white mb-3 group-hover:text-blue-500 transition-colors line-clamp-2">
                            {news.subject}
                        </h3>
                        <p className="text-sm text-zinc-500 dark:text-zinc-400 line-clamp-4 font-light leading-relaxed">
                            {news.content}
                        </p>
                    </div>
                ))}
            </div>
        </section>
    )
}
