import { resolveAtmospherePhase } from '@llm-market-bench/ui-design-system';
import { createFileRoute } from '@tanstack/react-router';
import { PersonalityQuizPage } from '~/features/personality/PersonalityQuizPage';
import { type ArchetypeId, isValidArchetypeId } from '~/features/personality/personality-data';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/personality')({
    loader: () => ({
        initialAtmosphere: resolveAtmospherePhase(new Date(), 'market-et'),
    }),
    validateSearch: (search: Record<string, unknown>): { archetype?: ArchetypeId } => ({
        archetype: isValidArchetypeId(search.archetype) ? search.archetype : undefined,
    }),
    head: () => ({
        meta: [
            ...seo({
                title: 'Investing Style & Best Trading Bot Quiz | Benchify',
                description:
                    'Take the 10-question diagnostic to map your investing personality across Horizon, Signal, Crowd Stance, and Cadence and unlock your matched starter trading bot.',
            }),
        ],
    }),
    component: RouteComponent,
});

function RouteComponent() {
    const { archetype } = Route.useSearch();
    const { initialAtmosphere } = Route.useLoaderData();
    return (
        <PersonalityQuizPage initialArchetype={archetype} initialAtmosphere={initialAtmosphere} />
    );
}
