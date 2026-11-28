import { Badge, Button } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';

/**
 * Returns the ISO date (YYYY-MM-DD) of a lapsed live week, or null when the bot
 * is live, never was live, or its week has not finished yet. Kept pure so the
 * banner's visibility is testable without a clock.
 */
export function lapsedLiveWeek(
    isLive: boolean,
    liveExpiresAt: string | null | undefined,
    now: number = Date.now(),
): string | null {
    if (isLive || !liveExpiresAt) return null;
    const at = Date.parse(liveExpiresAt);
    if (Number.isNaN(at) || at > now) return null;
    // Slice the ISO string rather than format a locale: server and client must
    // render the same characters or hydration complains.
    return liveExpiresAt.slice(0, 10);
}

export interface LiveWeekBannerProps {
    isOwner: boolean;
    isLive: boolean;
    liveExpiresAt?: string | null;
    onRenew?: () => void;
    busy?: boolean;
}

/**
 * Explains a paused bot whose token-funded week ran out. Without it the bot just
 * looks switched off, and a visitor has no idea the pause was a deadline.
 */
export function LiveWeekBanner({
    isOwner,
    isLive,
    liveExpiresAt,
    onRenew,
    busy = false,
}: LiveWeekBannerProps) {
    const endedOn = lapsedLiveWeek(isLive, liveExpiresAt);
    if (!endedOn) return null;

    return (
        <div
            data-testid="live-week-banner"
            className="voxel-trough bg-voxel-trough flex flex-wrap items-center justify-between gap-3 p-3"
        >
            <span className="flex flex-wrap items-center gap-2 text-xs font-normal text-voxel-ink">
                <Badge variant="soft" colorScheme="warning" size="xs">
                    LIVE WEEK ENDED
                </Badge>
                {isOwner
                    ? `This bot's live week ended on ${endedOn}. Renew to run it again.`
                    : `This bot's live week ended on ${endedOn}. Sign in to keep it running.`}
            </span>

            {isOwner ? (
                <Button size="sm" variant="solid" onClick={onRenew} disabled={busy}>
                    {busy ? 'Renewing…' : 'Renew for 1 token'}
                </Button>
            ) : (
                <Link
                    to="/signup"
                    className="text-xs font-bold text-accent underline decoration-accent underline-offset-4 hover:text-accent-hover"
                >
                    Sign in to claim this bot
                </Link>
            )}
        </div>
    );
}
