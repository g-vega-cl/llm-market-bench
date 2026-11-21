import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GardenBackdrop } from './GardenBackdrop';

function mockMatchMedia(matches: boolean) {
    Object.defineProperty(window, 'matchMedia', {
        writable: true,
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

describe('GardenBackdrop (lifecycle, reduced-motion, and null-context resilience)', () => {
    beforeEach(() => {
        if (typeof globalThis.ResizeObserver === 'undefined') {
            globalThis.ResizeObserver = class ResizeObserver {
                observe() {}
                unobserve() {}
                disconnect() {}
            };
        }
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('renders safely when mounted at 0x0 or when getContext("2d") returns null', () => {
        mockMatchMedia(true);
        const getContextSpy = vi
            .spyOn(HTMLCanvasElement.prototype, 'getContext')
            .mockReturnValue(null);

        const { unmount } = render(<GardenBackdrop />);
        const canvas = screen.getByTestId('garden-backdrop') as HTMLCanvasElement;

        expect(canvas).toBeInTheDocument();
        expect(canvas.width).toBe(300); // default jsdom canvas width untouched on 0x0 bail
        expect(getContextSpy).not.toHaveBeenCalled();

        unmount();
    });

    it('respects prefers-reduced-motion and toggles between Play motion and Pause motion', () => {
        mockMatchMedia(true);
        const rafSpy = vi.spyOn(window, 'requestAnimationFrame').mockReturnValue(1);
        const cancelSpy = vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});

        const { unmount } = render(<GardenBackdrop />);

        const btn = screen.getByRole('button', { name: 'Play motion' });
        expect(rafSpy).not.toHaveBeenCalled();

        fireEvent.click(btn);
        expect(screen.getByRole('button', { name: 'Pause motion' })).toBeInTheDocument();
        expect(rafSpy).toHaveBeenCalledTimes(1);

        fireEvent.click(screen.getByRole('button', { name: 'Pause motion' }));
        expect(screen.getByRole('button', { name: 'Play motion' })).toBeInTheDocument();
        expect(cancelSpy).toHaveBeenCalled();

        unmount();
    });

    it('cleans up window and document event listeners on unmount', () => {
        mockMatchMedia(false);
        vi.spyOn(window, 'requestAnimationFrame').mockReturnValue(7);
        const removeWinSpy = vi.spyOn(window, 'removeEventListener');
        const removeDocSpy = vi.spyOn(document, 'removeEventListener');

        const { unmount } = render(<GardenBackdrop />);
        unmount();

        const removedWinEvents = removeWinSpy.mock.calls.map(([ev]) => ev);
        expect(removedWinEvents).toEqual(
            expect.arrayContaining(['resize', 'pointermove', 'keydown', 'touchstart']),
        );
        expect(removeDocSpy.mock.calls.map(([ev]) => ev)).toContain('visibilitychange');
    });
});
