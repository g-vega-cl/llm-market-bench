import { createCsrfMiddleware, createMiddleware, createStart } from '@tanstack/react-start';
import { getPostHogClient } from './utils/posthog-server';

const posthogExceptionAutocapture = createMiddleware().server(async ({ next }) => {
    getPostHogClient();
    return await next();
});

export const startInstance = createStart(() => ({
    requestMiddleware: [
        createCsrfMiddleware({ filter: ({ handlerType }) => handlerType === 'serverFn' }),
        posthogExceptionAutocapture,
    ],
}));
