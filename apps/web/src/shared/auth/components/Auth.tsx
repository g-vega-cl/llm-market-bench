import { Button, Card } from '@llm-market-bench/ui-design-system';
import { useEffect, useRef, useState } from 'react';
import { FINANCIAL_DISCLAIMER_SHORT_TEXT } from '~/features/legal/FinancialDisclaimer';
import { getAuthBrowserClient } from '~/lib/auth-client';
import { clearPendingGoogleAuth, markPendingGoogleAuth } from '../pending-auth';
import { buildOAuthCallbackUrl, resolveCurrentReturnPath } from '../redirect';

const AUTH_ERROR_MESSAGES: Record<string, string> = {
    access_denied: 'Google sign-in was cancelled. Try again when you are ready.',
    exchange_failed: 'We could not finish signing you in with Google. Please try again.',
    oauth_failed: 'Google sign-in could not be completed. Please try again.',
};

export type AuthPhase =
    | { kind: 'idle' }
    | { kind: 'redirecting' }
    | { kind: 'error'; message: string };

export function resolveAuthErrorMessage(code: unknown): string | null {
    if (typeof code !== 'string' || !code) return null;
    return AUTH_ERROR_MESSAGES[code] ?? AUTH_ERROR_MESSAGES.oauth_failed;
}

function initialPhaseFromErrorCode(errorCode?: string): AuthPhase {
    const message = resolveAuthErrorMessage(errorCode);
    return message ? { kind: 'error', message } : { kind: 'idle' };
}

function isRecipesPath(path: string): boolean {
    const pathname = path.split(/[?#]/)[0]?.replace(/\/+$/, '') || '/';
    return pathname === '/recipes' || pathname.startsWith('/recipes/');
}

function GoogleIcon() {
    return (
        <svg className="w-5 h-5 shrink-0" aria-hidden="true" viewBox="0 0 24 24">
            <path
                fill="currentColor"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
                fill="currentColor"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
                fill="currentColor"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
            />
            <path
                fill="currentColor"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.47 2.18 7.07 4.56l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
        </svg>
    );
}

export function Auth({
    actionText = 'Sign in to Benchify',
    redirectPath,
    errorCode,
}: {
    actionText?: string;
    redirectPath?: string;
    errorCode?: string;
}) {
    const [browserReturnPath, setBrowserReturnPath] = useState('/');
    const [phase, setPhase] = useState<AuthPhase>(() => initialPhaseFromErrorCode(errorCode));
    const prevErrorCodeRef = useRef(errorCode);

    useEffect(() => {
        setBrowserReturnPath(resolveCurrentReturnPath());
        clearPendingGoogleAuth();
    }, []);

    useEffect(() => {
        if (prevErrorCodeRef.current === errorCode) return;
        prevErrorCodeRef.current = errorCode;
        setPhase(initialPhaseFromErrorCode(errorCode));
    }, [errorCode]);

    useEffect(() => {
        if (typeof window === 'undefined') return;
        const handlePageShow = (event: PageTransitionEvent) => {
            if (event.persisted) {
                clearPendingGoogleAuth();
                setPhase({ kind: 'idle' });
            }
        };
        window.addEventListener('pageshow', handlePageShow);
        return () => window.removeEventListener('pageshow', handlePageShow);
    }, []);

    const returnPath = redirectPath ?? browserReturnPath;
    const isRecipesGate = isRecipesPath(returnPath);
    const isRedirecting = phase.kind === 'redirecting';

    const handleGoogleLogin = async () => {
        if (phase.kind === 'redirecting') return;
        setPhase({ kind: 'redirecting' });
        try {
            markPendingGoogleAuth();
            const authClient = getAuthBrowserClient();
            const result = await authClient.auth.signInWithOAuth({
                provider: 'google',
                options: {
                    redirectTo: buildOAuthCallbackUrl(window.location.origin, returnPath),
                },
            });
            if (result?.error) {
                throw result.error;
            }
        } catch (error) {
            clearPendingGoogleAuth();
            setPhase({
                kind: 'error',
                message:
                    error instanceof Error && error.message
                        ? error.message
                        : 'Could not start Google sign-in. Please try again.',
            });
        }
    };

    return (
        <div className="flex-1 flex items-center justify-center px-6 py-8">
            <Card variant="default" padding="lg" className="w-full max-w-md flex flex-col gap-6">
                <div className="flex flex-col gap-2">
                    <h1 className="text-sm font-bold font-display uppercase tracking-wider text-voxel-ink">
                        {actionText}
                    </h1>
                    <p className="text-xs font-normal leading-relaxed text-voxel-muted">
                        {isRecipesGate
                            ? 'Sign in with Google to run backtests and live paper sessions in Strategy Recipe Studio.'
                            : 'Sign in with Google to run backtests, save trading bots, and track live paper results.'}
                    </p>
                </div>

                {phase.kind === 'error' && (
                    <div
                        role="alert"
                        className="voxel-trough p-4 border-l-2 border-l-danger flex flex-col gap-1"
                    >
                        <span className="text-sm font-bold text-danger">Sign-in failed</span>
                        <span className="text-xs font-normal leading-relaxed text-voxel-muted">
                            {phase.message}
                        </span>
                    </div>
                )}

                <Button
                    type="button"
                    variant="solid"
                    colorScheme="neutral"
                    isLoading={isRedirecting}
                    className="w-full text-sm font-bold ring-1 ring-accent/40"
                    leftIcon={<GoogleIcon />}
                    onClick={handleGoogleLogin}
                >
                    {isRedirecting ? 'Redirecting to Google...' : 'Continue with Google'}
                </Button>

                {isRecipesGate && (
                    <div className="voxel-trough p-4 flex flex-col gap-2 text-xs font-normal text-voxel-muted">
                        <span className="text-sm font-bold text-voxel-ink">
                            Strategy Recipe Studio — Free Beta Access
                        </span>
                        <span className="leading-relaxed">
                            Sign in with Google to get 2 free 2-week backtests/day (strata-auto-go)
                            and 3 live paper turns/day (auto-go).
                        </span>
                    </div>
                )}

                <div className="voxel-trough p-4 flex flex-col gap-2 text-xs font-normal text-voxel-muted">
                    <span className="text-sm font-bold text-voxel-ink">
                        Research &amp; paper trading only
                    </span>
                    <span className="leading-relaxed">{FINANCIAL_DISCLAIMER_SHORT_TEXT}</span>
                </div>

                <div className="flex flex-col gap-2 text-xs font-normal leading-relaxed text-voxel-muted text-center">
                    <p>
                        By continuing you agree to the{' '}
                        <a href="/terms" className="text-accent hover:underline">
                            Terms
                        </a>{' '}
                        and acknowledge the{' '}
                        <a href="/privacy" className="text-accent hover:underline">
                            Privacy Policy
                        </a>{' '}
                        and{' '}
                        <a href="/disclaimer" className="text-accent hover:underline">
                            Financial Disclaimer
                        </a>
                        .
                    </p>
                    <a href="/recipes-demo" className="text-accent hover:underline">
                        Or inspect a public sample backtest first →
                    </a>
                </div>
            </Card>
        </div>
    );
}
