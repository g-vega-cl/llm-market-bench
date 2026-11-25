import { ATMOSPHERE_PHASES } from '@llm-market-bench/ui-design-system';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { CedarRidgeBackdrop, type CedarRidgeBackdropProps } from './CedarRidgeBackdrop';

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

async function nextFrame() {
    await new Promise<void>((resolve) => {
        requestAnimationFrame(() => {
            resolve();
        });
    });
}

function renderBackdrop(overrides: Partial<CedarRidgeBackdropProps> = {}) {
    return render(<CedarRidgeBackdrop atmosphere="dusk" motion="running" {...overrides} />);
}

describe('CedarRidgeBackdrop (planes, atmosphere exposure, drift and pause)', () => {
    beforeEach(() => {
        mockMatchMedia(false);
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('renders six depth planes with the moon and meadow fauna', () => {
        const { container } = renderBackdrop();
        const root = screen.getByTestId('cedar-ridge-backdrop');

        expect(root).toHaveAttribute('data-world', 'cedar-ridge');
        expect(root).toHaveAttribute('data-atmosphere', 'dusk');
        expect(root).toHaveAttribute('data-motion', 'running');
        expect(container.querySelectorAll('.cr-layer')).toHaveLength(6);
        expect(container.querySelector('.cr-celestial')).not.toBeNull();
        expect(container.querySelector('.cr-bot')).not.toBeNull();
        expect(container.querySelector('.cr-fox')).not.toBeNull();
        expect(container.querySelectorAll('.cr-firefly')).toHaveLength(4);
    });

    it('carries the atmosphere phase onto the root for exposure-only styling', () => {
        for (const phase of ATMOSPHERE_PHASES) {
            const { unmount } = renderBackdrop({ atmosphere: phase });
            expect(screen.getByTestId('cedar-ridge-backdrop')).toHaveAttribute(
                'data-atmosphere',
                phase,
            );
            unmount();
        }
    });

    it('carries the derived motion onto the root so CSS can freeze every loop', () => {
        const { rerender } = renderBackdrop();
        expect(screen.getByTestId('cedar-ridge-backdrop')).toHaveAttribute(
            'data-motion',
            'running',
        );

        rerender(<CedarRidgeBackdrop atmosphere="dusk" motion="paused" />);
        expect(screen.getByTestId('cedar-ridge-backdrop')).toHaveAttribute('data-motion', 'paused');

        rerender(<CedarRidgeBackdrop atmosphere="dusk" motion="reduced" />);
        expect(screen.getByTestId('cedar-ridge-backdrop')).toHaveAttribute(
            'data-motion',
            'reduced',
        );
    });

    it('writes pointer drift into the root custom properties', async () => {
        renderBackdrop();
        const root = screen.getByTestId('cedar-ridge-backdrop');

        await act(async () => {
            fireEvent.pointerMove(window, { clientX: 0, clientY: 0 });
            await nextFrame();
            await nextFrame();
        });

        const px = Number(root.style.getPropertyValue('--cr-px'));
        const py = Number(root.style.getPropertyValue('--cr-py'));
        expect(Number.isFinite(px)).toBe(true);
        expect(px).toBeGreaterThan(0);
        expect(py).toBeGreaterThan(0);
    });

    it('ignores pointer drift while paused and settles back to centre', async () => {
        renderBackdrop({ motion: 'paused' });
        const root = screen.getByTestId('cedar-ridge-backdrop');

        await act(async () => {
            fireEvent.pointerMove(window, { clientX: 10, clientY: 10 });
            await nextFrame();
            await nextFrame();
        });

        expect(root.style.getPropertyValue('--cr-px')).toBe('0.00');
        expect(root.style.getPropertyValue('--cr-py')).toBe('0.00');
    });

    it('settles without a pointer sample when the OS asks for reduced motion', async () => {
        mockMatchMedia(true);
        renderBackdrop({ motion: 'reduced' });
        const root = screen.getByTestId('cedar-ridge-backdrop');

        await act(async () => {
            fireEvent.pointerMove(window, { clientX: 1500, clientY: 900 });
            await nextFrame();
            await nextFrame();
        });

        expect(root.style.getPropertyValue('--cr-px')).toBe('0.00');
    });

    it('derives the scroll offset instead of accumulating it', async () => {
        // The bug this pins: an `y -= scrollTerm()` accumulator subtracts again
        // on every scroll event at an unchanged offset, walking the scene off
        // the stage on touch devices where no pointermove re-derives it.
        Object.defineProperty(window, 'scrollY', { value: 900, configurable: true });

        try {
            renderBackdrop();
            const root = screen.getByTestId('cedar-ridge-backdrop');

            await act(async () => {
                for (let i = 0; i < 6; i += 1) {
                    fireEvent.scroll(window);
                    await nextFrame();
                }
            });

            // 900px is past the 400px range, so the term is at full strength.
            expect(Number(root.style.getPropertyValue('--cr-py'))).toBeCloseTo(-18, 1);
        } finally {
            Object.defineProperty(window, 'scrollY', { value: 0, configurable: true });
        }
    });

    it('settles to centre while the document is hidden', async () => {
        Object.defineProperty(document, 'hidden', { value: true, configurable: true });

        try {
            renderBackdrop();
            const root = screen.getByTestId('cedar-ridge-backdrop');

            await act(async () => {
                fireEvent.pointerMove(window, { clientX: 1500, clientY: 900 });
                document.dispatchEvent(new Event('visibilitychange'));
                await nextFrame();
                await nextFrame();
            });

            expect(root.style.getPropertyValue('--cr-px')).toBe('0.00');
            expect(root.style.getPropertyValue('--cr-py')).toBe('0.00');
        } finally {
            Object.defineProperty(document, 'hidden', { value: false, configurable: true });
        }
    });
});
