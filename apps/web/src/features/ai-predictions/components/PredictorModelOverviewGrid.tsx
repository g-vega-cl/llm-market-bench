import { Badge, Card } from '@llm-market-bench/ui-design-system';
import type { ModelTrackSummary, SectorTrackId } from '../lib/sector-tracks';

export interface PredictorModelOverviewGridProps {
    summaries: ModelTrackSummary[];
    onSelectTrack: (trackId: SectorTrackId) => void;
}

export function PredictorModelOverviewGrid({
    summaries,
    onSelectTrack,
}: PredictorModelOverviewGridProps) {
    return (
        <div className="space-y-4">
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-2">
                <div>
                    <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <span>🤖</span> Multi-Model Sector Autoresearch Tracks
                    </h3>
                    <p className="text-xs text-slate-400">
                        Independent Karpathy prompt evolution loops and ratchet baselines per model.
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {summaries.map((s) => {
                    const hasActive = s.status === 'active';
                    return (
                        <Card
                            key={s.track.id}
                            role="button"
                            tabIndex={0}
                            onClick={() => onSelectTrack(s.track.id)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                    onSelectTrack(s.track.id);
                                }
                            }}
                            className="p-5 bg-slate-800/40 border-slate-700/60 hover:border-slate-500 cursor-pointer transition-all hover:scale-[1.01] space-y-4 group"
                        >
                            <div className="flex items-start justify-between gap-2">
                                <div>
                                    <span className="text-sm font-bold text-white group-hover:text-blue-400 transition-colors">
                                        {s.track.label}
                                    </span>
                                    <div className="text-[11px] text-slate-400 mt-0.5">
                                        {s.experimentCount}{' '}
                                        {s.experimentCount === 1 ? 'Variant' : 'Variants'}
                                    </div>
                                </div>
                                <div className="flex items-center gap-1.5 flex-wrap justify-end">
                                    {s.isColdStart && (
                                        <Badge variant="soft" colorScheme="warning" size="xs">
                                            From 0
                                        </Badge>
                                    )}
                                    <Badge
                                        variant={hasActive ? 'solid' : 'soft'}
                                        colorScheme={hasActive ? 'success' : 'neutral'}
                                        size="xs"
                                    >
                                        {hasActive ? 'Active' : 'Saved'}
                                    </Badge>
                                </div>
                            </div>

                            <div className="space-y-2 pt-1 border-t border-slate-700/40">
                                <div>
                                    <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                                        Active Variant
                                    </div>
                                    <div className="text-sm font-mono font-bold text-blue-400 truncate">
                                        {s.activeVariant}
                                    </div>
                                </div>

                                <div>
                                    <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                                        Ratchet Baseline Score
                                    </div>
                                    <div className="text-xl font-mono font-black text-emerald-400">
                                        {s.baselineScore}
                                    </div>
                                </div>
                            </div>

                            <div className="text-[11px] font-medium text-slate-500 group-hover:text-blue-400 transition-colors flex items-center justify-between">
                                <span>Focus Track</span>
                                <span>→</span>
                            </div>
                        </Card>
                    );
                })}
            </div>
        </div>
    );
}
