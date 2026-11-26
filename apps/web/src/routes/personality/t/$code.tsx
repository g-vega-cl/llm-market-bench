import { resolveAtmospherePhase } from '@llm-market-bench/ui-design-system';
import { createFileRoute, notFound } from '@tanstack/react-router';
import { PersonalityQuizPage } from '~/features/personality/PersonalityQuizPage';
import {
    ARCHETYPES,
    isValidTypeCode,
    TYPE_GRID,
    type TypeCode,
} from '~/features/personality/personality-data';
import { seo } from '~/lib/seo';

/**
 * Canonical share path: `/personality/t/LVFP`. Lowercase is accepted and
 * normalised; an unknown code is a 404 rather than a silent empty quiz.
 */
export const Route = createFileRoute('/personality/t/$code')({
    loader: ({ params }) => {
        const code = params.code.toUpperCase();
        if (!isValidTypeCode(code)) throw notFound();
        return {
            code: code as TypeCode,
            initialAtmosphere: resolveAtmospherePhase(new Date(), 'market-et'),
        };
    },
    head: ({ loaderData }) => {
        const code = loaderData?.code ?? '';
        const archetypeId = TYPE_GRID.find((cell) => cell.code === code)?.archetypeId;
        const archetype = archetypeId ? ARCHETYPES[archetypeId] : undefined;
        return {
            meta: [
                ...seo({
                    title: archetype
                        ? `${code} - ${archetype.title} | Benchify`
                        : `${code} | Benchify investing type`,
                    description: archetype
                        ? `${code}: ${archetype.tagline} Best starter bot: ${archetype.recipeName}.`
                        : 'A Benchify investing personality type.',
                }),
            ],
        };
    },
    component: RouteComponent,
});

function RouteComponent() {
    const { code, initialAtmosphere } = Route.useLoaderData();
    const archetypeId = TYPE_GRID.find((cell) => cell.code === code)?.archetypeId;

    return (
        <PersonalityQuizPage initialArchetype={archetypeId} initialAtmosphere={initialAtmosphere} />
    );
}
