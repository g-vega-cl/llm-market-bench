import { Button } from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import type { ErrorComponentProps } from '@tanstack/react-router';
import { ErrorComponent, Link, rootRouteId, useMatch, useRouter } from '@tanstack/react-router';
import { type MutableRefObject, useEffect, useRef, useState } from 'react';
import {
    type ChunkReloadClaimStatus,
    claimChunkReloadAttempt,
    isDynamicChunkError,
    reloadAtTarget,
} from '~/utils/chunk-reload';

type ChunkRecoveryPhase = 'checking' | ChunkReloadClaimStatus | 'dispatched';

interface ChunkRecoveryAttempt {
    error: unknown;
    phase: ChunkRecoveryPhase;
}

function reportBoundaryError(params: {
    error: unknown;
    isRoot: boolean;
    routeId: string | undefined;
    isChunkErr: boolean;
    autoReloaded: boolean;
    posthog: ReturnType<typeof usePostHog>;
    trackedErrorRef: MutableRefObject<unknown>;
    loggedErrorRef: MutableRefObject<unknown>;
}) {
    const {
        error,
        isRoot,
        routeId,
        isChunkErr,
        autoReloaded,
        posthog,
        trackedErrorRef,
        loggedErrorRef,
    } = params;
    if (!error) return;

    const err = error instanceof Error ? error : new Error(String(error));
    const isLoaded = (posthog as { __loaded?: boolean } | null | undefined)?.__loaded !== false;
    const hasCaptureException = isLoaded && typeof posthog?.captureException === 'function';

    if (hasCaptureException && trackedErrorRef.current !== error) {
        trackedErrorRef.current = error;
        posthog.captureException(err, {
            source: 'DefaultCatchBoundary',
            is_root: isRoot,
            pathname: typeof window !== 'undefined' ? window.location.pathname : undefined,
            route_id: routeId,
            ...(isChunkErr ? { chunk_error: true, auto_reloaded: autoReloaded } : {}),
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

function claimRecoveryForError(
    recoveryAttemptRef: MutableRefObject<ChunkRecoveryAttempt | null>,
    error: unknown,
    isChunkErr: boolean,
): ChunkRecoveryAttempt | null {
    if (!isChunkErr) {
        recoveryAttemptRef.current = null;
        return null;
    }
    if (recoveryAttemptRef.current?.error !== error) {
        recoveryAttemptRef.current = {
            error,
            phase: claimChunkReloadAttempt(),
        };
    }
    return recoveryAttemptRef.current;
}

function ChunkRecoveryView({
    phase,
    targetHref,
}: {
    phase: ChunkRecoveryPhase;
    targetHref?: string;
}) {
    const statusMessage =
        phase === 'circuit_open'
            ? 'Unable to load the latest application update. Please reload the page.'
            : phase === 'checking'
              ? 'Checking application update…'
              : 'Updating application to latest version…';

    return (
        <div className="min-w-0 flex-1 p-8 flex flex-col items-center justify-center gap-4">
            <div className="voxel-trough px-4 py-3 text-xs font-normal text-voxel-muted flex items-center gap-2">
                <span className="font-mono">{statusMessage}</span>
            </div>
            <Button
                type="button"
                variant="outline"
                colorScheme="neutral"
                size="sm"
                className="uppercase font-bold text-sm"
                onClick={() => {
                    reloadAtTarget(targetHref);
                }}
            >
                Reload Page
            </Button>
        </div>
    );
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
    const recoveryAttemptRef = useRef<ChunkRecoveryAttempt | null>(null);
    const isChunkErr = isDynamicChunkError(error);
    const targetHref = router.state?.location?.href;
    const routePath = router.state?.location?.pathname;
    const [recoveryState, setRecoveryState] = useState<ChunkRecoveryAttempt | null>(null);

    useEffect(() => {
        if (!error) return;
        if (!isChunkErr) {
            recoveryAttemptRef.current = null;
        }

        // Yield one macrotask so parent PostHogProvider's useEffect init() runs on cold root
        // errors before claiming storage, reporting telemetry, and reloading.
        const timerId = window.setTimeout(() => {
            const attempt = claimRecoveryForError(recoveryAttemptRef, error, isChunkErr);
            const autoReloaded = attempt?.phase === 'reloading' || attempt?.phase === 'dispatched';
            if (attempt) {
                setRecoveryState({ error, phase: attempt.phase });
            }

            reportBoundaryError({
                error,
                isRoot,
                routeId: routePath,
                isChunkErr,
                autoReloaded,
                posthog,
                trackedErrorRef,
                loggedErrorRef,
            });

            if (attempt && attempt.phase === 'reloading') {
                attempt.phase = 'dispatched';
                setRecoveryState({ error, phase: 'dispatched' });
                reloadAtTarget(targetHref);
            }
        }, 0);

        return () => window.clearTimeout(timerId);
    }, [error, isChunkErr, isRoot, posthog, targetHref, routePath]);

    if (isChunkErr) {
        const activePhase: ChunkRecoveryPhase =
            recoveryState !== null && recoveryState.error === error
                ? recoveryState.phase
                : 'checking';

        return <ChunkRecoveryView phase={activePhase} targetHref={targetHref} />;
    }

    return (
        <div className="min-w-0 flex-1 p-4 flex flex-col items-center justify-center gap-6">
            <ErrorComponent error={error} />
            <div className="flex gap-2 items-center flex-wrap">
                <Button
                    type="button"
                    variant="solid"
                    colorScheme="neutral"
                    size="sm"
                    className="uppercase font-bold text-sm"
                    onClick={() => {
                        router.invalidate();
                    }}
                >
                    Try Again
                </Button>
                {isRoot ? (
                    <Link
                        to="/"
                        className="px-2.5 py-1 bg-voxel-surface hover:bg-voxel-elevated border border-voxel-bevel-hi rounded-none text-voxel-ink uppercase font-bold text-sm shadow-sm"
                    >
                        Home
                    </Link>
                ) : (
                    <Link
                        to="/"
                        className="px-2.5 py-1 bg-voxel-surface hover:bg-voxel-elevated border border-voxel-bevel-hi rounded-none text-voxel-ink uppercase font-bold text-sm shadow-sm"
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
