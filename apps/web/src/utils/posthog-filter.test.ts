import type { CaptureResult } from 'posthog-js';
import { describe, expect, it } from 'vitest';
import { isCefSharpScannerException, posthogBeforeSend } from './posthog-filter';

describe('posthog-filter CefSharp scanner detection', () => {
    it('detects CefSharp synthetic exception in $exception_list', () => {
        const event: CaptureResult = {
            uuid: 'test-uuid-1',
            event: '$exception',
            properties: {
                $exception_level: 'error',
                $exception_list: [
                    {
                        type: 'UnhandledRejection',
                        value: 'Non-Error promise rejection captured with value: Object Not Found Matching Id:3, MethodName:update, ParamCount:4',
                    },
                ],
            },
        };

        expect(isCefSharpScannerException(event)).toBe(true);
    });

    it('detects CefSharp synthetic exception in $exception_values', () => {
        const event: CaptureResult = {
            uuid: 'test-uuid-2',
            event: '$exception',
            properties: {
                $exception_level: 'error',
                $exception_values: [
                    'Object Not Found Matching Id:2, MethodName:update, ParamCount:4',
                ],
            },
        };

        expect(isCefSharpScannerException(event)).toBe(true);
    });

    it('detects CefSharp synthetic exception in $exception_message', () => {
        const event: CaptureResult = {
            uuid: 'test-uuid-3',
            event: '$exception',
            properties: {
                $exception_level: 'error',
                $exception_message:
                    'UnhandledRejection: Non-Error promise rejection captured with value: Object Not Found Matching Id:3, MethodName:update, ParamCount:4',
            },
        };

        expect(isCefSharpScannerException(event)).toBe(true);
    });

    it('returns false for standard application exceptions', () => {
        const event: CaptureResult = {
            uuid: 'test-uuid-4',
            event: '$exception',
            properties: {
                $exception_level: 'error',
                $exception_list: [
                    {
                        type: 'TypeError',
                        value: 'Cannot read properties of undefined (reading "map")',
                    },
                ],
            },
        };

        expect(isCefSharpScannerException(event)).toBe(false);
    });

    it('returns false for non-exception events', () => {
        const event: CaptureResult = {
            uuid: 'test-uuid-5',
            event: '$pageview',
            properties: {
                $current_url: 'https://example.com/portfolios',
            },
        };

        expect(isCefSharpScannerException(event)).toBe(false);
    });

    it('returns false for null or malformed events', () => {
        expect(isCefSharpScannerException(null)).toBe(false);
        expect(isCefSharpScannerException(undefined as unknown as CaptureResult)).toBe(false);
        expect(isCefSharpScannerException({} as CaptureResult)).toBe(false);
    });
});

describe('posthogBeforeSend event transformation', () => {
    it('downgrades CefSharp scanner exception to warning severity with scanner tags', () => {
        const event: CaptureResult = {
            uuid: 'test-uuid-6',
            event: '$exception',
            properties: {
                $exception_level: 'error',
                $exception_list: [
                    {
                        type: 'UnhandledRejection',
                        value: 'Non-Error promise rejection captured with value: Object Not Found Matching Id:3, MethodName:update, ParamCount:4',
                    },
                ],
            },
        };

        const result = posthogBeforeSend(event);

        expect(result).not.toBeNull();
        expect(result?.event).toBe('$exception');
        expect(result?.properties?.$exception_level).toBe('warning');
        expect(result?.properties?.$scanner_detected).toBe(true);
        expect(result?.properties?.$scanner_type).toBe('cefsharp_safelinks');
        // Preserves original exception list and stack details
        expect(result?.properties?.$exception_list).toEqual(event.properties.$exception_list);
    });

    it('leaves legitimate application errors intact at error severity', () => {
        const event: CaptureResult = {
            uuid: 'test-uuid-7',
            event: '$exception',
            properties: {
                $exception_level: 'error',
                $exception_list: [
                    {
                        type: 'RangeError',
                        value: 'Invalid array length',
                    },
                ],
            },
        };

        const result = posthogBeforeSend(event);

        expect(result).toEqual(event);
        expect(result?.properties?.$exception_level).toBe('error');
        expect(result?.properties?.$scanner_detected).toBeUndefined();
    });

    it('leaves normal analytics events intact', () => {
        const event: CaptureResult = {
            uuid: 'test-uuid-8',
            event: '$pageview',
            properties: {
                $current_url: 'https://example.com/daily-predictions',
            },
        };

        const result = posthogBeforeSend(event);

        expect(result).toEqual(event);
    });

    it('returns null when input event is null or undefined', () => {
        expect(posthogBeforeSend(null)).toBeNull();
        expect(posthogBeforeSend(undefined as unknown as CaptureResult)).toBeNull();
    });
});
