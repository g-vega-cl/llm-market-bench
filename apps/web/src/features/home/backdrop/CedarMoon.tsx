/**
 * Pixel moon for the Cedar Ridge sky: a stepped 14×14 disc with three craters,
 * wrapped in a soft halo. Drawn as rects rather than a circle so the silhouette
 * matches the rest of the pixel-art world instead of reading as a UI chip.
 */
export function CedarMoon() {
    return (
        <div className="cr-celestial absolute right-[6%] bottom-[56%] h-16 w-16">
            <div className="cr-moon-halo absolute -inset-6" />
            <svg
                aria-hidden="true"
                focusable="false"
                className="relative h-full w-full"
                viewBox="0 0 14 14"
                fill="none"
            >
                <g fill="var(--color-accent)" opacity="0.6">
                    <rect x="5" y="0" width="4" height="1" />
                    <rect x="3" y="1" width="8" height="1" />
                    <rect x="2" y="2" width="10" height="1" />
                    <rect x="1" y="3" width="12" height="1" />
                    <rect x="1" y="4" width="12" height="1" />
                    <rect x="0" y="5" width="14" height="1" />
                    <rect x="0" y="6" width="14" height="1" />
                    <rect x="0" y="7" width="14" height="1" />
                    <rect x="0" y="8" width="14" height="1" />
                    <rect x="1" y="9" width="12" height="1" />
                    <rect x="1" y="10" width="12" height="1" />
                    <rect x="2" y="11" width="10" height="1" />
                    <rect x="3" y="12" width="8" height="1" />
                    <rect x="5" y="13" width="4" height="1" />
                </g>
                <g fill="var(--color-accent-dark)" opacity="0.5">
                    <rect x="3" y="3" width="2" height="2" />
                    <rect x="8" y="6" width="3" height="2" />
                    <rect x="5" y="9" width="2" height="2" />
                    <rect x="2" y="6" width="1" height="1" />
                </g>
            </svg>
        </div>
    );
}
