import { resolveAtmospherePhase } from '@llm-market-bench/ui-design-system';
import { createFileRoute } from '@tanstack/react-router';
import { PersonalityQuizPage } from '~/features/personality/PersonalityQuizPage';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/personality/')({
    loader: () => ({
        initialAtmosphere: resolveAtmospherePhase(new Date(), 'market-et'),
    }),
    head: () => ({
        meta: [
            ...seo({
                title: 'Investing Style & Best Trading Bot Quiz | Benchify',
                description:
                    'Take the 16-question diagnostic, across four acts, to map your investing personality across Horizon, Signal Anchor, Crowd Stance, and Cadence and unlock your matched starter trading bot.',
            }),
        ],
    }),
    component: RouteComponent,
});

function RouteComponent() {
    const { archetype } = Route.useSearch();
    const { initialAtmosphere } = Route.useLoaderData();
    const navigate = Route.useNavigate();

    // `?archetype=<slug>` renders inspect mode directly. Deliberately no redirect to
    // the canonical `/personality/t/CODE` path here: that navigation remounts the
    // page and would drop the in-progress result state, including the Act-4 words.
    // Share links are canonical; the in-quiz URL is allowed to stay on the query param.
    return (
        <PersonalityQuizPage
            initialArchetype={archetype}
            initialAtmosphere={initialAtmosphere}
            onArchetypeSearchChange={(next) =>
                void navigate({
                    search: next ? { archetype: next } : {},
                    replace: true,
                })
            }
        />
    );
}
