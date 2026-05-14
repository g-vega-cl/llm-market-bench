import { Button } from '@llm-market-bench/ui-design-system';
import type { ErrorComponentProps } from '@tanstack/react-router';
import { ErrorComponent, Link, rootRouteId, useMatch, useRouter } from '@tanstack/react-router';

export function DefaultCatchBoundary({ error }: ErrorComponentProps) {
    const router = useRouter();
    const isRoot = useMatch({
        strict: false,
        select: (state) => state.id === rootRouteId,
    });

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
                    className="uppercase font-extrabold"
                    onClick={() => {
                        router.invalidate();
                    }}
                >
                    Try Again
                </Button>
                {isRoot ? (
                    <Link
                        to="/"
                        className={`px-2 py-1 bg-gray-600 dark:bg-gray-700 rounded-sm text-white uppercase font-extrabold`}
                    >
                        Home
                    </Link>
                ) : (
                    <Link
                        to="/"
                        className={`px-2 py-1 bg-gray-600 dark:bg-gray-700 rounded-sm text-white uppercase font-extrabold`}
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
