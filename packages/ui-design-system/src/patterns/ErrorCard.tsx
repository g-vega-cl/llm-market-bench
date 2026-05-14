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
                'w-full max-w-2xl p-6 border border-danger/30 rounded-xl bg-danger-light/50 dark:bg-danger-dark/20',
                className,
            )}
        >
            <div className="flex items-start gap-3">
                <div>
                    <h3 className="text-sm font-bold text-danger mb-1">{title}</h3>
                    <p className="text-sm text-danger/80">{message}</p>
                </div>
            </div>
            {onRetry && (
                <div className="mt-4">
                    <button
                        type="button"
                        onClick={onRetry}
                        className="px-3 py-1.5 text-xs font-medium text-white bg-danger rounded-lg hover:bg-danger/90 transition-colors"
                    >
                        Retry
                    </button>
                </div>
            )}
        </div>
    );
}
