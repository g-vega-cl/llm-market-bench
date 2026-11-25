/** Scene paint for the meadow creatures — amber and pine shades, not UI tokens. */
const FUR = {
    chassis: '#39493f',
    leg: '#1b2620',
    body: '#c97b3a',
    tail: '#d49a58',
    ear: '#8f6d48',
} as const;

const BEVEL = 'var(--color-voxel-bevel-hi)';
const TROUGH = 'var(--color-voxel-trough)';

/**
 * Meadow fauna for the Cedar Ridge backdrop: a lantern-bot patrolling left, a
 * fox patrolling right, and four drifting fireflies. The patrol and bob loops
 * live in `app.css` (`.cr-bot`, `.cr-fox`, `.cr-bob`, `.cr-firefly`).
 */
export function CedarMeadowFauna() {
    return (
        <>
            <div className="cr-bot absolute bottom-0 left-0">
                <div className="cr-bot-glow absolute -inset-4" />
                <svg
                    aria-hidden="true"
                    focusable="false"
                    className="cr-bob relative w-11"
                    viewBox="0 0 36 40"
                    fill="none"
                >
                    <rect x="16" y="0" width="4" height="6" fill={BEVEL} />
                    <rect x="16" y="0" width="4" height="3" fill="var(--color-accent)" />
                    <rect x="8" y="6" width="20" height="16" fill={FUR.chassis} />
                    <rect x="8" y="6" width="20" height="2" fill={BEVEL} />
                    <rect x="12" y="11" width="12" height="5" fill={TROUGH} />
                    <rect x="14" y="12" width="4" height="3" fill="var(--color-accent)" />
                    <rect x="20" y="12" width="3" height="3" fill="var(--color-accent)" />
                    <rect x="11" y="22" width="5" height="8" fill={FUR.leg} />
                    <rect x="20" y="22" width="5" height="8" fill={FUR.leg} />
                </svg>
            </div>

            <div className="cr-fox absolute bottom-0 left-0">
                <div className="cr-fox-glow absolute -inset-3" />
                <svg
                    aria-hidden="true"
                    focusable="false"
                    className="cr-bob relative w-12"
                    viewBox="0 0 40 32"
                    fill="none"
                >
                    <rect x="2" y="12" width="10" height="6" fill={FUR.tail} />
                    <rect x="0" y="12" width="4" height="4" fill="var(--color-voxel-ink)" />
                    <rect x="10" y="12" width="16" height="9" fill={FUR.body} />
                    <rect x="24" y="6" width="10" height="9" fill={FUR.body} />
                    <rect x="24" y="2" width="3" height="4" fill={FUR.ear} />
                    <rect x="30" y="2" width="3" height="4" fill={FUR.ear} />
                    <rect x="31" y="10" width="5" height="3" fill={TROUGH} />
                    <rect x="12" y="21" width="3" height="6" fill={TROUGH} />
                    <rect x="22" y="21" width="3" height="6" fill={TROUGH} />
                </svg>
            </div>

            <div className="cr-firefly absolute bottom-6 left-[18%] h-1.5 w-1.5 bg-accent [animation-delay:-0.5s]" />
            <div className="cr-firefly cr-firefly--pale absolute bottom-10 left-[32%] h-1 w-1 bg-accent/70 [animation-delay:-2.4s]" />
            <div className="cr-firefly absolute bottom-4 left-[64%] h-1.5 w-1.5 bg-accent [animation-delay:-4.1s]" />
            <div className="cr-firefly cr-firefly--pale absolute bottom-12 left-[79%] h-1 w-1 bg-accent/70 [animation-delay:-1.7s]" />
        </>
    );
}
