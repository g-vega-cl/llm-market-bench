import { HeroBackground, SceneStage } from '@llm-market-bench/ui-design-system';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

describe('SceneStage', () => {
    it('renders a spatially contained hero stage with dusk atmosphere by default', () => {
        const { container } = render(
            <SceneStage backdrop={<div data-testid="diorama-layer" />}>
                <h1>Benchify Living Hero</h1>
            </SceneStage>,
        );

        const stage = container.querySelector('[data-slot="scene-stage"]') as HTMLElement;
        expect(stage.tagName).toBe('SECTION');
        expect(stage.getAttribute('data-stage-variant')).toBe('hero');
        expect(stage.getAttribute('data-atmosphere')).toBe('dusk');
        expect(stage.getAttribute('data-motion-role')).toBe('background');
        expect(stage.className).toContain('overflow-hidden');
        expect(stage.className).toContain('rounded-none');
        expect(stage.className).toContain('scene-atmosphere-dusk');

        const backdrop = container.querySelector('[data-slot="scene-backdrop"]') as HTMLElement;
        expect(backdrop.getAttribute('aria-hidden')).toBe('true');
        expect(backdrop.className).toContain('pointer-events-none');
        expect(backdrop.className).toContain('scene-backdrop');
        expect(screen.getByTestId('diorama-layer')).toBeInTheDocument();
        expect(screen.getByText('Benchify Living Hero')).toBeInTheDocument();
    });

    it('mounts the world as a fixed page layer and leaves the stage band-free in page mode', () => {
        const { container } = render(
            <SceneStage
                backdropMode="page"
                atmosphere="after-hours"
                motionRole="reactive"
                scrim="panel"
                backdrop={<div data-testid="page-world" />}
                controls={<button type="button">Pause motion</button>}
            >
                <h1>Bot header</h1>
            </SceneStage>,
        );

        const stage = container.querySelector('[data-slot="scene-stage"]') as HTMLElement;
        expect(stage.getAttribute('data-backdrop-mode')).toBe('page');
        expect(stage.className).not.toContain('min-h-80');
        expect(stage.className).not.toContain('min-h-svh');
        expect(stage.className).not.toContain('scene-stage-hero');
        expect(stage.className).not.toContain('scene-atmosphere-after-hours');
        expect(stage.className).toContain('relative');
        expect(stage.className).toContain('z-10');

        const world = container.querySelector('[data-slot="scene-backdrop"]') as HTMLElement;
        expect(world.getAttribute('aria-hidden')).toBe('true');
        expect(world.className).toContain('fixed');
        expect(world.className).toContain('pointer-events-none');
        expect(world.className).toContain('scene-atmosphere-after-hours');
        expect(screen.getByTestId('page-world')).toBeInTheDocument();

        const controls = container.querySelector('[data-slot="scene-controls"]') as HTMLElement;
        expect(controls.className).toContain('justify-end');
        expect(controls.className).not.toContain('fixed');
        expect(controls.getAttribute('aria-hidden')).toBeNull();
    });

    it('renders a footer landmark for parallax footer stages with reactive motion role', () => {
        const { container } = render(
            <SceneStage variant="footer" atmosphere="after-hours" motionRole="reactive">
                <p>Footer world</p>
            </SceneStage>,
        );

        const stage = container.querySelector('[data-slot="scene-stage"]') as HTMLElement;
        expect(stage.tagName).toBe('FOOTER');
        expect(stage.getAttribute('data-stage-variant')).toBe('footer');
        expect(stage.getAttribute('data-atmosphere')).toBe('after-hours');
        expect(stage.getAttribute('data-motion-role')).toBe('reactive');
        expect(stage.className).toContain('scene-atmosphere-after-hours');
        expect(container.querySelector('[data-slot="scene-backdrop"]')).toBeNull();
    });

    it('wraps foreground content in a sharp Matcha scrim panel when scrim="panel"', () => {
        const { container } = render(
            <SceneStage atmosphere="dawn" scrim="panel">
                <span>Protected CTA</span>
            </SceneStage>,
        );

        const scrim = container.querySelector('[data-slot="scene-scrim"]') as HTMLElement;
        expect(scrim).not.toBeNull();
        expect(scrim.className).toContain('scene-scrim');
        expect(scrim.className).toContain('voxel-card');
        expect(scrim.className).toContain('rounded-none');
        expect(scrim.className).not.toContain('backdrop-blur');
        expect(screen.getByText('Protected CTA')).toBeInTheDocument();
    });

    it('supports atmosphere and backdrop slots on modernized HeroBackground', () => {
        const { container } = render(
            <HeroBackground
                atmosphere="daylight"
                backdrop={<div data-testid="hero-diorama-layer" />}
            >
                <span>Market Hero</span>
            </HeroBackground>,
        );

        const root = container.querySelector('[data-slot="hero-background"]') as HTMLElement;
        expect(root.getAttribute('data-atmosphere')).toBe('daylight');
        expect(root.className).toContain('scene-atmosphere-daylight');
        expect(root.className).toContain('rounded-none');
        expect(screen.getByTestId('hero-diorama-layer')).toBeInTheDocument();
    });

    it('renders accessible foreground HUD controls outside aria-hidden when controls slot is supplied', () => {
        const { container } = render(
            <SceneStage
                backdrop={<div data-testid="bg-canvas" />}
                controls={<button type="button">Sky: Dusk</button>}
            >
                <span>Hero Copy</span>
            </SceneStage>,
        );

        const controls = container.querySelector('[data-slot="scene-controls"]') as HTMLElement;
        expect(controls).not.toBeNull();
        expect(controls.getAttribute('aria-hidden')).toBeNull();
        expect(controls.className).toContain('flex-wrap');
        expect(controls.className).toContain('justify-end');
        expect(screen.getByRole('button', { name: 'Sky: Dusk' })).toBeInTheDocument();
    });

    it('uses min-h-svh and compact padding via explicit props instead of custom stylesheet classes', () => {
        const { container } = render(
            <SceneStage viewport padding="compact" backdrop={<div data-testid="vp-canvas" />}>
                <h1>Viewport Hero</h1>
            </SceneStage>,
        );

        const stage = container.querySelector('[data-slot="scene-stage"]') as HTMLElement;
        expect(stage).toHaveAttribute('data-stage-viewport', 'true');
        expect(stage.className).toContain('min-h-svh');
        expect(stage.className).toContain('pt-4');
        expect(stage.className).toContain('pb-6');
        expect(stage.className).not.toContain('min-h-80');
        expect(stage.className).not.toContain('py-12');
    });
});
