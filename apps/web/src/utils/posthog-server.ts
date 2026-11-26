import { PostHog } from 'posthog-node';

let posthogClient: PostHog | null = null;

export function getPostHogClient(): PostHog | null {
    const token =
        process.env.VITE_PUBLIC_POSTHOG_PROJECT_TOKEN ||
        process.env.PUBLIC_POSTHOG_PROJECT_TOKEN ||
        import.meta.env.VITE_PUBLIC_POSTHOG_PROJECT_TOKEN ||
        '';
    if (!token) {
        return null;
    }
    if (!posthogClient) {
        posthogClient = new PostHog(token, {
            host:
                process.env.VITE_PUBLIC_POSTHOG_HOST ||
                process.env.PUBLIC_POSTHOG_HOST ||
                import.meta.env.VITE_PUBLIC_POSTHOG_HOST,
            flushAt: 1,
            flushInterval: 0,
            enableExceptionAutocapture: true,
        });
    }
    return posthogClient;
}
