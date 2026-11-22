import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import { CEDAR_WORLD_ID } from '../backdrop/voxel-world';
import { HomeCtaPage } from './HomeCtaPage';

vi.mock('@tanstack/react-router', () => ({
    Link: ({
        children,
        to,
        className,
        ...rest
    }: {
        children: React.ReactNode;
        to: string;
        className?: string;
    }) => (
        <a href={to} className={className} {...rest}>
            {children}
        </a>
    ),
}));

beforeAll(() => {
    Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation((query: string) => ({
            matches: true,
            media: query,
            onchange: null,
            addListener: vi.fn(),
            removeListener: vi.fn(),
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
            dispatchEvent: vi.fn(),
        })),
    });

    if (typeof globalThis.ResizeObserver === 'undefined') {
        globalThis.ResizeObserver = class ResizeObserver {
            observe() {}
            unobserve() {}
            disconnect() {}
        };
    }
});

describe('HomeCtaPage (Cedar Sanctuary SceneStage, zero-flash initialAtmosphere & tactile CTA plaque)', () => {
    it('renders on SceneStage with reactive motion role and zero-scroll hero viewport shell', () => {
        const { container } = render(<HomeCtaPage initialAtmosphere="after-hours" />);
        const section = container.querySelector('section');

        expect(section).not.toBeNull();
        expect(section).toHaveAttribute('data-slot', 'scene-stage');
        expect(section).toHaveAttribute('data-stage-variant', 'hero');
        expect(section).toHaveAttribute('data-motion-role', 'reactive');
        expect(section).toHaveAttribute('data-atmosphere', 'after-hours');
        expect(section?.className).toContain('scene-atmosphere-after-hours');
        expect(section?.className).not.toContain('home-twilight-sky');
        expect(section?.className).toContain('home-hero-viewport');
        expect(section?.className).not.toContain('min-h-dvh');

        const canvas = screen.getByTestId('garden-backdrop');
        expect(canvas).toHaveAttribute('data-world', CEDAR_WORLD_ID);
        expect(canvas).toHaveAttribute('data-atmosphere', 'after-hours');
    });

    it('uses parent-owned spacing with zero manual child margins on hero elements', () => {
        const { container } = render(<HomeCtaPage />);
        const heroStack = screen.getByTestId('home-hero-content');

        const childrenWithMargins = Array.from(heroStack.querySelectorAll('*')).filter((el) =>
            /\b(m|mt|mb|ml|mr)-\d+/.test(el.className),
        );
        expect(childrenWithMargins).toEqual([]);
        expect(container.querySelector('[data-testid="garden-backdrop"]')).toBeInTheDocument();
    });

    it('frames the CTA cluster and trust strip inside an opaque .scene-scrim .voxel-card plaque without backdrop-blur', () => {
        render(<HomeCtaPage />);

        const plaque = screen.getByTestId('home-cta-plaque');
        expect(plaque.className).toContain('scene-scrim');
        expect(plaque.className).toContain('voxel-card');
        expect(plaque.className).toContain('rounded-none');
        expect(plaque.className).not.toContain('backdrop-blur');

        const startLink = within(plaque).getByTestId('start-building');
        expect(startLink).toHaveAttribute('href', '/lab');
        expect(startLink.className).toContain('font-bold');

        const quizLink = within(plaque).getByTestId('take-personality-test');
        expect(quizLink).toHaveAttribute('href', '/personality');

        const leaderboardLink = within(plaque).getByRole('link', {
            name: /see how the published bots are doing/i,
        });
        expect(leaderboardLink).toHaveAttribute('href', '/leaderboard');

        const trustStrip = within(plaque).getByTestId('home-trust-strip');
        expect(trustStrip.className).toContain('flex-wrap');

        const items = within(trustStrip).getAllByText(
            /Paper cash only|Live every 30m ET|Every loser stays on the record/,
        );
        expect(items).toHaveLength(3);
        for (const item of items) {
            expect(item.className).toContain('whitespace-nowrap');
        }
    });

    it('exposes Sky and Pause HUD controls outside aria-hidden without a multi-world switcher', () => {
        const { container } = render(<HomeCtaPage initialAtmosphere="dusk" />);
        const section = container.querySelector('section');
        const backdropSlot = container.querySelector('[data-slot="scene-backdrop"]');
        const controlsSlot = container.querySelector('[data-slot="scene-controls"]');
        const canvas = screen.getByTestId('garden-backdrop');

        expect(backdropSlot).toHaveAttribute('aria-hidden', 'true');
        expect(backdropSlot?.querySelectorAll('button').length).toBe(0);
        expect(controlsSlot).not.toBeNull();
        expect(controlsSlot).not.toHaveAttribute('aria-hidden');
        expect(screen.queryByTestId('world-switcher')).toBeNull();

        const switcher = screen.getByTestId('atmosphere-switcher');
        expect(section).toHaveAttribute('data-atmosphere', 'dusk');
        expect(canvas).toHaveAttribute('data-atmosphere', 'dusk');

        const seenPhases = new Set<string | null>(['dusk']);
        for (let i = 0; i < 4; i++) {
            fireEvent.click(switcher);
            const nextPhase = section?.getAttribute('data-atmosphere') ?? null;
            seenPhases.add(nextPhase);
            expect(canvas).toHaveAttribute('data-atmosphere', nextPhase);
        }
        expect(seenPhases.size).toBe(4);

        const motionBtn = screen.getByRole('button', { name: /play motion|pause motion/i });
        const initialMotionText = motionBtn.textContent;
        fireEvent.click(motionBtn);
        expect(motionBtn.textContent).not.toBe(initialMotionText);
    });
});
