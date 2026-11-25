import { createFileRoute } from '@tanstack/react-router';
import { LegalPage } from '~/features/legal/LegalPage';
import { financialDisclaimer } from '~/features/legal/legal-content';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/disclaimer')({
    head: () => ({
        meta: [
            ...seo({
                title: 'Financial Disclaimer | Benchify',
                description:
                    'Benchify is a research and benchmarking tool, not financial advice. Paper trading only; backtests are simulations.',
            }),
        ],
    }),
    component: () => <LegalPage document={financialDisclaimer} />,
});
