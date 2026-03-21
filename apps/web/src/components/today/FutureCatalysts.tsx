import * as React from 'react'

function extractDate(content: string): string | null {
    const match = content.match(/(\d{4}-\d{2}-\d{2})/);
    return match ? match[1] : null;
}

export function FutureCatalysts({ events }: { events: any[] }) {
    if (!events.length) return null;
    return (
        <section className="space-y-6">
            <h2 className="text-2xl font-black text-zinc-900 dark:text-white flex items-center gap-3">
                <span className="w-2 h-8 bg-purple-500 rounded-full" />
                Horizon Watch: Pending Events
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {events.map((event) => {
                    const dateNote = event.metadata?.future_date_note;
                    const eventDate = event.target_date || extractDate(event.content);
                    
                    // Fix timezone shift by forcing local time parsing
                    const dateObj = eventDate ? new Date(eventDate + 'T00:00:00') : null;
                    const isPassed = dateObj ? dateObj < new Date(new Date().setHours(0, 0, 0, 0)) : false;

                    // Double safety: don't render passed events in Horizon Watch
                    if (isPassed) return null;

                    return (
                        <div key={event.id} className="p-6 border border-zinc-200 dark:border-zinc-800 rounded-3xl bg-white dark:bg-zinc-900 shadow-sm relative overflow-hidden group hover:border-purple-500 transition-colors">
                            <div className="absolute top-0 right-0 p-4">
                                <span className="bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 text-[9px] font-black uppercase tracking-widest rounded flex items-center gap-1.5 px-2 py-1">
                                    {eventDate ? (
                                        <>
                                            {dateNote && <span className="text-zinc-500 opacity-70">{dateNote}:</span>}
                                            {dateObj?.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                                            {event.metadata?.event_time && event.metadata.event_time !== 'N/A' && (
                                                <span className="ml-1 pl-1.5 border-l border-purple-200 dark:border-purple-800 text-purple-500 dark:text-purple-300">
                                                    {event.metadata.event_time}
                                                </span>
                                            )}
                                        </>
                                    ) : (dateNote || 'Ongoing')}
                                </span>
                            </div>
                            <p className="text-sm text-zinc-800 dark:text-zinc-200 font-bold leading-relaxed pr-16 text-pretty mb-4">
                                {event.content}
                            </p>
                            {event.metadata?.scenario_analysis && (
                                <div className="mt-4 pt-4 border-t border-zinc-100 dark:border-zinc-800 space-y-3">
                                    <h4 className="text-[10px] font-black uppercase tracking-widest text-purple-600 dark:text-purple-400">
                                        Scenarios & Trading Plans
                                    </h4>
                                    <div className="text-[11px] text-zinc-600 dark:text-zinc-400 font-medium leading-relaxed whitespace-pre-wrap">
                                        {event.metadata.scenario_analysis}
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}

            </div>
        </section>
    )
}
