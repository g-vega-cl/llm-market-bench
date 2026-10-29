import { createFileRoute, redirect } from '@tanstack/react-router';

export const Route = createFileRoute('/today')({
    beforeLoad: () => {
        throw redirect({ to: '/' });
    },
});
