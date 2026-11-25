import { MetricTile } from '@llm-market-bench/ui-design-system';
import type * as React from 'react';

export interface BotSummaryItem {
    label: string;
    value: React.ReactNode;
}

export interface BotSummaryStripProps {
    items: BotSummaryItem[];
    /** Hub → details link. The host page builds it so the route literal stays typed. */
    detailLink?: React.ReactNode;
}

/**
 * The bot hub's single row of numbers.
 *
 * A hub card that carried only name, description and cadence was a splash screen:
 * the data lived in panels the visitor had to scroll to, which made the page serve
 * two purposes at once. The strip puts the four numbers that summarise the tab on
 * the card itself, and the trailing link is the one way into the detail page that
 * holds the full panels. Values are the same fields those panels read — nothing is
 * computed twice.
 */
export function BotSummaryStrip({ items, detailLink }: BotSummaryStripProps) {
    return (
        <div data-testid="bot-summary-strip" className="flex flex-col gap-3 min-w-0">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                {items.map((item) => (
                    <MetricTile key={item.label} label={item.label} value={item.value} />
                ))}
            </div>
            {detailLink ? <div className="flex justify-end min-w-0">{detailLink}</div> : null}
        </div>
    );
}
