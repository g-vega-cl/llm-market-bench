import type { PromptExperiment } from '@llm-market-bench/database';
import { Badge } from '@llm-market-bench/ui-design-system';
import {
    isSectorTrackColdStart,
    type SectorTrackConfig,
    type SectorTrackId,
} from '../lib/sector-tracks';

export interface PredictorTrackTabsProps {
    tracks: SectorTrackConfig[];
    activeTrack: SectorTrackId;
    onSelectTrack: (trackId: SectorTrackId) => void;
    experiments: PromptExperiment[];
}

export function PredictorTrackTabs({
    tracks,
    activeTrack,
    onSelectTrack,
    experiments,
}: PredictorTrackTabsProps) {
    const isAllActive = activeTrack === 'all';
    const totalCount = experiments.length;

    // Precalculate counts and cold start status per track
    const trackCounts: Record<string, number> = {};
    const trackCold: Record<string, boolean> = {};

    for (const trk of tracks) {
        const trkExps = experiments.filter((e) => trk.matches(e.track_id, e.variant_tag));
        trackCounts[trk.id] = trkExps.length;
        trackCold[trk.id] = isSectorTrackColdStart(trkExps);
    }

    return (
        <div className="flex items-center space-x-2 border-b border-slate-700/60 pb-3 overflow-x-auto">
            {/* "All Models" Tab */}
            <button
                type="button"
                onClick={() => onSelectTrack('all')}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all whitespace-nowrap ${
                    isAllActive
                        ? 'bg-blue-600/20 text-blue-400 border border-blue-500/40 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
            >
                <span>All Models</span>
                <Badge
                    variant={isAllActive ? 'solid' : 'soft'}
                    colorScheme={isAllActive ? 'accent' : 'neutral'}
                    size="xs"
                >
                    {totalCount}
                </Badge>
            </button>

            {/* Individual Model Tracks */}
            {tracks.map((trk) => {
                const isActive = activeTrack === trk.id;
                const count = trackCounts[trk.id] ?? 0;
                const isCold = trackCold[trk.id] ?? false;

                return (
                    <button
                        key={trk.id}
                        type="button"
                        onClick={() => onSelectTrack(trk.id)}
                        className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all whitespace-nowrap ${
                            isActive
                                ? 'bg-slate-800 text-white border border-slate-600 shadow-sm'
                                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                        }`}
                    >
                        <span>{trk.label}</span>
                        {isCold && (
                            <Badge variant="soft" colorScheme="warning" size="xs">
                                From 0
                            </Badge>
                        )}
                        <Badge
                            variant={isActive ? 'solid' : 'soft'}
                            colorScheme={isActive ? trk.badgeColorScheme : 'neutral'}
                            size="xs"
                        >
                            {count}
                        </Badge>
                    </button>
                );
            })}
        </div>
    );
}
