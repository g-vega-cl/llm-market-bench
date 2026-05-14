import * as React from 'react';
import { cn } from '../lib/cn';

/**
 * ErrorBoundary primitive.
 *
 * Catches errors in children and renders a fallback UI.
 * Also provides a hook `useErrorBoundary()` for programmatic resets.
 */

interface ErrorBoundaryState {
    hasError: boolean;
    error: Error | null;
}

export interface ErrorBoundaryProps {
    fallback?: React.ReactNode;
    fallbackClassName?: string;
    onReset?: () => void;
    children: React.ReactNode;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
    constructor(props: ErrorBoundaryProps) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        // In production you might log to Sentry here
        console.error('ErrorBoundary caught an error:', error, errorInfo);
    }

    handleReset = () => {
        this.props.onReset?.();
        this.setState({ hasError: false, error: null });
    };

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div
                    className={cn(
                        'flex flex-col items-center justify-center p-8 border border-danger/30 rounded-xl bg-danger-light/50 dark:bg-danger-dark/20',
                        this.props.fallbackClassName,
                    )}
                >
                    <h3 className="text-lg font-bold text-danger mb-2">Something went wrong</h3>
                    <p className="text-sm text-danger/80 mb-4 text-center max-w-md">
                        {this.state.error?.message ?? 'An unexpected error occurred.'}
                    </p>
                    <button
                        type="button"
                        onClick={this.handleReset}
                        className="px-4 py-2 text-sm font-medium text-white bg-danger rounded-lg hover:bg-danger/90 transition-colors"
                    >
                        Try again
                    </button>
                </div>
            );
        }

        return this.props.children;
    }
}
