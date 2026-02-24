import * as React from 'react'

export function FutureCatalysts({ events }: { events: any[] }) {
    if (!events.length) return null;
    return (
        <section className="space-y-6">
            <h2 className="text-2xl font-black text-zinc-900 dark:text-white flex items-center gap-3">
                <span className="w-2 h-8 bg-purple-500 rounded-full" />
                Horizon Watch: Pending Events
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {events.map((event) => (
                    <div key={event.id} className="p-6 border border-zinc-200 dark:border-zinc-800 rounded-3xl bg-white dark:bg-zinc-900 shadow-sm relative overflow-hidden group hover:border-purple-500 transition-colors">
                        <div className="absolute top-0 right-0 p-4">
                            <span className="px-2 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 text-[9px] font-black uppercase tracking-widest rounded">
                                {event.target_date || 'Ongoing'}
                            </span>
                        </div>
                        <p className="text-sm text-zinc-800 dark:text-zinc-200 font-bold leading-relaxed pr-16">
                            {event.content}
                        </p>
                    </div>
                ))}
            </div>
        </section>
    )
}
