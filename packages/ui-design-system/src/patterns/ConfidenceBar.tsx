import * as React from 'react';
import { cn } from '../lib/cn';

export interface ConfidenceBarProps {
    label: string;
    value: number;
    colorScheme?: 'accent' | 'success' | 'danger' | 'info' | 'warning';
    textStyle?: 'default' | 'hero';
    className?: string;
}

const barBg: Record<string, string> = {
    accent: 'bg-accent',
    success: 'bg-neon-green-500',
    danger: 'bg-alert-red-500',
    info: 'bg-deep-purple-500',
    warning: 'bg-amber-500',
};

export function ConfidenceBar({
    label,
    value,
    colorScheme = 'accent',
    textStyle = 'default',
    className,
}: ConfidenceBarProps) {
    const clampedValue = Math.max(0, Math.min(100, value));
    const barColorClass = barBg[colorScheme] ?? barBg.accent;
    const isHero = textStyle === 'hero';

    return (
        <div className={cn('flex items-center gap-2', className)}>
            <span
                className={cn(
                    'text-[10px] font-black uppercase tracking-wider',
                    isHero ? 'text-white/70' : 'text-zinc-400',
                )}
            >
                {label}
            </span>
            <div
                className={cn(
                    'flex-1 h-2 rounded-full overflow-hidden shadow-inner max-w-[120px]',
                    isHero ? 'bg-white/10' : 'bg-zinc-100 dark:bg-zinc-800',
                )}
            >
                <div
                    className={cn(
                        'h-full rounded-full transition-all duration-1000 shadow-lg',
                        barColorClass,
                    )}
                    style={{ width: `${clampedValue}%` }}
                />
            </div>
            <span
                className={cn(
                    'text-xs font-bold tabular-nums',
                    isHero ? 'text-white' : 'text-zinc-500 dark:text-zinc-300',
                )}
            >
                {clampedValue}%
            </span>
        </div>
    );
}
