import { render, screen, within } from '@testing-library/react';
import { beforeAll, describe, expect, it, vi } from 'vitest';
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

describe('HomeCtaPage (twilight hero framing & design-spec compliance)', () => {
    it('renders the SSR twilight sky fallback class and zero-scroll hero viewport shell', () => {
        const { container } = render(<HomeCtaPage />);
        const section = container.querySelector('section');

        expect(section).not.toBeNull();
        expect(section?.className).toContain('home-twilight-sky');
        expect(section?.className).toContain('home-hero-viewport');
        expect(section?.className).not.toContain('min-h-dvh');
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

    it('renders primary CTA, leaderboard link, and a 360px-safe wrapping trust strip', () => {
        render(<HomeCtaPage />);

        const startLink = screen.getByTestId('start-building');
        expect(startLink).toHaveAttribute('href', '/lab');
        expect(startLink.className).toContain('font-bold');

        const leaderboardLink = screen.getByRole('link', {
            name: /see how the published bots are doing/i,
        });
        expect(leaderboardLink).toHaveAttribute('href', '/leaderboard');

        const trustStrip = screen.getByTestId('home-trust-strip');
        expect(trustStrip.className).toContain('flex-wrap');

        const items = within(trustStrip).getAllByText(
            /Paper cash only|Live every 30m ET|Every loser stays on the record/,
        );
        expect(items).toHaveLength(3);
        for (const item of items) {
            expect(item.className).toContain('whitespace-nowrap');
        }
    });
});
