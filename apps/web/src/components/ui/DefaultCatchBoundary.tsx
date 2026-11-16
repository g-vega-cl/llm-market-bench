import { Button } from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import type { ErrorComponentProps } from '@tanstack/react-router';
import { ErrorComponent, Link, rootRouteId, useMatch, useRouter } from '@tanstack/react-router';
import { type MutableRefObject, useEffect, useRef } from 'react';

function reportBoundaryError(params: {
    error: unknown;
    isRoot: boolean;
    routeId: string | undefined;
    posthog: ReturnType<typeof usePostHog>;
    trackedErrorRef: MutableRefObject<unknown>;
    loggedErrorRef: MutableRefObject<unknown>;
}) {
    const { error, isRoot, routeId, posthog, trackedErrorRef, loggedErrorRef } = params;
    if (!error) return;

    const err = error instanceof Error ? error : new Error(String(error));
    const hasCaptureException = typeof posthog?.captureException === 'function';

    if (hasCaptureException && trackedErrorRef.current !== error) {
        trackedErrorRef.current = error;
        posthog.captureException(err, {
            source: 'DefaultCatchBoundary',
            is_root: isRoot,
            pathname: typeof window !== 'undefined' ? window.location.pathname : undefined,
            route_id: routeId,
        });
    }

    if (loggedErrorRef.current !== error) {
        loggedErrorRef.current = error;
        // Use console.warn when PostHog already captured the exception explicitly so
        // wrapConsoleError (capture_console_errors: true) does not emit a duplicate $exception.
        if (hasCaptureException) {
            console.warn('[DefaultCatchBoundary]', error);
        } else {
            console.error(error);
        }
    }
}

export function DefaultCatchBoundary({ error }: ErrorComponentProps) {
    const router = useRouter();
    const isRoot = useMatch({
        strict: false,
        select: (state) => state.id === rootRouteId,
    });
    const posthog = usePostHog();
    const trackedErrorRef = useRef<unknown>(null);
    const loggedErrorRef = useRef<unknown>(null);

    useEffect(() => {
        reportBoundaryError({
            error,
            isRoot,
            routeId: router.state?.location?.pathname,
            posthog,
            trackedErrorRef,
            loggedErrorRef,
        });
    }, [error, isRoot, posthog, router.state?.location?.pathname]);

    return (
        <div className="min-w-0 flex-1 p-4 flex flex-col items-center justify-center gap-6">
            <ErrorComponent error={error} />
            <div className="flex gap-2 items-center flex-wrap">
                <Button
                    type="button"
                    variant="solid"
                    colorScheme="neutral"
                    size="sm"
                    className="uppercase font-bold text-xs"
                    onClick={() => {
                        router.invalidate();
                    }}
                >
                    Try Again
                </Button>
                {isRoot ? (
                    <Link
                        to="/"
                        className="px-2.5 py-1 bg-zinc-700 rounded-none text-white uppercase font-bold text-xs shadow-sm"
                    >
                        Home
                    </Link>
                ) : (
                    <Link
                        to="/"
                        className="px-2.5 py-1 bg-zinc-700 rounded-none text-white uppercase font-bold text-xs shadow-sm"
                        onClick={(e) => {
                            e.preventDefault();
                            window.history.back();
                        }}
                    >
                        Go Back
                    </Link>
                )}
            </div>
        </div>
    );
}
