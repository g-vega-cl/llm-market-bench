import { cn } from '../lib/cn';

/**
 * ErrorCard pattern.
 *
 * Displays an inline error message. Used inside pages and components
 * where a full error boundary is too heavy.
 */

export interface ErrorCardProps {
    title?: string;
    message: string;
    className?: string;
    onRetry?: () => void;
}

export function ErrorCard({ title = 'Error', message, className, onRetry }: ErrorCardProps) {
    return (
        <div
            className={cn(
                'voxel-card rounded-none w-full max-w-2xl p-4 bg-boxel-surface border-t-danger/70 border-l-danger/70 flex flex-col gap-3',
                className,
            )}
        >
            <div className="flex flex-col gap-1">
                <h3 className="text-sm font-bold text-danger">{title}</h3>
                <p className="text-xs font-normal text-boxel-muted leading-relaxed">{message}</p>
            </div>
            {onRetry && (
                <div>
                    <button
                        type="button"
                        onClick={onRetry}
                        className="voxel-btn rounded-none px-3 py-1.5 text-sm font-bold text-white bg-danger hover:bg-danger/90 transition-colors uppercase tracking-wider"
                    >
                        Retry
                    </button>
                </div>
            )}
        </div>
    );
}
