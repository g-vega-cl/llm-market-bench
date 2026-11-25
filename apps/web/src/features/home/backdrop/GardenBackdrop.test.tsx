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

        const { unmount } = render(<GardenBackdrop atmosphere="dusk" motion="running" />);
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

    it('implements the SceneBackdropProps contract when hosted inside SceneStage', () => {
        mockMatchMedia(true);
        const { rerender } = render(<GardenBackdrop atmosphere="dawn" motion="reduced" />);

        const canvas = screen.getByTestId('garden-backdrop');
        expect(canvas).toHaveAttribute('data-world', CEDAR_WORLD_ID);
        expect(canvas).toHaveAttribute('data-atmosphere', 'dawn');
        expect(canvas).toHaveAttribute('data-motion', 'reduced');
        expect(screen.queryByRole('button')).toBeNull();

        rerender(<GardenBackdrop atmosphere="after-hours" motion="reduced" />);
        expect(canvas).toHaveAttribute('data-atmosphere', 'after-hours');
    });

    it('freezes while the host reports a non-running motion and resumes when it runs again', () => {
        mockMatchMedia(false);
        const rafSpy = vi.spyOn(window, 'requestAnimationFrame').mockReturnValue(1);
        const cancelSpy = vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});

        // Fully controlled now: the host derives `motion`, the canvas only
        // reacts to it. An internal Pause button would be a second owner.
        const { rerender, unmount } = render(<GardenBackdrop atmosphere="dusk" motion="running" />);
        expect(rafSpy).toHaveBeenCalled();

        rafSpy.mockClear();
        rerender(<GardenBackdrop atmosphere="dusk" motion="paused" />);
        expect(cancelSpy).toHaveBeenCalled();
        expect(rafSpy).not.toHaveBeenCalled();

        rerender(<GardenBackdrop atmosphere="dusk" motion="reduced" />);
        expect(rafSpy).not.toHaveBeenCalled();

        rerender(<GardenBackdrop atmosphere="dusk" motion="running" />);
        expect(rafSpy).toHaveBeenCalled();

        unmount();
    });

    it('never starts RAF on mount when prefers-reduced-motion races a running host, or when the host is frozen', () => {
        mockMatchMedia(true);
        const rafSpy = vi.spyOn(window, 'requestAnimationFrame').mockReturnValue(1);

        const first = render(<GardenBackdrop atmosphere="dusk" motion="running" />);
        expect(rafSpy).not.toHaveBeenCalled();
        first.unmount();

        rafSpy.mockClear();
        mockMatchMedia(false);
        const second = render(<GardenBackdrop atmosphere="dusk" motion="paused" />);
        expect(rafSpy).not.toHaveBeenCalled();
        second.unmount();
    });

    it('cleans up window and document event listeners on unmount', () => {
        mockMatchMedia(false);
        vi.spyOn(window, 'requestAnimationFrame').mockReturnValue(7);
        const removeWinSpy = vi.spyOn(window, 'removeEventListener');
        const removeDocSpy = vi.spyOn(document, 'removeEventListener');

        const { unmount } = render(<GardenBackdrop atmosphere="dusk" motion="running" />);
        unmount();

        const removedWinEvents = removeWinSpy.mock.calls.map(([ev]) => ev);
        expect(removedWinEvents).toEqual(
            expect.arrayContaining(['resize', 'pointermove', 'keydown', 'touchstart']),
        );
        expect(removeDocSpy.mock.calls.map(([ev]) => ev)).toContain('visibilitychange');
    });

    it('renders non-zero viewport layers, advances entrance RAF, settles immediately on pause, and disposes canvases', () => {
        mockMatchMedia(false);
        let rafCallback: FrameRequestCallback | undefined;
        let nowMs = 1000;
        vi.spyOn(performance, 'now').mockImplementation(() => nowMs);
        vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => {
            rafCallback = cb;
            return 11;
        });
        vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});

        const fakeGradient = { addColorStop: vi.fn() };
        const fakeCtx = {
            setTransform: vi.fn(),
            clearRect: vi.fn(),
            createLinearGradient: vi.fn(() => fakeGradient),
            createRadialGradient: vi.fn(() => fakeGradient),
            fillRect: vi.fn(),
            beginPath: vi.fn(),
            moveTo: vi.fn(),
            lineTo: vi.fn(),
            rect: vi.fn(),
            closePath: vi.fn(),
            fill: vi.fn(),
            stroke: vi.fn(),
            drawImage: vi.fn(),
            clip: vi.fn(),
            save: vi.fn(),
            restore: vi.fn(),
            globalAlpha: 1,
            globalCompositeOperation: 'source-over',
            fillStyle: '',
            strokeStyle: '',
            lineWidth: 1,
        } as unknown as CanvasRenderingContext2D;

        vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(fakeCtx);
        vi.spyOn(HTMLCanvasElement.prototype, 'clientWidth', 'get').mockReturnValue(390);
        vi.spyOn(HTMLCanvasElement.prototype, 'clientHeight', 'get').mockReturnValue(780);

        const origCreateElement = document.createElement.bind(document);
        const createdOffscreenCanvases: HTMLCanvasElement[] = [];
        vi.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
            const el = origCreateElement(tagName);
            if (tagName === 'canvas') createdOffscreenCanvases.push(el as HTMLCanvasElement);
            return el;
        });

        const clearTimeoutSpy = vi.spyOn(window, 'clearTimeout');
        const { rerender, unmount } = render(<GardenBackdrop atmosphere="dusk" motion="running" />);

        const canvas = screen.getByTestId('garden-backdrop') as HTMLCanvasElement;
        const offscreenCanvases = createdOffscreenCanvases.filter((c) => c !== canvas);
        expect(canvas.className).toContain('opacity-100');
        // sky, foot, island, lantern sprite + one cropped canvas per cloud
        expect(offscreenCanvases).toHaveLength(10);
        expect(fakeCtx.clip).not.toHaveBeenCalled();

        // Advance one entrance frame past frame interval -> stepped reveal clip activates
        nowMs += 40;
        rafCallback?.(nowMs);
        expect(fakeCtx.clip).toHaveBeenCalled();
        expect(fakeCtx.drawImage).toHaveBeenCalled();

        // Freezing mid-entrance (host flips motion) settles the diorama
        // completely, without the clip mask
        (fakeCtx.clip as ReturnType<typeof vi.fn>).mockClear();
        rerender(<GardenBackdrop atmosphere="dusk" motion="paused" />);
        expect(clearTimeoutSpy).toHaveBeenCalled();
        expect(fakeCtx.clip).not.toHaveBeenCalled();

        unmount();
        for (const offscreen of offscreenCanvases) {
            expect(offscreen.width).toBe(0);
            expect(offscreen.height).toBe(0);
        }
    });
});
