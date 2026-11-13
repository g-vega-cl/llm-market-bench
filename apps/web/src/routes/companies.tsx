import { createFileRoute, Outlet, useMatches } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import { fetchCompaniesList } from '~/features/companies/api/fetch-companies';
import { CompaniesPage } from '~/features/companies/pages/CompaniesPage';

const getCompaniesData = createServerFn({ method: 'GET' }).handler(async () => {
    return fetchCompaniesList();
});

export const Route = createFileRoute('/companies')({
    loader: async () => await getCompaniesData(),
    component: RouteComponent,
});

export function RouteComponent() {
    const initialData = Route.useLoaderData();
    const matches = useMatches();
    const renderingDossier = matches.some((m) => m.routeId === '/companies/$ticker');

    if (renderingDossier) {
        return <Outlet />;
    }

    return <CompaniesPage initialCompanies={initialData} />;
}
