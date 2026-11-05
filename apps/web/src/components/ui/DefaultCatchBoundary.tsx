import { Button } from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import type { ErrorComponentProps } from '@tanstack/react-router';
import { ErrorComponent, Link, rootRouteId, useMatch, useRouter } from '@tanstack/react-router';
import { useEffect, useRef } from 'react';

export function DefaultCatchBoundary({ error }: ErrorComponentProps) {
    const router = useRouter();
    const isRoot = useMatch({
        strict: false,
        select: (state) => state.id === rootRouteId,
    });
    const posthog = usePostHog();
    const trackedErrorRef = useRef<unknown>(null);

    useEffect(() => {
        if (!error || trackedErrorRef.current === error) return;
        trackedErrorRef.current = error;

        const err = error instanceof Error ? error : new Error(String(error));
        if (typeof posthog?.captureException === 'function') {
            posthog.captureException(err, {
                source: 'DefaultCatchBoundary',
                is_root: isRoot,
                pathname: typeof window !== 'undefined' ? window.location.pathname : undefined,
                route_id: router.state?.location?.pathname,
            });
        }
    }, [error, isRoot, posthog, router.state?.location?.pathname]);

    console.error(error);

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
