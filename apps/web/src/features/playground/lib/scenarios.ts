import { STARTER_RECIPES } from '~/features/recipes/starter-templates';
import type { PushStrategy } from '~/features/recipes/types';

export interface Scenario {
    id: string;
    label: string;
    blurb: string;
    strategy: PushStrategy;
}

/**
 * Visitor-facing names for the five starters (N9). The recipes keep their
 * internal names so seeding and the studio stay untouched; only the chips change.
 */
const VISITOR_COPY: Record<string, { label: string; blurb: string }> = {
    'Trump & Chips News Momentum': {
        label: 'Chip tariff momentum',
        blurb: 'Buys chipmakers when tariff and capex headlines turn positive.',
    },
    'Claude Agent Portfolio Mirror': {
        label: 'Follow the desk',
        blurb: 'Copies what the live research agent is buying, with its tools.',
    },
    'Quality Value Screener': {
        label: 'Cheap quality',
        blurb: 'Low P/E, real free cash flow, price above its long trend.',
    },
    'Contrarian Sentiment Fader': {
        label: 'Fade the crowd',
        blurb: 'Buys when the desk is fearful and sells when it is euphoric.',
    },
    'Earnings Catalyst Hunter': {
        label: 'Earnings surprises',
        blurb: 'Trades tickers whose last earnings beat and are in the news.',
    },
};

export const SCENARIOS: Scenario[] = STARTER_RECIPES.map((strategy) => {
    const copy = VISITOR_COPY[strategy.name];
    return {
        id: strategy.name,
        label: copy?.label ?? strategy.name,
        blurb: copy?.blurb ?? strategy.description ?? '',
        strategy,
    };
});
