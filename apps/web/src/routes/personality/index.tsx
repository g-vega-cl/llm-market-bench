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
                title: 'Investing style test | Benchify',
                description:
                    'Take Benchify’s 16-question investing style test to find your trading personality and unlock a matched starter bot you can backtest.',
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
