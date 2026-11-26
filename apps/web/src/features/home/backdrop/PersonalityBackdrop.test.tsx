import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PersonalityBackdrop, type PersonalityBackdropProps } from './PersonalityBackdrop';

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

function renderBackdrop(overrides: Partial<PersonalityBackdropProps> = {}) {
    return render(<PersonalityBackdrop atmosphere="dusk" motion="running" {...overrides} />);
}

describe('PersonalityBackdrop (four act landmarks, horizon-first, frozen-safe)', () => {
    beforeEach(() => {
        mockMatchMedia(false);
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('renders four act landmarks with horizon floor anchor', () => {
        const { container } = renderBackdrop();
        const root = screen.getByTestId('personality-backdrop');

        expect(root).toHaveAttribute('data-world', 'personality-compass');
        expect(root).toHaveAttribute('data-atmosphere', 'dusk');
        expect(root).toHaveAttribute('data-motion', 'running');
        expect(root).toHaveAttribute('data-act', '0');

        const landmarks = container.querySelectorAll('.pb-landmark');
        expect(landmarks).toHaveLength(4);
        expect(Array.from(landmarks).map((l) => l.getAttribute('data-axis'))).toEqual([
            'horizon',
            'signal',
            'crowd',
            'cadence',
        ]);
        expect(container.querySelector('.pb-celestial')).not.toBeNull();
    });

    it('lights exactly one landmark per act, all four on result', () => {
        const cases: Array<[PersonalityBackdropProps['act'], string | null]> = [
            [0, 'horizon'],
            [1, 'signal'],
            [2, 'crowd'],
            [3, 'cadence'],
            ['result', null],
        ];

        for (const [act, activeAxis] of cases) {
            const { rerender, container } = renderBackdrop({ act });
            const root = container.querySelector('[data-testid="personality-backdrop"]');
            expect(root).toHaveAttribute('data-act', String(act));

            const active = container.querySelectorAll('.pb-landmark[data-active="true"]');
            if (activeAxis === null) {
                expect(active).toHaveLength(4);
            } else {
                expect(active).toHaveLength(1);
                expect(active[0]).toHaveAttribute('data-axis', activeAxis);
            }

            const inactive = container.querySelectorAll('.pb-landmark[data-active="false"]');
            if (activeAxis === null) {
                expect(inactive).toHaveLength(0);
            } else {
                expect(inactive).toHaveLength(3);
            }

            rerender(<PersonalityBackdrop atmosphere="dusk" motion="running" act={0} />);
        }
    });

    it('carries the atmosphere phase onto the root for exposure-only styling', () => {
        const phases = ['dawn', 'daylight', 'dusk', 'after-hours'] as const;
        for (const phase of phases) {
            const { unmount } = renderBackdrop({ atmosphere: phase });
            expect(screen.getByTestId('personality-backdrop')).toHaveAttribute(
                'data-atmosphere',
                phase,
            );
            unmount();
        }
    });

    it('carries the derived motion onto the root so CSS can freeze every loop', () => {
        const { rerender } = renderBackdrop();
        expect(screen.getByTestId('personality-backdrop')).toHaveAttribute(
            'data-motion',
            'running',
        );

        rerender(<PersonalityBackdrop atmosphere="dusk" motion="paused" />);
        expect(screen.getByTestId('personality-backdrop')).toHaveAttribute('data-motion', 'paused');

        rerender(<PersonalityBackdrop atmosphere="dusk" motion="reduced" />);
        expect(screen.getByTestId('personality-backdrop')).toHaveAttribute(
            'data-motion',
            'reduced',
        );
    });

    it('ignores pointer drift while paused and settles back to centre', async () => {
        renderBackdrop({ motion: 'paused' });
        const root = screen.getByTestId('personality-backdrop');

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
        const root = screen.getByTestId('personality-backdrop');

        await act(async () => {
            fireEvent.pointerMove(window, { clientX: 1500, clientY: 900 });
            await nextFrame();
            await nextFrame();
        });

        expect(root.style.getPropertyValue('--cr-px')).toBe('0.00');
    });
});
