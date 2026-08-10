import { act } from '@testing-library/react';
import type React from 'react';
import { hydrateRoot } from 'react-dom/client';
import ReactDOMServer from 'react-dom/server';
import { vi } from 'vitest';

/**
 * Asserts that a React element hydrates successfully in JSDOM without triggering
 * any React hydration mismatches (Error #418, prop mismatches, etc.).
 *
 * @param element The React element to render and hydrate
 * @returns An array of string error/warning messages captured during hydration
 */
export function assertHydrationSymmetry(element: React.ReactElement): string[] {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const hydrationErrors: string[] = [];

    // Set up a global error event listener to catch React 19's thrown hydration errors
    const globalErrorHandler = (event: ErrorEvent) => {
        const errorMsg = event.message || String(event.error);
        const lower = errorMsg.toLowerCase();

        if (
            lower.includes('hydration') ||
            lower.includes('did not match') ||
            lower.includes('react error #418') ||
            lower.includes('react error #423') ||
            lower.includes('text content')
        ) {
            event.preventDefault(); // Prevent Vitest from catching this as an unhandled error
            hydrationErrors.push(errorMsg);
        }
    };

    window.addEventListener('error', globalErrorHandler);

    let root: ReturnType<typeof hydrateRoot> | undefined;
    const container = document.createElement('div');

    try {
        // 1. Simulate SSR (Server-Side Rendering)
        const serverHtml = ReactDOMServer.renderToString(element);

        // 2. Set up the JSDOM container with SSR markup
        container.innerHTML = serverHtml;
        document.body.appendChild(container);

        // 3. Simulate Client Hydration wrapped in act() to flush synchronous updates
        try {
            act(() => {
                root = hydrateRoot(container, element);
            });
        } catch (err) {
            const errorMsg = err instanceof Error ? err.message : String(err);
            hydrationErrors.push(errorMsg);
        }
    } finally {
        // Clean up DOM and unmount client root wrapped in act()
        if (root) {
            try {
                act(() => {
                    root?.unmount();
                });
            } catch {
                // Ignore harmless unmount warnings from act in JSDOM
            }
        }
        if (container.parentNode) {
            document.body.removeChild(container);
        }

        // Remove the error listener and restore console.error
        window.removeEventListener('error', globalErrorHandler);
    }

    // 4. Retrieve captured React hydration mismatch errors from console.error
    const consoleErrors = consoleErrorSpy.mock.calls
        .map(([msg, ...args]) => {
            // Format message if it contains specifiers
            if (typeof msg === 'string') {
                return msg.replace(/%s/g, () => String(args.shift() || ''));
            }
            return String(msg);
        })
        .filter((msg) => {
            const lower = msg.toLowerCase();
            return (
                lower.includes('hydration') ||
                lower.includes('did not match') ||
                lower.includes('react error #418') ||
                lower.includes('react error #423') ||
                lower.includes('text content')
            );
        });

    hydrationErrors.push(...consoleErrors);
    consoleErrorSpy.mockRestore();
    consoleWarnSpy.mockRestore();

    return hydrationErrors;
}
