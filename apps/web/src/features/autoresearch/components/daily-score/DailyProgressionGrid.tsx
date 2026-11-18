import { Button, SubHeading } from '@llm-market-bench/ui-design-system';
import type { Checkpoint } from './daily-score-math';

interface CheckpointCardProps {
    cp: Checkpoint;
    idx: number;
    isActive: boolean;
    isSelected: boolean;
    onSelect: () => void;
}

function getCheckpointStyle(
    cp: Checkpoint,
    idx: number,
    isActive: boolean,
    isSelected: boolean,
): { colorScheme: 'neutral' | 'warning' | 'success' | 'danger'; extra: string } {
    if (cp.isFuture) {
        return { colorScheme: 'neutral', extra: 'opacity-40 select-none' };
    }
    if (cp.isInProgress) {
        return { colorScheme: 'warning', extra: 'cursor-pointer' };
    }
    if (isSelected || (idx === 4 && isActive)) {
        return {
            colorScheme: cp.score >= 0 || (idx === 4 && isActive) ? 'success' : 'danger',
            extra: 'cursor-pointer',
        };
    }
    return { colorScheme: 'neutral', extra: 'cursor-pointer' };
}

function CheckpointBody({ cp }: { cp: Checkpoint }) {
    if (cp.isFuture) {
        return (
            <>
                <div className="text-sm font-bold font-mono mt-1 text-voxel-muted">N/A</div>
                <div className="text-xs text-voxel-muted font-mono font-normal mt-0.5">P: N/A</div>
            </>
        );
    }
    if (cp.isInProgress) {
        return (
            <>
                <div className="text-sm font-bold font-mono mt-1 text-amber-400 animate-pulse">
                    Pending
                </div>
                <div className="text-xs text-voxel-muted font-mono font-normal mt-0.5">
                    In Progress
                </div>
            </>
        );
    }
    return (
        <>
            <div
                className={`text-sm font-bold font-mono mt-1 ${cp.score >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}
            >
                {cp.score >= 0 ? '+' : ''}
                {cp.score.toFixed(3)}
            </div>
            <div className="text-xs text-voxel-muted font-mono font-normal mt-0.5">
                P: {cp.portfolio.toFixed(2)}%
            </div>
        </>
    );
}

export function CheckpointCard({ cp, idx, isActive, isSelected, onSelect }: CheckpointCardProps) {
    const { colorScheme, extra } = getCheckpointStyle(cp, idx, isActive, isSelected);
    return (
        <Button
            type="button"
            variant="outline"
            colorScheme={colorScheme}
            disabled={cp.isFuture}
            onClick={onSelect}
            className={`p-3 h-full w-full text-left flex flex-col justify-between ${extra}`}
        >
            <div className="flex items-center justify-between gap-1 w-full">
                <div className="text-sm font-bold text-voxel-muted uppercase tracking-wider">
                    {cp.day.substring(0, 3)}
                </div>
                {cp.dateStr && (
                    <div className="text-xs font-normal text-voxel-muted font-mono bg-voxel-trough px-1 py-0.5 rounded-none border border-voxel-bevel-hi">
                        {cp.dateStr}
                    </div>
                )}
            </div>
            <CheckpointBody cp={cp} />
        </Button>
    );
}

interface DailyProgressionGridProps {
    checkpoints: Checkpoint[];
    isActive: boolean;
    selectedDayName: string | null;
    onSelectDay: (dayName: string) => void;
}

export function DailyProgressionGrid({
    checkpoints,
    isActive,
    selectedDayName,
    onSelectDay,
}: DailyProgressionGridProps) {
    return (
        <div className="flex flex-col gap-3 relative z-10 pt-2">
            <SubHeading className="uppercase tracking-wider">
                Day-by-Day Score Progression
            </SubHeading>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,7rem),1fr))] gap-2 items-stretch">
                {checkpoints.map((cp, idx) => (
                    <CheckpointCard
                        key={cp.day}
                        cp={cp}
                        idx={idx}
                        isActive={isActive}
                        isSelected={selectedDayName === cp.day}
                        onSelect={() => onSelectDay(cp.day)}
                    />
                ))}
            </div>
        </div>
    );
}
