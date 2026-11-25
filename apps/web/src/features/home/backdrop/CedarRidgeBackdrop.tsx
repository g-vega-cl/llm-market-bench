import type { SceneBackdropProps } from '@llm-market-bench/ui-design-system';
import { cn } from '@llm-market-bench/ui-design-system';
import { CedarMeadowFauna } from './CedarMeadowFauna';
import { CedarMoon } from './CedarMoon';
import { useCedarRidgeDrift } from './useCedarRidgeDrift';

/**
 * Cedar Ridge backdrop: a 2.5D pixel-art landscape behind `/build`.
 *
 * Six stacked planes — stars and a moon, drifting cloud slabs and a gliding
 * bird, a far mountain range, a pine ridge with a lookout tower, a forest
 * floor, and a meadow of ambient fauna. Every plane is plain DOM/CSS/SVG, so
 * the scene costs no canvas or GL context, composites on the GPU, and stays
 * sharp at any DPR.
 *
 * Two layers of motion:
 * - Ambient loops in `app.css` (`.cr-cloud-*`, `.cr-bird`, `.cr-bot`, `.cr-fox`,
 *   `.cr-bob`, `.cr-star`, `.cr-firefly`, `.cr-grass`).
 * - Parallax: `useCedarRidgeDrift` writes `--cr-px` / `--cr-py` on the root and
 *   each plane multiplies them by its own `--cr-depth`.
 *
 * The stage sky itself is painted by `.scene-atmosphere-*` on SceneStage; this
 * layer only contributes silhouettes and the horizon band, so the two never
 * disagree about the time of day. Atmosphere changes exposure here (star
 * opacity, moon height), never the geometry.
 */

/** Implements the shared `SceneBackdropProps` contract (see `SceneStage`). */
export type CedarRidgeBackdropProps = SceneBackdropProps;

/** Scene paint. The surface hues are design tokens; these are the
 *  silhouette and foliage shades that give the ridge its depth. */
const RIDGE = {
    far: '#2b4238',
    farDeep: '#1c2e27',
    pine: '#0c1411',
    towerBody: '#1a2721',
    towerDark: '#070c0a',
    cloudShade: '#dce5de',
    cloudWarm: '#ffddb2',
    cloudWarmDeep: '#cba570',
} as const;

const BEVEL = 'var(--color-voxel-bevel-hi)';
const INK = 'var(--color-voxel-ink)';

export function CedarRidgeBackdrop({ atmosphere, motion, className }: CedarRidgeBackdropProps) {
    const rootRef = useCedarRidgeDrift(motion !== 'running');

    return (
        <div
            ref={rootRef}
            data-testid="cedar-ridge-backdrop"
            data-world="cedar-ridge"
            data-atmosphere={atmosphere}
            data-motion={motion}
            className={cn(
                'cedar-ridge pointer-events-none absolute inset-0 h-full w-full select-none',
                className,
            )}
        >
            {/* Plane 0 · stars and moon */}
            <div className="cr-layer absolute inset-0 [--cr-depth:0.05]">
                <div className="cr-stars absolute inset-x-0 top-0 h-[55%]">
                    <div className="cr-star absolute top-[12%] left-[14%] h-1 w-1 bg-voxel-ink" />
                    <div className="cr-star absolute top-[18%] left-[29%] h-1 w-1 bg-voxel-ink/70 [animation-delay:-1.4s]" />
                    <div className="cr-star absolute top-[9%] left-[47%] h-1 w-1 bg-accent [animation-delay:-2.6s]" />
                    <div className="cr-star absolute top-[22%] left-[63%] h-1 w-1 bg-voxel-ink/80 [animation-delay:-0.9s]" />
                    <div className="cr-star absolute top-[14%] left-[78%] h-1 w-1 bg-voxel-ink [animation-delay:-3.1s]" />
                    <div className="cr-star absolute top-[26%] left-[88%] h-1 w-1 bg-accent/80 [animation-delay:-1.8s]" />
                    <div className="cr-star absolute top-[29%] left-[19%] h-1 w-1 bg-voxel-ink/60 [animation-delay:-2.2s]" />
                </div>
                <CedarMoon />
            </div>

            {/* Plane 1 · cloud bank and a gliding bird */}
            <div className="cr-layer absolute inset-x-0 top-0 h-[46%] [--cr-depth:0.12]">
                <svg
                    aria-hidden="true"
                    focusable="false"
                    className="cr-cloud-1 absolute top-1 left-0 w-[clamp(7.5rem,11vw,11rem)] opacity-40"
                    viewBox="0 0 176 48"
                    fill="none"
                >
                    <rect x="24" y="16" width="112" height="16" fill={INK} />
                    <rect x="48" y="4" width="60" height="14" fill={INK} />
                    <rect x="8" y="24" width="152" height="12" fill={RIDGE.cloudShade} />
                </svg>
                <svg
                    aria-hidden="true"
                    focusable="false"
                    className="cr-cloud-2 absolute top-14 left-0 w-[clamp(9rem,14vw,14rem)] opacity-30"
                    viewBox="0 0 220 56"
                    fill="none"
                >
                    <rect x="32" y="20" width="144" height="18" fill={INK} />
                    <rect x="64" y="6" width="76" height="16" fill={INK} />
                    <rect x="12" y="30" width="188" height="12" fill="var(--color-voxel-muted)" />
                </svg>
                <svg
                    aria-hidden="true"
                    focusable="false"
                    className="cr-cloud-3 absolute top-[26%] left-0 w-[clamp(7rem,9vw,9rem)] opacity-35"
                    viewBox="0 0 144 40"
                    fill="none"
                >
                    <rect x="20" y="12" width="96" height="14" fill={RIDGE.cloudWarm} />
                    <rect x="44" y="2" width="48" height="12" fill={RIDGE.cloudWarm} />
                    <rect x="8" y="20" width="124" height="10" fill={RIDGE.cloudWarmDeep} />
                </svg>
                <svg
                    aria-hidden="true"
                    focusable="false"
                    className="cr-bird absolute top-[21%] left-0 w-10"
                    viewBox="0 0 40 16"
                    fill="none"
                >
                    <path
                        d="M2 8 L8 4 L14 8 M20 12 L25 8 L30 12"
                        stroke="var(--color-voxel-trough)"
                        strokeWidth="2"
                        strokeLinecap="square"
                    />
                </svg>
            </div>

            {/* Plane 2 · far mountain range, warmed at its base by the horizon */}
            <div className="cr-layer absolute inset-x-[-6%] bottom-[22%] h-[40%] [--cr-depth:0.2]">
                <svg
                    aria-hidden="true"
                    focusable="false"
                    className="h-full w-full"
                    preserveAspectRatio="none"
                    viewBox="0 0 1440 320"
                    fill="none"
                >
                    <path
                        d="M0 320 L0 210 L70 200 L120 150 L190 190 L250 165 L300 205 L360 175 L430 118 L500 170 L560 148 L640 196 L700 214 L760 184 L820 118 L882 86 L948 158 L1010 200 L1080 174 L1150 212 L1220 158 L1292 196 L1364 170 L1440 148 L1440 320 Z"
                        fill={RIDGE.far}
                        opacity="0.9"
                    />
                    <path
                        d="M0 320 L0 248 L112 226 L212 252 L322 214 L432 246 L562 224 L692 256 L822 230 L942 252 L1062 218 L1182 250 L1302 228 L1440 246 L1440 320 Z"
                        fill={RIDGE.farDeep}
                        opacity="0.95"
                    />
                </svg>
                <div className="cr-horizon-haze absolute inset-x-0 bottom-0 h-1/3" />
            </div>

            {/* Plane 3 · pine ridge and the lookout tower */}
            <div className="cr-layer absolute inset-x-[-6%] bottom-[14%] h-[34%] [--cr-depth:0.36]">
                <svg
                    aria-hidden="true"
                    focusable="false"
                    className="h-full w-full"
                    preserveAspectRatio="none"
                    viewBox="0 0 1440 260"
                    fill="none"
                >
                    <path
                        d="M0 260 L0 165 L35 165 L55 120 L75 165 L105 165 L125 110 L145 165 L180 165 L205 125 L230 165 L280 165 L305 100 L330 165 L400 165 L425 130 L450 165 L520 165 L540 115 L560 165 L660 165 L780 165 L805 120 L830 165 L910 165 L935 105 L960 165 L1050 165 L1075 130 L1100 165 L1175 165 L1195 95 L1215 165 L1270 165 L1295 125 L1320 165 L1385 165 L1405 115 L1425 165 L1440 165 L1440 260 Z"
                        fill={RIDGE.pine}
                    />
                    <g transform="translate(1152, 62)">
                        <circle cx="20" cy="21" r="16" fill="var(--color-accent)" opacity="0.14" />
                        <rect x="8" y="28" width="4" height="40" fill={RIDGE.towerDark} />
                        <rect x="28" y="28" width="4" height="40" fill={RIDGE.towerDark} />
                        <rect x="10" y="42" width="20" height="3" fill={RIDGE.towerDark} />
                        <rect x="18" y="34" width="4" height="2" fill={RIDGE.towerDark} />
                        <rect x="18" y="49" width="4" height="2" fill={RIDGE.towerDark} />
                        <rect x="18" y="56" width="4" height="2" fill={RIDGE.towerDark} />
                        <rect x="4" y="14" width="32" height="16" fill={RIDGE.towerBody} />
                        <rect x="2" y="30" width="36" height="2" fill={RIDGE.towerDark} />
                        <rect x="4" y="32" width="2" height="4" fill={RIDGE.towerDark} />
                        <rect x="34" y="32" width="2" height="4" fill={RIDGE.towerDark} />
                        <rect x="0" y="8" width="40" height="6" fill={RIDGE.towerDark} />
                        <rect x="12" y="18" width="16" height="6" fill="var(--color-accent)" />
                    </g>
                </svg>
            </div>

            {/* Plane 4 · forest floor, fading into the near foreground */}
            <div className="cr-layer absolute inset-x-[-6%] bottom-0 h-[14%] [--cr-depth:0.56]">
                <div className="absolute inset-x-0 top-0 h-3 border-t border-voxel-bevel-hi/50 bg-voxel-surface" />
                <div className="cr-ground absolute inset-x-0 top-3 bottom-0 bg-voxel-trough" />
                <div className="cr-near-fade absolute inset-x-0 top-3 bottom-0" />
                <svg
                    aria-hidden="true"
                    focusable="false"
                    className="cr-grass absolute -top-3 left-[8%] w-3"
                    viewBox="0 0 12 16"
                    fill="none"
                >
                    <rect x="1" y="6" width="2" height="10" fill={BEVEL} opacity="0.7" />
                    <rect x="5" y="2" width="2" height="14" fill={BEVEL} opacity="0.55" />
                    <rect x="9" y="8" width="2" height="8" fill={BEVEL} opacity="0.7" />
                </svg>
                <svg
                    aria-hidden="true"
                    focusable="false"
                    className="cr-grass absolute -top-4 left-[24%] w-3"
                    viewBox="0 0 12 16"
                    fill="none"
                >
                    <rect x="1" y="4" width="2" height="12" fill={BEVEL} opacity="0.55" />
                    <rect x="5" y="7" width="2" height="9" fill={BEVEL} opacity="0.7" />
                    <rect x="9" y="3" width="2" height="13" fill={BEVEL} opacity="0.45" />
                </svg>
                <svg
                    aria-hidden="true"
                    focusable="false"
                    className="cr-grass absolute -top-4 left-[71%] w-3 [animation-delay:-1.1s]"
                    viewBox="0 0 12 16"
                    fill="none"
                >
                    <rect x="1" y="7" width="2" height="9" fill={BEVEL} opacity="0.6" />
                    <rect x="5" y="3" width="2" height="13" fill={BEVEL} opacity="0.7" />
                    <rect x="9" y="6" width="2" height="10" fill={BEVEL} opacity="0.5" />
                </svg>
                <svg
                    aria-hidden="true"
                    focusable="false"
                    className="cr-grass absolute -top-3 left-[86%] w-3 [animation-delay:-0.6s]"
                    viewBox="0 0 12 16"
                    fill="none"
                >
                    <rect x="1" y="5" width="2" height="11" fill={BEVEL} opacity="0.7" />
                    <rect x="5" y="8" width="2" height="8" fill={BEVEL} opacity="0.5" />
                    <rect x="9" y="4" width="2" height="12" fill={BEVEL} opacity="0.65" />
                </svg>
            </div>

            {/* Plane 5 · meadow fauna */}
            <div className="cr-layer absolute inset-x-0 bottom-[11%] h-24 [--cr-depth:0.74]">
                <CedarMeadowFauna />
            </div>
        </div>
    );
}
