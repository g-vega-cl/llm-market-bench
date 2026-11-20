import { Button } from '@llm-market-bench/ui-design-system';
import { useEffect, useState } from 'react';
import { canActivateTurboEt, formatTurboRemainingLabel } from '../utils/market-hours';

interface TurboButtonProps {
    turboExpiresAt?: string | null;
    turboUsedToday?: boolean;
    isActivating?: boolean;
    disabled?: boolean;
    now?: Date;
    onActivate: () => void;
}

/**
 * Shared 5-minute Turbo boost control for Studio and Live Status views.
 *
 * Displays live countdown while active, daily allowance exhaustion after use,
 * and market-hours gating (Mon-Fri 09:30-15:55 ET) outside regular sessions.
 */
export function TurboButton({
    turboExpiresAt,
    turboUsedToday = false,
    isActivating = false,
    disabled = false,
    now: externalNow,
    onActivate,
}: TurboButtonProps) {
    const [internalNow, setInternalNow] = useState<Date>(() => new Date());

    useEffect(() => {
        if (externalNow) return;
        const timer = setInterval(() => setInternalNow(new Date()), 15_000);
        return () => clearInterval(timer);
    }, [externalNow]);

    const currentNow = externalNow ?? internalNow;
    const remainingLabel = formatTurboRemainingLabel(turboExpiresAt, currentNow);
    if (remainingLabel) {
        return (
            <Button
                size="sm"
                variant="solid"
                colorScheme="accent"
                disabled
                suppressHydrationWarning
            >
                Turbo: {remainingLabel} (5m)
            </Button>
        );
    }

    if (turboUsedToday) {
        return (
            <Button size="sm" variant="outline" colorScheme="neutral" disabled>
                Turbo Used Today
            </Button>
        );
    }

    if (!canActivateTurboEt(currentNow)) {
        return (
            <Button
                size="sm"
                variant="outline"
                colorScheme="neutral"
                disabled
                suppressHydrationWarning
            >
                Turbo (Market Closed)
            </Button>
        );
    }

    return (
        <Button
            size="sm"
            variant="outline"
            colorScheme="accent"
            onClick={onActivate}
            disabled={disabled || isActivating}
            isLoading={isActivating}
            suppressHydrationWarning
        >
            Turbo (5m x 1h)
        </Button>
    );
}
