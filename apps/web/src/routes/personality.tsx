import { createFileRoute } from '@tanstack/react-router';
import { PersonalityQuizPage } from '~/features/personality/PersonalityQuizPage';
import { type ArchetypeId, isValidArchetypeId } from '~/features/personality/personality-data';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/personality')({
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
    return <PersonalityQuizPage initialArchetype={archetype} />;
}
