import { Button } from '@llm-market-bench/ui-design-system';

interface RunPaginatorProps {
    /** Zero-based index into the newest-first run list. */
    index: number;
    total: number;
    /** Eastern-time stamp of the run on screen; announced with the page number. */
    label?: string;
    /** Step back in time (higher index). */
    onOlder: () => void;
    /** Step forward toward the newest run (lower index). */
    onNewer: () => void;
}

/**
 * Pages the persisted live runs one at a time. The list is newest-first, so the
 * controls are labelled by time rather than "prev/next": "Newer" always moves
 * toward today.
 *
 * The boundary control stays focusable (`aria-disabled` plus a guarded handler)
 * instead of using `disabled`: disabling the button the user just activated
 * drops keyboard focus to `<body>`, forcing a Tab across the whole page to
 * reach the other direction.
 */
export function RunPaginator({ index, total, label, onOlder, onNewer }: RunPaginatorProps) {
    if (total <= 1) return null;

    // The component owns its own bound: a caller cannot page past the list.
    const safeIndex = Math.min(Math.max(index, 0), total - 1);
    const isNewest = safeIndex === 0;
    const isOldest = safeIndex === total - 1;

    return (
        <nav aria-label="Live run pages" className="w-full">
            <div className="flex flex-wrap items-center justify-between gap-2 w-full">
                <Button
                    size="sm"
                    variant="outline"
                    colorScheme="neutral"
                    aria-disabled={isOldest}
                    onClick={() => {
                        if (!isOldest) onOlder();
                    }}
                >
                    <span aria-hidden="true">←</span> Older
                </Button>
                <span role="status" className="text-xs font-normal text-voxel-muted">
                    {safeIndex + 1} of {total}
                    {label ? <span className="sr-only"> · {label}</span> : null}
                </span>
                <Button
                    size="sm"
                    variant="outline"
                    colorScheme="neutral"
                    aria-disabled={isNewest}
                    onClick={() => {
                        if (!isNewest) onNewer();
                    }}
                >
                    Newer <span aria-hidden="true">→</span>
                </Button>
            </div>
        </nav>
    );
}
