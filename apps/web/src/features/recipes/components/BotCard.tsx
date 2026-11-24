import { Badge, Button, Card } from '@llm-market-bench/ui-design-system';
import { Link, useRouter } from '@tanstack/react-router';
import type { MouseEvent as ReactMouseEvent } from 'react';

import type { RecipeSummaryItem } from '../types';
import { isTurboActive } from '../utils/market-hours';

/** Which link on this card started the in-flight navigation, if any. */
export type BotCardPendingDestination = 'workspace' | 'live' | null;

export interface BotCardProps {
    item: RecipeSummaryItem;
    /** Destination of the in-flight navigation started from this card. */
    pendingDestination: BotCardPendingDestination;
    /** A mutation (live toggle, removal) is in flight and must not be navigated away from. */
    isLocked: boolean;
    isTogglingLive: boolean;
    isRemoving: boolean;
    onToggleLive: (item: RecipeSummaryItem) => void;
    onRemove: (item: RecipeSummaryItem) => void;
}

const PENDING_COPY: Record<Exclude<BotCardPendingDestination, null>, string> = {
    workspace: 'Opening bot…',
    live: 'Opening live view…',
};

/**
 * Minimal per-bot card on the /recipes dashboard.
 *
 * The bot name is the navigation affordance (→ /build?recipeId=<id>) and
 * carries an always-visible chevron so the action is legible on touch, where
 * there is no hover state. While a navigation or one of the card's own
 * mutations is in flight every control goes inert — links without an href,
 * both actions disabled — and a navigation adds a dimmed name plus an in-flow
 * status line naming the destination it is opening.
 *
 * A second click in the same frame lands before React commits the pending
 * state, so the handler also reads the router synchronously: `navigate()` sets
 * `store.status = 'pending'` inside the first click's call stack, so the
 * duplicate click sees it and is prevented. No latch of our own to strand.
 */
export function BotCard({
    item,
    pendingDestination,
    isLocked,
    isTogglingLive,
    isRemoving,
    onToggleLive,
    onRemove,
}: BotCardProps) {
    const router = useRouter();
    const turbo = item.is_live && isTurboActive(item.turbo_expires_at);
    const isOpening = pendingDestination !== null;
    const isActionDisabled = isLocked || isOpening;

    const guardDuplicateClick = (event: ReactMouseEvent<HTMLAnchorElement>) => {
        // A modified or non-primary click opens elsewhere / in a new tab and
        // never starts an in-app navigation, so it must not be swallowed.
        if (
            isActionDisabled ||
            event.defaultPrevented ||
            event.button !== 0 ||
            event.metaKey ||
            event.ctrlKey ||
            event.shiftKey ||
            event.altKey
        ) {
            if (isActionDisabled) event.preventDefault();
            return;
        }
        // `navigate()` flips the router status to pending inside the first
        // click's call stack, so a same-frame duplicate click is caught here.
        if (router.state.status === 'pending') event.preventDefault();
    };

    const linkState = isOpening
        ? 'text-voxel-muted'
        : 'text-voxel-ink hover:text-accent hover:underline focus-visible:underline';

    return (
        <Card
            padding="md"
            data-testid={`bot-card-${item.id}`}
            className="flex flex-col justify-between gap-4 min-w-0"
        >
            <div className="flex items-start justify-between gap-2 min-w-0">
                <Link
                    to="/recipes/$recipeId"
                    params={{ recipeId: item.id }}
                    disabled={isActionDisabled}
                    aria-disabled={isActionDisabled || undefined}
                    aria-label={`${item.name} (open recipe workspace)`}
                    data-testid={`bot-open-${item.id}`}
                    onClick={guardDuplicateClick}
                    className={`group/open inline-flex min-w-0 items-center gap-1.5 text-sm font-bold underline-offset-4 ${linkState}`}
                >
                    <span className="min-w-0 break-words">{item.name}</span>
                    {isOpening ? (
                        <span
                            aria-hidden="true"
                            data-testid={`bot-open-pending-${item.id}`}
                            className="inline-flex w-4 h-4 shrink-0 items-center justify-center"
                        >
                            <span className="inline-block w-2 h-2 rounded-none bg-current animate-pulse motion-reduce:animate-none" />
                        </span>
                    ) : (
                        <ChevronRightIcon testId={`bot-open-chevron-${item.id}`} />
                    )}
                </Link>
                {item.is_live && (
                    <Link
                        to="/recipes/live/$recipeId"
                        params={{ recipeId: item.id }}
                        disabled={isActionDisabled}
                        aria-disabled={isActionDisabled || undefined}
                        data-testid={`bot-live-${item.id}`}
                        onClick={guardDuplicateClick}
                        className="shrink-0"
                    >
                        <Badge
                            variant="soft"
                            colorScheme={turbo ? 'accent' : 'success'}
                            size="xs"
                            suppressHydrationWarning
                        >
                            {turbo ? 'TURBO 5m' : 'LIVE 30m'}
                        </Badge>
                    </Link>
                )}
            </div>

            {isOpening && (
                <span role="status" className="text-xs font-normal text-voxel-muted">
                    {PENDING_COPY[pendingDestination]}
                </span>
            )}

            <div
                aria-busy={isOpening || isTogglingLive || isRemoving || undefined}
                data-testid={`bot-actions-${item.id}`}
                className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-voxel-bevel-hi"
            >
                <Button
                    size="sm"
                    variant="outline"
                    colorScheme={item.is_live ? 'success' : 'neutral'}
                    disabled={isActionDisabled}
                    isLoading={isTogglingLive}
                    onClick={() => onToggleLive(item)}
                >
                    {item.is_live ? 'Pause Live' : 'Enable Live (30m)'}
                </Button>

                <Button
                    size="sm"
                    variant="outline"
                    colorScheme="danger"
                    aria-label={`Remove ${item.name}`}
                    disabled={isActionDisabled}
                    isLoading={isRemoving}
                    onClick={() => onRemove(item)}
                >
                    Remove
                </Button>
            </div>
        </Card>
    );
}

function ChevronRightIcon({ testId }: { testId: string }) {
    return (
        <svg
            data-testid={testId}
            className="w-4 h-4 shrink-0 text-voxel-muted transition-transform group-hover/open:translate-x-0.5 group-hover/open:text-accent"
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <polyline points="9 6 15 12 9 18" />
        </svg>
    );
}
