import { Button } from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import type { ErrorComponentProps } from '@tanstack/react-router';
import { ErrorComponent, Link, rootRouteId, useMatch, useRouter } from '@tanstack/react-router';
import { useEffect, useRef } from 'react';
import { isDynamicChunkError, triggerChunkReload } from '~/utils/chunk-reload';

export function DefaultCatchBoundary({ error }: ErrorComponentProps) {
    const router = useRouter();
    const isRoot = useMatch({
        strict: false,
        select: (state) => state.id === rootRouteId,
    });
    const posthog = usePostHog();
    const trackedErrorRef = useRef<unknown>(null);
    const isChunkErr = isDynamicChunkError(error);

    useEffect(() => {
        if (!error || trackedErrorRef.current === error) return;
        trackedErrorRef.current = error;

        let autoReloaded = false;
        if (isChunkErr) {
            autoReloaded = triggerChunkReload();
        }

        const err = error instanceof Error ? error : new Error(String(error));
        if (typeof posthog?.captureException === 'function') {
            posthog.captureException(err, {
                source: 'DefaultCatchBoundary',
                is_root: isRoot,
                pathname: typeof window !== 'undefined' ? window.location.pathname : undefined,
                route_id: router.state?.location?.pathname,
                chunk_error: isChunkErr,
                auto_reloaded: autoReloaded,
            });
        }
    }, [error, isChunkErr, isRoot, posthog, router.state?.location?.pathname]);

    console.error(error);

    if (isChunkErr) {
        return (
            <div className="min-w-0 flex-1 p-8 flex flex-col items-center justify-center gap-4">
                <div className="voxel-trough px-4 py-3 text-xs text-boxel-muted border border-boxel-bevel-hi flex items-center gap-2">
                    <span className="font-mono">Updating application to latest version…</span>
                </div>
                <Button
                    type="button"
                    variant="ghost"
                    colorScheme="neutral"
                    size="sm"
                    className="uppercase font-bold text-xs"
                    onClick={() => {
                        window.location.reload();
                    }}
                >
                    Reload Page
                </Button>
            </div>
        );
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
