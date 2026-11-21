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
});
