import { ATMOSPHERE_PHASES } from '@llm-market-bench/ui-design-system';
import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GardenBackdrop } from './GardenBackdrop';
import { ATMOSPHERE_PALETTES } from './garden-renderer';
import { CEDAR_WORLD_ID } from './voxel-world';

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

describe('GardenBackdrop (Cedar Sanctuary lifecycle, atmosphere phases, reduced-motion, and null-context resilience)', () => {
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
        expect(canvas).toHaveAttribute('data-world', CEDAR_WORLD_ID);
        expect(canvas).toHaveAttribute('data-atmosphere', 'dusk');
        expect(canvas.width).toBe(300); // default jsdom canvas width untouched on 0x0 bail
        expect(getContextSpy).not.toHaveBeenCalled();

        unmount();
    });

    it('defines distinct Matcha & Cedar sky and lighting palettes for all 4 atmosphere phases', () => {
        const zenithTops = new Set<string>();
        for (const phase of ATMOSPHERE_PHASES) {
            const palette = ATMOSPHERE_PALETTES[phase];
            expect(palette).toBeDefined();
            expect(palette.skyStops.length).toBeGreaterThanOrEqual(7);
            zenithTops.add(palette.skyStops[0][1]);
        }
        expect(zenithTops.size).toBe(4);
    });

    it('supports controlled atmosphere and showControls={false} when hosted inside SceneStage', () => {
        mockMatchMedia(true);
        const { rerender } = render(
            <GardenBackdrop atmosphere="dawn" showControls={false} paused={true} />,
        );

        const canvas = screen.getByTestId('garden-backdrop');
        expect(canvas).toHaveAttribute('data-world', CEDAR_WORLD_ID);
        expect(canvas).toHaveAttribute('data-atmosphere', 'dawn');
        expect(screen.queryByRole('button')).toBeNull();

        rerender(<GardenBackdrop atmosphere="after-hours" showControls={false} paused={true} />);
        expect(canvas).toHaveAttribute('data-atmosphere', 'after-hours');
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

    it('never starts RAF on mount when paused={false} races prefers-reduced-motion or when paused={true}', () => {
        mockMatchMedia(true);
        const rafSpy = vi.spyOn(window, 'requestAnimationFrame').mockReturnValue(1);
        const onPausedChange = vi.fn();

        const first = render(
            <GardenBackdrop paused={false} onPausedChange={onPausedChange} showControls={false} />,
        );
        expect(rafSpy).not.toHaveBeenCalled();
        expect(onPausedChange).toHaveBeenCalledWith(true);
        first.unmount();

        rafSpy.mockClear();
        mockMatchMedia(false);
        const second = render(<GardenBackdrop paused={true} showControls={false} />);
        expect(rafSpy).not.toHaveBeenCalled();
        second.unmount();
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
