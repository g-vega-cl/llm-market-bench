import { createFileRoute } from '@tanstack/react-router';
import { LegalPage } from '~/features/legal/LegalPage';
import { privacyPolicy } from '~/features/legal/legal-content';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/privacy')({
    head: () => ({
        meta: [
            ...seo({
                title: 'Privacy Policy | Benchify',
                description:
                    'What Benchify collects, which providers process it, how long it is kept, and how to request deletion.',
            }),
        ],
    }),
    component: () => <LegalPage document={privacyPolicy} />,
});
