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
                'flex items-center gap-2 px-3 py-1.5 bg-white dark:bg-zinc-900 border rounded-full shadow-sm transition-all duration-300 cursor-pointer',
                isActive
                    ? 'border-zinc-900 dark:border-white shadow-md scale-105'
                    : 'border-zinc-200 dark:border-zinc-800 hover:shadow-md hover:scale-105',
                className,
            )}
        >
            <div className={cn('w-2 h-2 rounded-full shadow-lg', dotColorClass)} />
            <span
                className={cn(
                    'text-[10px] font-black uppercase tracking-wider',
                    isActive ? 'text-zinc-900 dark:text-white' : 'text-zinc-400',
                )}
            >
                {label}
            </span>
            <span
                className={cn(
                    'text-sm font-black tabular-nums',
                    isActive ? 'text-zinc-900 dark:text-white' : 'text-zinc-500 dark:text-zinc-400',
                )}
            >
                {value}
            </span>
        </button>
    );
}
