import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { VoxelWorld } from './VoxelWorld';

/**
 * jsdom has no WebGL, so every GL surface is a stub. A Proxy keeps the stub
 * honest as the renderer grows: unknown methods become no-ops instead of
 * undefined-is-not-a-function.
 */
function makeGl(overrides: Record<string, unknown> = {}): WebGL2RenderingContext {
    const constants: Record<string, unknown> = {
        VERTEX_SHADER: 1,
        FRAGMENT_SHADER: 2,
        COMPILE_STATUS: 3,
        LINK_STATUS: 4,
        ARRAY_BUFFER: 5,
        STATIC_DRAW: 6,
        TRIANGLES: 7,
        FLOAT: 8,
        COLOR_BUFFER_BIT: 16,
    };
    const stub = new Proxy(constants, {
        get(target, property: string) {
            if (property in overrides) return overrides[property];
            if (property in target) return target[property];
            const noop = () => ({});
            target[property] = noop;
            return noop;
        },
    });
    return stub as unknown as WebGL2RenderingContext;
}

async function flushIdle() {
    await act(async () => {
        vi.advanceTimersByTime(5);
    });
}

describe('VoxelWorld', () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
        vi.restoreAllMocks();
    });

    it('renders a decorative canvas, hidden from assistive tech and from drags', () => {
        render(<VoxelWorld tone="neutral" />);

        const canvas = screen.getByTestId('voxel-world');
        expect(canvas.closest('[aria-hidden="true"]')).not.toBeNull();
        expect(canvas.className).toContain('pointer-events-none');
    });

    it('falls back once, with a reason, when there is no WebGL2 context', async () => {
        const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
        render(<VoxelWorld tone="bearish" createContext={() => null} />);

        await flushIdle();

        const fallback = screen.getByTestId('world-fallback');
        expect(fallback).toHaveAttribute('data-reason', 'no-context');
        expect(warn).toHaveBeenCalledTimes(1);
        expect(warn).toHaveBeenCalledWith('[world] fallback', 'no-context');
    });

    it('falls back when the context factory throws instead of crashing the page', async () => {
        vi.spyOn(console, 'warn').mockImplementation(() => {});
        render(
            <VoxelWorld
                tone="neutral"
                createContext={() => {
                    throw new Error('gpu gone');
                }}
            />,
        );

        await flushIdle();

        expect(screen.getByTestId('world-fallback')).toHaveAttribute('data-reason', 'throw');
    });

    it('reports a shader failure from the renderer rather than pretending to draw', async () => {
        vi.spyOn(console, 'warn').mockImplementation(() => {});
        const gl = makeGl({ createShader: () => null });
        render(<VoxelWorld tone="bullish" createContext={() => gl} />);

        await flushIdle();

        expect(screen.getByTestId('world-fallback')).toHaveAttribute('data-reason', 'shader');
    });

    it('offers a pause control that reflects its state', () => {
        render(<VoxelWorld tone="neutral" />);

        const pause = screen.getByRole('button', { name: 'Pause the world' });
        expect(pause).toHaveAttribute('aria-pressed', 'false');

        act(() => {
            pause.click();
        });

        const resume = screen.getByRole('button', { name: 'Resume the world' });
        expect(resume).toHaveAttribute('aria-pressed', 'true');
    });

    it('tears down a live session without throwing', async () => {
        vi.spyOn(console, 'warn').mockImplementation(() => {});
        const gl = makeGl();
        const view = render(<VoxelWorld tone="neutral" createContext={() => gl} />);

        await flushIdle();
        expect(screen.queryByTestId('world-fallback')).not.toBeInTheDocument();

        expect(() => view.unmount()).not.toThrow();
    });
});
