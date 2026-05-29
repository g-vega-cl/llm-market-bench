import type { CauseAndEffectEntry } from '../api/fetch-cause-and-effect';

export function CauseAndEffectCard({ entry }: { entry: CauseAndEffectEntry }) {
    const { event, analysis, market_outcome, confidence, tags, created_at } = entry;

    return (
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-8 hover:border-blue-900/50 transition-all group">
            <div className="flex flex-col md:flex-row md:items-start gap-8">
                <div className="flex-1 space-y-6">
                    <div className="flex items-center gap-4 text-[10px] uppercase tracking-widest font-bold text-zinc-500">
                        <span>
                            {new Date(created_at).toLocaleDateString('en-US', {
                                timeZone: 'America/New_York',
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                            })}
                        </span>
                        <span className="w-1 h-1 bg-zinc-800 rounded-full" />
                        <span className="text-blue-500">Confidence: {confidence}%</span>
                    </div>

                    <div>
                        <h3 className="text-2xl font-bold text-zinc-200 mb-2 group-hover:text-blue-400 transition-colors">
                            {event?.content
                                ? event.content.split('\n')[0].substring(0, 80)
                                : 'Market Event Analysis'}
                        </h3>
                        <p className="text-zinc-400 leading-relaxed line-clamp-3">
                            {event?.content}
                        </p>
                    </div>

                    <div className="p-6 bg-blue-500/5 border border-blue-500/10 rounded-xl">
                        <div className="text-[10px] uppercase tracking-widest font-bold text-blue-400 mb-2">
                            Market Outcome
                        </div>
                        <div className="text-lg font-semibold text-zinc-200">{market_outcome}</div>
                    </div>

                    <div className="space-y-3">
                        <div className="text-[10px] uppercase tracking-widest font-bold text-zinc-500">
                            Causal Analysis
                        </div>
                        <div className="text-sm text-zinc-400 leading-relaxed whitespace-pre-wrap">
                            {analysis}
                        </div>
                    </div>

                    <div className="flex flex-wrap gap-2 pt-2">
                        {tags?.map((tag: string) => (
                            <span
                                key={tag}
                                className="px-3 py-1 bg-zinc-800 text-zinc-400 text-[10px] uppercase font-bold rounded-full border border-zinc-700"
                            >
                                {tag}
                            </span>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
