import type { CaptureResult } from 'posthog-js';

/**
 * Checks whether an incoming PostHog event represents a synthetic CefSharp unhandled rejection
 * produced when Microsoft 365 Defender / Outlook "Safe Links" crawlers dispose host objects.
 */
export function isCefSharpScannerException(event: CaptureResult | null | undefined): boolean {
    if (!event || event.event !== '$exception' || !event.properties) {
        return false;
    }

    const { $exception_list, $exception_values, $exception_message } = event.properties;

    const matchesSignature = (text: unknown): boolean => {
        if (typeof text !== 'string') return false;
        return text.includes('Object Not Found Matching Id') && text.includes('MethodName:');
    };

    if (Array.isArray($exception_list)) {
        if (
            $exception_list.some((item) => {
                if (typeof item === 'string') return matchesSignature(item);
                return (
                    matchesSignature(item?.value) ||
                    matchesSignature(item?.type) ||
                    matchesSignature(item?.stack)
                );
            })
        ) {
            return true;
        }
    }

    if (Array.isArray($exception_values)) {
        if (
            $exception_values.some((item) => {
                if (typeof item === 'string') return matchesSignature(item);
                return matchesSignature(item?.value) || matchesSignature(item?.type);
            })
        ) {
            return true;
        }
    }

    if (matchesSignature($exception_message)) {
        return true;
    }

    try {
        const serialized = JSON.stringify(event.properties);
        if (matchesSignature(serialized)) {
            return true;
        }
    } catch {
        // Safe fallback in case of circular references
    }

    return false;
}

/**
 * PostHog before_send lifecycle handler.
 * Completely drops synthetic CefSharp crawler exceptions by returning null,
 * preventing external scanner teardown noise from creating PostHog Error Tracking issues.
 */
export function posthogBeforeSend(event: CaptureResult | null | undefined): CaptureResult | null {
    if (!event) return null;

    if (isCefSharpScannerException(event)) {
        return null;
    }

    return event;
}
