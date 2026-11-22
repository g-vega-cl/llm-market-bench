import { createFileRoute, Outlet } from '@tanstack/react-router';
import { type ArchetypeId, isValidArchetypeId } from '~/features/personality/personality-data';

/**
 * Layout-only route for `/personality`: it owns the validated `?archetype=` search
 * param (inherited by both children) and renders nothing but an outlet, so the quiz
 * index (`/personality`) and a shared type (`/personality/t/CODE`) stay siblings.
 */
export const Route = createFileRoute('/personality')({
    validateSearch: (search: Record<string, unknown>): { archetype?: ArchetypeId } => ({
        archetype: isValidArchetypeId(search.archetype) ? search.archetype : undefined,
    }),
    component: PersonalityLayout,
});

function PersonalityLayout() {
    return <Outlet />;
}
