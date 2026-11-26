import { createFileRoute } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import { fetchCompanyDossier } from '~/features/companies/api/fetch-company-dossier';
import { CompanyDossierPage } from '~/features/companies/pages/CompanyDossierPage';

const getCompanyDossierData = createServerFn({ method: 'GET' })
    .validator((ticker: string) => ticker)
    .handler(async ({ data: ticker }) => {
        return fetchCompanyDossier(ticker);
    });

export const Route = createFileRoute('/companies/$ticker')({
    loader: async ({ params }) => await getCompanyDossierData({ data: params.ticker }),
    component: RouteComponent,
});

function RouteComponent() {
    const initialData = Route.useLoaderData();
    return <CompanyDossierPage initialData={initialData} />;
}
