import { SubHeading } from '@llm-market-bench/ui-design-system';
import type { Checkpoint } from './daily-score-math';

interface CheckpointCardProps {
    cp: Checkpoint;
    idx: number;
    isActive: boolean;
    isSelected: boolean;
    onSelect: () => void;
}

export function CheckpointCard({ cp, idx, isActive, isSelected, onSelect }: CheckpointCardProps) {
    let buttonClass = 'p-3 rounded-xl border transition-all duration-300 w-full text-left';

    if (cp.isFuture) {
        buttonClass +=
            ' bg-zinc-950/20 border-zinc-900/50 opacity-40 select-none cursor-not-allowed';
    } else if (isSelected) {
        if (cp.score >= 0) {
            buttonClass +=
                ' bg-emerald-950/20 border-emerald-500/60 shadow-[0_0_12px_rgba(16,185,129,0.15)] cursor-pointer';
        } else {
            buttonClass +=
                ' bg-rose-950/20 border-rose-500/60 shadow-[0_0_12px_rgba(239,68,68,0.15)] cursor-pointer';
        }
    } else if (idx === 4 && isActive) {
        buttonClass +=
            ' bg-zinc-800/40 border-emerald-500/30 shadow-[0_0_12px_rgba(16,185,129,0.05)] cursor-pointer hover:border-zinc-700';
    } else {
        buttonClass +=
            ' bg-zinc-950/40 border-zinc-850 hover:border-zinc-700 cursor-pointer hover:bg-zinc-900/20';
    }

    return (
        <button type="button" disabled={cp.isFuture} onClick={onSelect} className={buttonClass}>
            <div className="flex items-center justify-between gap-1 w-full">
                <div className="text-[9px] font-black text-zinc-500 uppercase tracking-widest">
                    {cp.day.substring(0, 3)}
                </div>
                {cp.dateStr && (
                    <div className="text-[8px] font-bold text-zinc-400 font-mono bg-zinc-800 px-1 py-0.5 rounded-sm">
                        {cp.dateStr}
                    </div>
                )}
            </div>
            {cp.isFuture ? (
                <>
                    <div className="text-xs font-mono font-bold mt-1 text-zinc-500">N/A</div>
                    <div className="text-[8px] text-zinc-500 font-mono mt-0.5">P: N/A</div>
                </>
            ) : (
                <>
                    <div
                        className={`text-xs font-mono font-bold mt-1 ${cp.score >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}
                    >
                        {cp.score >= 0 ? '+' : ''}
                        {cp.score.toFixed(3)}
                    </div>
                    <div className="text-[8px] text-zinc-400 font-mono mt-0.5">
                        P: {cp.portfolio.toFixed(2)}%
                    </div>
                </>
            )}
        </button>
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
        <div className="space-y-3 relative z-10 pt-2">
            <SubHeading className="text-zinc-300 text-xs font-black uppercase tracking-wider">
                Day-by-Day Score Progression
            </SubHeading>

            <div className="grid grid-cols-5 gap-2">
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
