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
        if ($exception_list.some((item) => matchesSignature(item?.value))) {
            return true;
        }
    }

    if (Array.isArray($exception_values)) {
        if ($exception_values.some(matchesSignature)) {
            return true;
        }
    }

    if (matchesSignature($exception_message)) {
        return true;
    }

    return false;
}

/**
 * PostHog before_send lifecycle handler.
 * Downgrades synthetic CefSharp crawler exceptions from 'error' to 'warning' severity
 * while preserving the event and telemetry in PostHog for future audit.
 */
export function posthogBeforeSend(event: CaptureResult | null | undefined): CaptureResult | null {
    if (!event) return null;

    if (isCefSharpScannerException(event)) {
        return {
            ...event,
            properties: {
                ...event.properties,
                $exception_level: 'warning',
                $scanner_detected: true,
                $scanner_type: 'cefsharp_safelinks',
            },
        };
    }

    return event;
}
