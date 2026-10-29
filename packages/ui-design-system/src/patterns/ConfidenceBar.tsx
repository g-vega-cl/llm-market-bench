import { cn } from '../lib/cn';

export interface ConfidenceBarProps {
    label: string;
    value: number;
    colorScheme?: 'accent' | 'success' | 'danger' | 'info' | 'warning';
    textStyle?: 'default' | 'hero';
    className?: string;
}

const segmentBg: Record<string, string> = {
    accent: 'bg-accent',
    success: 'bg-success',
    danger: 'bg-danger',
    info: 'bg-info',
    warning: 'bg-warning',
};

const SEGMENT_INDICES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] as const;

export function ConfidenceBar({
    label,
    value,
    colorScheme = 'accent',
    textStyle = 'default',
    className,
}: ConfidenceBarProps) {
    const clampedValue = Math.max(0, Math.min(100, value));
    const filledSegments = Math.round(clampedValue / 10);
    const activeColorClass = segmentBg[colorScheme] ?? segmentBg.accent;
    const isHero = textStyle === 'hero';

    return (
        <div className={cn('flex items-center gap-2', className)}>
            <span
                className={cn(
                    'text-[10px] font-black uppercase tracking-wider',
                    isHero ? 'text-boxel-ink' : 'text-boxel-muted',
                )}
            >
                {label}
            </span>
            <div className="voxel-trough grid grid-cols-10 gap-0.5 p-1 flex-1 min-w-24 max-w-36">
                {SEGMENT_INDICES.map((idx) => {
                    const isFilled = idx < filledSegments;
                    return (
                        <span
                            key={idx}
                            data-testid="confidence-segment"
                            data-filled={isFilled ? 'true' : 'false'}
                            className={cn(
                                'h-2.5 rounded-none transition-colors',
                                isFilled ? activeColorClass : 'bg-boxel-surface/50',
                            )}
                        />
                    );
                })}
            </div>
            <span
                className={cn(
                    'text-xs font-bold font-mono tabular-nums',
                    isHero ? 'text-boxel-ink' : 'text-boxel-ink',
                )}
            >
                {clampedValue}%
            </span>
        </div>
    );
}
