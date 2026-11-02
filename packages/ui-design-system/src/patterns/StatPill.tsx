import { cn } from '../lib/cn';

export interface StatPillProps {
    label: string;
    value: number;
    colorScheme?: 'accent' | 'success' | 'danger' | 'info' | 'warning' | 'neutral';
    isActive?: boolean;
    onClick?: () => void;
    className?: string;
}

const dotBg: Record<string, string> = {
    accent: 'bg-accent',
    success: 'bg-neon-green-500',
    danger: 'bg-alert-red-500',
    info: 'bg-deep-purple-500',
    warning: 'bg-amber-500',
    neutral: 'bg-zinc-400',
};

export function StatPill({
    label,
    value,
    colorScheme = 'neutral',
    isActive = false,
    onClick,
    className,
}: StatPillProps) {
    const dotColorClass = dotBg[colorScheme] ?? dotBg.neutral;

    return (
        <button
            type="button"
            onClick={onClick}
            className={cn(
                'voxel-btn rounded-none flex items-center gap-2 px-3 py-1.5 bg-boxel-surface transition-all duration-150 cursor-pointer',
                isActive ? 'border-accent bg-boxel-elevated' : 'hover:bg-boxel-elevated',
                className,
            )}
        >
            <div className={cn('w-2 h-2 rounded-none shrink-0', dotColorClass)} />
            <span
                className={cn(
                    'text-xs font-normal uppercase tracking-wider',
                    isActive ? 'text-boxel-ink' : 'text-boxel-muted',
                )}
            >
                {label}
            </span>
            <span
                className={cn(
                    'text-sm font-bold tabular-nums',
                    isActive ? 'text-accent' : 'text-boxel-ink',
                )}
            >
                {value}
            </span>
        </button>
    );
}
