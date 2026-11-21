import { Link } from '@tanstack/react-router';
import { GardenBackdrop } from '../backdrop/GardenBackdrop';

/**
 * The homepage: crisp open-sky hero CTA above the twilight voxel garden.
 *
 * Composition separates the hero copy (upper twilight zenith) from the
 * floating voxel island and flat Minecraft slab clouds (lower half) so text
 * reads cleanly without heavy muddy scrims. Spacing is parent-owned (`gap-*`)
 * and typography stays strictly within the 2-combo component budget.
 */
export function HomeCtaPage() {
    return (
        <section className="home-hero-viewport home-twilight-sky relative isolate flex w-full flex-col overflow-hidden text-voxel-ink">
            <GardenBackdrop className="pointer-events-none absolute inset-0 -z-10 h-full w-full" />

            <div
                data-testid="home-hero-content"
                className="flex flex-1 flex-col items-center justify-start gap-6 px-6 pt-12 pb-16 text-center"
            >
                <div className="flex flex-col items-center gap-4">
                    <p className="home-hero-copy text-sm font-bold tracking-[0.28em] uppercase text-accent">
                        Benchify
                    </p>

                    <h1 className="home-hero-heading max-w-[16ch] text-balance text-[clamp(2.1rem,5vw,3.35rem)] font-bold leading-[1.06] text-voxel-ink">
                        Build your own trading bot.
                    </h1>

                    <p className="home-hero-copy max-w-[44ch] text-sm font-normal leading-relaxed text-voxel-ink">
                        Describe a strategy in plain English, test it on point-in-time news, and
                        switch it Live.
                    </p>
                </div>

                <div className="flex w-full flex-col items-center gap-4">
                    <Link
                        to="/lab"
                        data-testid="start-building"
                        className="voxel-btn voxel-btn--hero inline-flex w-full max-w-xs min-h-14 items-center justify-center bg-accent px-10 py-4 text-sm font-bold uppercase tracking-[0.16em] text-accent-ink hover:bg-accent-hover"
                    >
                        Start building
                    </Link>

                    <Link
                        to="/leaderboard"
                        className="home-hero-copy text-sm font-normal text-voxel-ink underline decoration-voxel-bevel-hi underline-offset-4 hover:text-accent"
                    >
                        See how the published bots are doing
                    </Link>

                    <div
                        data-testid="home-trust-strip"
                        className="home-hero-copy flex flex-wrap items-baseline justify-center gap-x-4 gap-y-1 text-sm font-normal text-voxel-ink"
                    >
                        <span className="whitespace-nowrap">Paper cash only</span>
                        <span className="whitespace-nowrap">• Live every 30m ET</span>
                        <span className="whitespace-nowrap">• Every loser stays on the record</span>
                    </div>
                </div>
            </div>
        </section>
    );
}
