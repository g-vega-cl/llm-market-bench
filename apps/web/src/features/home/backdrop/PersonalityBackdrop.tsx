import type { SceneBackdropProps } from '@llm-market-bench/ui-design-system';
import { cn } from '@llm-market-bench/ui-design-system';
import type { ReactNode } from 'react';
import { useCedarRidgeDrift } from './useCedarRidgeDrift';

/**
 * Personality-specific world: a canvas-free, horizon-first diorama behind the
 * investing-style diagnostic. One abstract silhouette per act — ridge · signal
 * · fork · gate — one lit at a time, all four lit on result. The diagnostic
 * copy stays dominant; atmosphere changes exposure only (day/night cycle),
 * never the scene composition. The Sky HUD remains the sole sky owner, so act
 * shifts never fight the atmosphere switcher.
 */
export type PersonalitySceneAct = 0 | 1 | 2 | 3 | 'result';
export interface PersonalityBackdropProps extends SceneBackdropProps {
    /** Which act's landmark is lit; all four are lit on `result`. Defaults to Act 1. */
    act?: PersonalitySceneAct;
}

const ACT_AXES: Record<PersonalitySceneAct, 'horizon' | 'signal' | 'crowd' | 'cadence' | null> = {
    0: 'horizon',
    1: 'signal',
    2: 'crowd',
    3: 'cadence',
    result: null,
};

/** One landmark per act. Depth and focus live in `personality-backdrop.css`. */
const LANDMARKS: Array<{
    axis: 'horizon' | 'signal' | 'crowd' | 'cadence';
    shape: ReactNode;
}> = [
    {
        axis: 'horizon',
        shape: (
            <svg
                aria-hidden="true"
                focusable="false"
                className="pb-shape absolute inset-x-[-6%] bottom-0 h-[40%] w-full"
                preserveAspectRatio="none"
                viewBox="0 0 1440 320"
                fill="none"
            >
                <path
                    d="M0 320 L0 210 L70 200 L120 150 L190 190 L250 165 L300 205 L360 175 L430 118 L500 170 L560 148 L640 196 L700 214 L760 184 L820 118 L882 86 L948 158 L1010 200 L1080 174 L1150 212 L1220 158 L1292 196 L1364 170 L1440 148 L1440 320 Z"
                    fill="var(--color-voxel-ink)"
                    opacity="0.9"
                />
                <path
                    d="M0 320 L0 248 L112 226 L212 252 L322 214 L432 246 L562 224 L692 256 L822 230 L942 252 L1062 218 L1182 250 L1302 228 L1440 246 L1440 320 Z"
                    fill="var(--color-voxel-muted)"
                    opacity="0.95"
                />
            </svg>
        ),
    },
    {
        axis: 'signal',
        shape: (
            <svg
                aria-hidden="true"
                focusable="false"
                className="pb-shape absolute inset-x-[-6%] bottom-[14%] h-[34%] w-full"
                preserveAspectRatio="none"
                viewBox="0 0 1440 260"
                fill="none"
            >
                <path
                    d="M0 260 L0 165 L35 165 L55 120 L75 165 L105 165 L125 110 L145 165 L180 165 L205 125 L230 165 L280 165 L305 100 L330 165 L400 165 L425 130 L450 165 L520 165 L540 115 L560 165 L660 165 L780 165 L805 120 L830 165 L910 165 L935 105 L960 165 L1050 165 L1075 130 L1100 165 L1175 165 L1195 95 L1215 165 L1270 165 L1295 125 L1320 165 L1385 165 L1405 115 L1425 165 L1440 165 L1440 260 Z"
                    fill="var(--color-voxel-ink)"
                    opacity="0.85"
                />
                <rect
                    x="720"
                    y="40"
                    width="4"
                    height="100"
                    fill="var(--color-accent)"
                    opacity="0.6"
                />
                <circle cx="722" cy="34" r="14" fill="var(--color-accent)" opacity="0.5" />
            </svg>
        ),
    },
    {
        axis: 'crowd',
        shape: (
            <svg
                aria-hidden="true"
                focusable="false"
                className="pb-shape absolute inset-x-[-6%] bottom-[10%] h-[30%] w-full"
                preserveAspectRatio="none"
                viewBox="0 0 1440 220"
                fill="none"
            >
                <path
                    d="M0 220 L0 150 L140 150 L140 110 L200 110 L200 150 L280 150 L280 80 L360 80 L360 150 L460 150 L460 120 L540 120 L540 150 L640 150 L640 90 L720 90 L720 150 L820 150 L820 100 L900 100 L900 150 L1000 150 L1000 70 L1080 70 L1080 150 L1180 150 L1180 90 L1260 90 L1260 150 L1360 150 L1360 130 L1440 130 L1440 220 Z"
                    fill="var(--color-voxel-muted)"
                    opacity="0.85"
                />
                <path
                    d="M140 150 L200 110 L200 150 M360 150 L460 120 L460 150 M640 150 L720 90 L720 150 M900 150 L1000 70 L1000 150 M1180 150 L1260 90 L1260 150"
                    stroke="var(--color-accent)"
                    strokeWidth="2"
                    strokeLinecap="square"
                    opacity="0.45"
                />
            </svg>
        ),
    },
    {
        axis: 'cadence',
        shape: (
            <svg
                aria-hidden="true"
                focusable="false"
                className="pb-shape absolute inset-x-[-6%] bottom-[6%] h-[26%] w-full"
                preserveAspectRatio="none"
                viewBox="0 0 1440 180"
                fill="none"
            >
                <rect
                    x="0"
                    y="110"
                    width="1440"
                    height="70"
                    fill="var(--color-voxel-trough)"
                    opacity="0.8"
                />
                <path
                    d="M0 110 L220 110 L220 50 L440 50 L440 110 L660 110 L660 30 L880 30 L880 110 L1100 110 L1100 60 L1320 60 L1320 110 L1440 110 Z"
                    fill="var(--color-voxel-ink)"
                    opacity="0.85"
                />
            </svg>
        ),
    },
];

export function PersonalityBackdrop({
    atmosphere,
    motion,
    act = 0,
    className,
}: PersonalityBackdropProps) {
    const rootRef = useCedarRidgeDrift(motion !== 'running');
    const activeAxis = ACT_AXES[act];
    const isLit = (axis: 'horizon' | 'signal' | 'crowd' | 'cadence') =>
        activeAxis === null || activeAxis === axis;

    return (
        <div
            ref={rootRef}
            data-testid="personality-backdrop"
            data-world="personality-compass"
            data-atmosphere={atmosphere}
            data-motion={motion}
            data-act={String(act)}
            className={cn(
                'personality-compass pointer-events-none absolute inset-0 h-full w-full select-none',
                className,
            )}
        >
            {/* Plane 0 · celestial (stars) */}
            <div className="pb-layer pb-celestial absolute inset-0">
                <div className="pb-stars absolute inset-x-0 top-0 h-[55%]">
                    <div className="pb-star absolute top-[12%] left-[14%] h-1 w-1 bg-voxel-ink" />
                    <div className="pb-star absolute top-[18%] left-[29%] h-1 w-1 bg-voxel-ink/70" />
                    <div className="pb-star absolute top-[9%] left-[47%] h-1 w-1 bg-accent" />
                    <div className="pb-star absolute top-[22%] left-[63%] h-1 w-1 bg-voxel-ink/80" />
                    <div className="pb-star absolute top-[14%] left-[78%] h-1 w-1 bg-voxel-ink" />
                    <div className="pb-star absolute top-[26%] left-[88%] h-1 w-1 bg-accent/80" />
                    <div className="pb-star absolute top-[29%] left-[19%] h-1 w-1 bg-voxel-ink/60" />
                </div>
            </div>

            {/* Act landmarks · horizon-first, floor anchored to stage bottom */}
            {LANDMARKS.map(({ axis, shape }) => (
                <div
                    key={axis}
                    className="pb-layer pb-landmark pb-anchor-bottom absolute inset-x-[-6%] bottom-[4%] h-[44%]"
                    data-axis={axis}
                    data-active={isLit(axis)}
                >
                    {shape}
                </div>
            ))}
        </div>
    );
}
