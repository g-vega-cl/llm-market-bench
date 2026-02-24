import * as React from 'react'

export function AgentInsights({ memories }: { memories: any[] }) {
    const consensus = memories.filter(m => m.memory_type === 'MARKET_EVENT');
    const lessons = memories.filter(m => m.memory_type === 'LESSON_LEARNED');
    const incentives = memories.filter(m => m.memory_type === 'GOVERNMENT_INCENTIVE');

    if (!consensus.length && !lessons.length && !incentives.length) return null;

    return (
        <section className="space-y-6">
            <h2 className="text-2xl font-black text-zinc-900 dark:text-white flex items-center gap-3">
                <span className="w-2 h-8 bg-indigo-500 rounded-full" />
                AI Cognitive Synthesis
            </h2>

            <div className="space-y-4">
                {consensus.map(m => (
                    <div key={m.id} className="p-6 border-l-4 border-indigo-500 rounded-r-3xl bg-indigo-50/30 dark:bg-indigo-900/10 border border-zinc-200 dark:border-zinc-800 shadow-sm">
                        <div className="flex justify-between items-start mb-2">
                            <span className="text-[9px] font-black text-indigo-600 dark:text-indigo-400 uppercase tracking-widest block">Market Consensus</span>
                            <span className="text-[9px] font-black text-zinc-400 uppercase tracking-widest block">
                                {new Date(m.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                            </span>
                        </div>
                        <p className="text-zinc-800 dark:text-zinc-200 font-medium leading-relaxed italic">"{m.content}"</p>
                    </div>
                ))}

                {incentives.map(m => (
                    <div key={m.id} className="p-6 border-l-4 border-emerald-500 rounded-r-3xl bg-emerald-50/30 dark:bg-emerald-900/10 border border-zinc-200 dark:border-zinc-800 shadow-sm">
                        <div className="flex justify-between items-start mb-2">
                            <span className="text-[9px] font-black text-emerald-600 dark:text-emerald-400 uppercase tracking-widest block">Government Incentive</span>
                            <span className="text-[9px] font-black text-zinc-400 uppercase tracking-widest block">
                                {new Date(m.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                            </span>
                        </div>
                        <p className="text-zinc-800 dark:text-zinc-200 font-medium leading-relaxed">{m.content}</p>
                    </div>
                ))}

                {lessons.map(m => (
                    <div key={m.id} className="p-6 border-l-4 border-amber-500 rounded-r-3xl bg-amber-50/30 dark:bg-amber-900/10 border border-zinc-200 dark:border-zinc-800 shadow-sm">
                        <div className="flex justify-between items-start mb-2">
                            <span className="text-[9px] font-black text-amber-600 dark:text-amber-400 uppercase tracking-widest block">Lesson Learned</span>
                            <span className="text-[9px] font-black text-zinc-400 uppercase tracking-widest block">
                                {new Date(m.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                            </span>
                        </div>
                        <p className="text-zinc-800 dark:text-zinc-200 font-medium leading-relaxed italic">"{m.content}"</p>
                    </div>
                ))}
            </div>
        </section>
    )
}
