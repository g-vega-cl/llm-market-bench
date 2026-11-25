import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useDioramaStage } from './useDioramaStage';

function mockMatchMedia(matches: boolean) {
    Object.defineProperty(window, 'matchMedia', {
        writable: true,
        configurable: true,
        value: vi.fn().mockImplementation((query: string) => ({
            matches,
            media: query,
            onchange: null,
            addListener: vi.fn(),
            removeListener: vi.fn(),
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
            dispatchEvent: vi.fn(),
        })),
    });
}

describe('useDioramaStage (derived motion state)', () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('starts running and toggles to paused and back', () => {
        mockMatchMedia(false);
        const { result } = renderHook(() => useDioramaStage('dusk'));

        expect(result.current.motion).toBe('running');

        act(() => {
            result.current.toggleMotion();
        });
        expect(result.current.motion).toBe('paused');

        act(() => {
            result.current.toggleMotion();
        });
        expect(result.current.motion).toBe('running');
    });

    it('lets the OS preference outrank the visitor toggle', () => {
        mockMatchMedia(true);
        const { result } = renderHook(() => useDioramaStage('dawn'));

        expect(result.current.motion).toBe('reduced');

        // Toggling cannot un-freeze a scene the OS asked to freeze.
        act(() => {
            result.current.toggleMotion();
        });
        expect(result.current.motion).toBe('reduced');
    });

    it('cycles the sky and keeps the SSR-resolved atmosphere as the first value', () => {
        mockMatchMedia(false);
        const { result } = renderHook(() => useDioramaStage('dusk'));

        expect(result.current.atmosphere).toBe('dusk');

        act(() => {
            result.current.cycleAtmosphere();
        });
        expect(result.current.atmosphere).toBe('after-hours');
    });
});
