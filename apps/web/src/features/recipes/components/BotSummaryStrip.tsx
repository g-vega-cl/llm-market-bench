import { Badge, MetricTile } from '@llm-market-bench/ui-design-system';
import type * as React from 'react';

export interface BotSummaryItem {
    label: string;
    value: React.ReactNode;
}

export interface BotSummaryStripProps {
    items: BotSummaryItem[];
}

/**
 * The Overview tab's single row of numbers.
 *
 * The strip used to end in a "→ Performance, behaviors & positions" link because
 * the panels lived on a second page with no other way in. Performance, Behaviour
 * and Live Runs are tabs now, so the strip is only the bot's four numbers.
 */
export function BotSummaryStrip({ items }: BotSummaryStripProps) {
    return (
        <div data-testid="bot-summary-strip" className="flex flex-col gap-3 min-w-0">
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,11rem),1fr))] gap-3">
                {items.map((item) => (
                    <MetricTile key={item.label} label={item.label} value={item.value} />
                ))}
            </div>
        </div>
    );
}
