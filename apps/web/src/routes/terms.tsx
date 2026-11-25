import { createFileRoute } from '@tanstack/react-router';
import { LegalPage } from '~/features/legal/LegalPage';
import { termsOfService } from '~/features/legal/legal-content';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/terms')({
    head: () => ({
        meta: [
            ...seo({
                title: 'Terms of Service | Benchify',
                description:
                    'Beta terms governing use of benchify.dev, including account responsibilities, acceptable use, and liability limits.',
            }),
        ],
    }),
    component: () => <LegalPage document={termsOfService} />,
});
