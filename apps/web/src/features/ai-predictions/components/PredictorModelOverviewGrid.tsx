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
                    <h3 className="text-lg font-bold text-boxel-ink flex items-center gap-2">
                        <span>🤖</span> Multi-Model Sector Autoresearch Tracks
                    </h3>
                    <p className="text-xs font-normal text-boxel-muted">
                        Independent Karpathy prompt evolution loops and ratchet baselines per model.
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,14rem),1fr))] gap-4 items-stretch">
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
                            className="p-5 bg-boxel-surface border border-boxel-bevel-hi rounded-none hover:border-accent cursor-pointer transition-all flex flex-col justify-between gap-4 h-full group"
                        >
                            <div className="flex items-start justify-between gap-2">
                                <div>
                                    <span className="text-sm font-bold text-boxel-ink group-hover:text-accent transition-colors">
                                        {s.track.label}
                                    </span>
                                    <div className="text-xs font-normal text-boxel-muted mt-0.5">
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

                            <div className="flex flex-col gap-2 pt-1 border-t border-boxel-bevel-hi">
                                <div>
                                    <div className="text-sm font-bold text-boxel-muted uppercase tracking-wider">
                                        Active Variant
                                    </div>
                                    <div className="text-sm font-mono font-bold text-accent truncate">
                                        {s.activeVariant}
                                    </div>
                                </div>

                                <div>
                                    <div className="text-sm font-bold text-boxel-muted uppercase tracking-wider">
                                        Ratchet Baseline Score
                                    </div>
                                    <div className="text-lg font-mono font-bold text-emerald-400">
                                        {s.baselineScore}
                                    </div>
                                </div>
                            </div>

                            <div className="text-xs font-normal text-boxel-muted group-hover:text-accent transition-colors flex items-center justify-between mt-auto">
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
