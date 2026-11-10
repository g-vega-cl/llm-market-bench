import { createFileRoute } from '@tanstack/react-router';
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

function RouteComponent() {
    const initialData = Route.useLoaderData();
    return <CompaniesPage initialCompanies={initialData} />;
}
