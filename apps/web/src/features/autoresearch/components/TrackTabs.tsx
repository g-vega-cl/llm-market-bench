import type { PromptExperiment } from '@llm-market-bench/database';
import { Badge } from '@llm-market-bench/ui-design-system';

interface TrackTabsProps {
    experiments: PromptExperiment[];
    activeTrack: string;
    onSelectTrack: (trackId: string) => void;
}

export function formatTrackLabel(trackId: string): string {
    if (!trackId || trackId === 'track_default') return 'Default Track (Combined)';
    const clean = trackId.replace(/^track_/, '').replace(/_/g, ' ');
    return clean.charAt(0).toUpperCase() + clean.slice(1);
}

export function TrackTabs({ experiments, activeTrack, onSelectTrack }: TrackTabsProps) {
    // Derive unique track IDs from experiments, defaulting missing track_id to 'track_default'
    const tracksSet = new Set<string>();
    tracksSet.add('track_default');

    for (const exp of experiments) {
        const tid = exp.track_id || 'track_default';
        tracksSet.add(tid);
    }

    const availableTracks = Array.from(tracksSet);

    // Count experiments per track
    const counts = availableTracks.reduce<Record<string, number>>((acc, tid) => {
        acc[tid] = experiments.filter((e) => (e.track_id || 'track_default') === tid).length;
        return acc;
    }, {});

    return (
        <div className="flex items-center space-x-2 border-b border-zinc-200 dark:border-zinc-800 pb-2 overflow-x-auto">
            {availableTracks.map((tid) => {
                const isActive = activeTrack === tid;
                const count = counts[tid] || 0;

                return (
                    <button
                        key={tid}
                        type="button"
                        onClick={() => onSelectTrack(tid)}
                        className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all whitespace-nowrap ${
                            isActive
                                ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30'
                                : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800/50'
                        }`}
                    >
                        <span>{formatTrackLabel(tid)}</span>
                        <Badge
                            variant={isActive ? 'solid' : 'soft'}
                            colorScheme={isActive ? 'accent' : 'neutral'}
                            className="text-xs px-2 py-0.5"
                        >
                            {count}
                        </Badge>
                    </button>
                );
            })}
        </div>
    );
}
