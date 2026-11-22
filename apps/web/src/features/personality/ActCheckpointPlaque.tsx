import { Button } from '@llm-market-bench/ui-design-system';

export interface ActCheckpointPlaqueProps {
    actTitle: string;
    /** Zero-based act index. */
    actIndex: number;
    totalActs: number;
    /** The letter this act settled on, e.g. `L`. */
    letter: string;
    /** Human pole label for that letter, e.g. `Multi-Quarter Thesis`. */
    poleLabel: string;
    strength: string;
    /** Axis value 0..100 — drives the single filled voxel bar. */
    value: number;
    onContinue: () => void;
}

/**
 * In-place checkpoint between acts. Renders as its own card at the same level as
 * the question step (never nested inside one), so replacing the step causes no
 * layout shift and needs no new page block.
 */
export function ActCheckpointPlaque({
    actTitle,
    actIndex,
    totalActs,
    letter,
    poleLabel,
    strength,
    value,
    onContinue,
}: ActCheckpointPlaqueProps) {
    const safeValue = Math.max(0, Math.min(100, Math.round(value)));

    return (
        <div
            data-testid="act-checkpoint"
            className="scene-scrim voxel-card flex w-full max-w-2xl flex-col gap-4 rounded-none p-6"
        >
            <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-2 border-b-2 border-voxel-bevel-hi pb-3">
                <h2 className="text-sm font-bold text-voxel-ink">
                    {`Act ${String(actIndex + 1)} of ${String(totalActs)} complete`}
                </h2>
                <span className="min-w-0 break-words text-xs font-normal text-voxel-muted">
                    {actTitle}
                </span>
            </div>

            <p className="text-sm font-bold text-accent">{`${letter} — ${poleLabel}`}</p>
            <p className="text-xs font-normal text-voxel-muted">{`Strength: ${strength}`}</p>

            <div className="flex flex-col gap-1">
                <div className="flex items-baseline justify-between gap-2">
                    <span className="text-xs font-normal text-voxel-muted">
                        How strongly you lean
                    </span>
                    <span className="text-xs font-normal text-voxel-muted">
                        {`${String(safeValue)} / 100`}
                    </span>
                </div>
                <div className="voxel-trough h-2 w-full overflow-hidden rounded-none">
                    <div className="h-full bg-accent" style={{ width: `${String(safeValue)}%` }} />
                </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 border-t-2 border-voxel-bevel-hi pt-3">
                <span className="min-w-0 break-words text-xs font-normal text-voxel-muted">
                    {actIndex + 1 < totalActs
                        ? `Act ${String(actIndex + 2)} of ${String(totalActs)} begins`
                        : 'Final act'}
                </span>
                <Button
                    type="button"
                    size="sm"
                    variant="solid"
                    colorScheme="accent"
                    data-testid="continue-act"
                    onClick={onContinue}
                >
                    Keep going
                </Button>
            </div>
        </div>
    );
}
