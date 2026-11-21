import { Link } from '@tanstack/react-router';
import { GardenBackdrop } from '../backdrop/GardenBackdrop';

/**
 * The homepage: one sentence, one button, over the garden.
 *
 * Nothing else lives here. The old desk — boards, feed, proof strips — is gone;
 * discovery is on /lab and in the nav.
 *
 * Typography stays inside the design budget: one display size for the headline,
 * one body size for everything supporting it.
 */
export function HomeCtaPage() {
    return (
        <section className="relative isolate flex min-h-dvh w-full flex-col overflow-hidden bg-voxel-canvas text-voxel-ink">
            <GardenBackdrop className="pointer-events-none absolute inset-0 -z-10 h-full w-full" />

            <div className="flex flex-1 flex-col items-center justify-center px-6 py-10 text-center">
                <p className="mb-5 text-sm font-normal tracking-[0.28em] uppercase text-voxel-ink">
                    Benchify
                </p>

                <h1 className="max-w-[16ch] text-balance text-[clamp(2rem,5.2vw,3.4rem)] font-normal leading-[1.08] text-voxel-ink">
                    Build your own trading bot.
                </h1>

                <p className="mt-5 max-w-[44ch] text-sm font-normal leading-relaxed text-voxel-ink">
                    Describe it in one sentence and run it on point-in-time news. Live bots decide
                    every 30 minutes on weekdays, 09:30–16:00 ET. Paper cash only — no brokerage
                    account, and no hiding the losers.
                </p>

                <div className="mt-8 flex flex-col items-center gap-4">
                    <Link
                        to="/lab"
                        data-testid="start-building"
                        className="voxel-btn voxel-btn--hero inline-flex w-full max-w-xs min-h-14 items-center justify-center bg-accent px-10 py-4 text-sm font-normal uppercase tracking-[0.16em] text-accent-ink hover:bg-accent-hover"
                    >
                        Start building
                    </Link>
                    <Link
                        to="/leaderboard"
                        className="text-sm font-normal text-voxel-ink underline decoration-voxel-bevel-hi underline-offset-4 hover:text-accent"
                    >
                        See how the published bots are doing
                    </Link>
                </div>
            </div>
        </section>
    );
}
