import type { PromptExperiment } from '@llm-market-bench/database';
import { Badge, Button } from '@llm-market-bench/ui-design-system';
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
            <Button
                type="button"
                variant={isAllActive ? 'solid' : 'outline'}
                colorScheme={isAllActive ? 'accent' : 'neutral'}
                onClick={() => onSelectTrack('all')}
                className="whitespace-nowrap"
            >
                <span>All Models</span>
                <Badge
                    variant={isAllActive ? 'solid' : 'soft'}
                    colorScheme={isAllActive ? 'accent' : 'neutral'}
                    size="xs"
                >
                    {totalCount}
                </Badge>
            </Button>

            {/* Individual Model Tracks */}
            {tracks.map((trk) => {
                const isActive = activeTrack === trk.id;
                const count = trackCounts[trk.id] ?? 0;
                const isCold = trackCold[trk.id] ?? false;

                return (
                    <Button
                        key={trk.id}
                        type="button"
                        variant={isActive ? 'solid' : 'outline'}
                        colorScheme={isActive ? 'accent' : 'neutral'}
                        onClick={() => onSelectTrack(trk.id)}
                        className="whitespace-nowrap"
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
                    </Button>
                );
            })}
        </div>
    );
}
