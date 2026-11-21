/**
 * Pre-baked distant horizon cloud bands in a crisp Minecraft flat-slab style.
 *
 * Each band's slabs are fixed in tile space (never morphed by screen-space X),
 * painted once into an offscreen seamless tile, and blitted at a continuous
 * wrapped offset so clouds glide glacially with zero snapping or distortion.
 */

export interface CloudSlabRect {
    /** Horizontal start inside [0, tileWidth). */
    x: number;
    /** Vertical offset from the band's flat cloud base (positive = upward). */
    yOffset: number;
    /** Slab width in CSS pixels. */
    w: number;
    /** Slab body height in CSS pixels. */
    h: number;
    /** Optional stepped upper Minecraft crown block inset from the main slab. */
    crown?: {
        insetLeft: number;
        w: number;
        h: number;
    };
}

export interface HorizonCloudBand {
    id: string;
    /** Baseline vertical position as a fraction of canvas height. */
    yRel: number;
    /** Seamless horizontal repeat width in CSS pixels. */
    tileWidth: number;
    /** Vertical height of the offscreen tile in CSS pixels. */
    tileHeight: number;
    /** Drift speed in CSS pixels per second (glacial: <= 4 px/s). */
    speed: number;
    /** Subtle horizontal pointer parallax range in CSS pixels. */
    parallax: number;
    /** Overall layer opacity. */
    alpha: number;
    /** Sunlit top rim color (warm golden-hour cream). */
    topColor: string;
    /** Mid body cloud color (dusk sage mist). */
    bodyColor: string;
    /** Flat shaded underside color (cool twilight slate). */
    baseColor: string;
    slabs: CloudSlabRect[];
}

export const HORIZON_CLOUD_BANDS: readonly HorizonCloudBand[] = [
    {
        id: 'far-horizon',
        yRel: 0.56,
        tileWidth: 1120,
        tileHeight: 68,
        speed: 1.4,
        parallax: 4,
        alpha: 0.52,
        topColor: '#eadbc0',
        bodyColor: '#98ada4',
        baseColor: '#4e6762',
        slabs: [
            { x: 24, yOffset: 8, w: 184, h: 14, crown: { insetLeft: 36, w: 96, h: 9 } },
            { x: 268, yOffset: 18, w: 142, h: 12, crown: { insetLeft: 28, w: 68, h: 8 } },
            { x: 472, yOffset: 6, w: 224, h: 15, crown: { insetLeft: 48, w: 118, h: 10 } },
            { x: 758, yOffset: 16, w: 156, h: 12, crown: { insetLeft: 26, w: 80, h: 8 } },
            { x: 960, yOffset: 10, w: 132, h: 13, crown: { insetLeft: 24, w: 64, h: 7 } },
        ],
    },
    {
        id: 'mid-horizon',
        yRel: 0.69,
        tileWidth: 960,
        tileHeight: 80,
        speed: 2.5,
        parallax: 9,
        alpha: 0.72,
        topColor: '#f5ebd3',
        bodyColor: '#b7c7bf',
        baseColor: '#5c7570',
        slabs: [
            { x: 42, yOffset: 10, w: 210, h: 17, crown: { insetLeft: 44, w: 112, h: 11 } },
            { x: 324, yOffset: 24, w: 158, h: 14, crown: { insetLeft: 28, w: 82, h: 9 } },
            { x: 548, yOffset: 8, w: 236, h: 18, crown: { insetLeft: 56, w: 120, h: 12 } },
            { x: 824, yOffset: 20, w: 114, h: 13, crown: { insetLeft: 20, w: 58, h: 8 } },
        ],
    },
];

/**
 * Computes a continuous seamless horizontal blit offset strictly within
 * (-tileWidth, 0], so tiling from `offset` across the viewport never snaps.
 */
export function computeTileOffset(
    time: number,
    speed: number,
    parallaxPx: number,
    tileWidth: number,
): number {
    if (tileWidth <= 0) return 0;
    const raw = (((time * speed + parallaxPx) % tileWidth) + tileWidth) % tileWidth;
    return raw === 0 ? 0 : -raw;
}

/**
 * Pre-renders one horizontal cloud band into an offscreen tile canvas once per
 * DPR/resize so per-frame rendering is purely cheap `drawImage` blits.
 */
export function bakeCloudBandTile(band: HorizonCloudBand, dpr: number): HTMLCanvasElement | null {
    const off = document.createElement('canvas');
    off.width = Math.round(band.tileWidth * dpr);
    off.height = Math.round(band.tileHeight * dpr);
    const ctx = off.getContext('2d');
    if (!ctx) return null;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const floorY = band.tileHeight - 4;
    const rimH = 3;
    const baseH = 4;

    for (const slab of band.slabs) {
        const bottomY = floorY - slab.yOffset;
        const bodyTopY = bottomY - slab.h;

        // Main flat-bottomed slab body
        ctx.fillStyle = band.bodyColor;
        ctx.fillRect(slab.x, bodyTopY, slab.w, slab.h);

        // Sunlit top bevel along the main slab
        ctx.fillStyle = band.topColor;
        ctx.fillRect(slab.x, bodyTopY, slab.w, rimH);

        // Optional stepped Minecraft upper terrace
        if (slab.crown) {
            const cx = slab.x + slab.crown.insetLeft;
            const cy = bodyTopY - slab.crown.h;
            ctx.fillStyle = band.bodyColor;
            ctx.fillRect(cx, cy, slab.crown.w, slab.crown.h + rimH);
            ctx.fillStyle = band.topColor;
            ctx.fillRect(cx, cy, slab.crown.w, rimH);
        }

        // Cool twilight flat underside shadow
        ctx.fillStyle = band.baseColor;
        ctx.fillRect(slab.x, bottomY - baseH, slab.w, baseH);
    }

    return off;
}
