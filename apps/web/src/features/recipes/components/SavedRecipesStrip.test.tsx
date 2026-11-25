import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { RecipeSummaryItem } from '../types';
import { SavedRecipesStrip } from './RecipeGuideAndQuotaBlock';

vi.mock('@tanstack/react-router', () => ({
    Link: ({
        children,
        to,
        params,
        search,
        className,
    }: {
        children: React.ReactNode;
        to: string;
        params?: Record<string, string>;
        search?: Record<string, string>;
        className?: string;
    }) => {
        let href = to;
        if (params) {
            for (const [k, v] of Object.entries(params)) {
                href = href.replace(`$${k}`, v);
            }
        }
        if (search?.recipeId) {
            href = `${href}?recipeId=${search.recipeId}`;
        }
        return (
            <a href={href} className={className}>
                {children}
            </a>
        );
    },
}));

const strategies: RecipeSummaryItem[] = [
    {
        id: 'rec-1',
        name: 'Claude Agent Portfolio Mirror',
        cadence: '3h',
        is_live: true,
        trial_count: 3,
        updated_at: '2026-11-17T12:00:00.000Z',
    },
    {
        id: 'rec-2',
        name: 'Quality Value Screener',
        cadence: '1d',
        is_live: false,
        trial_count: 0,
        updated_at: '2026-11-16T12:00:00.000Z',
    },
];

describe('SavedRecipesStrip', () => {
    it('puts the header on its own line above the strategy chips', () => {
        render(<SavedRecipesStrip recipes={strategies} />);

        const header = screen.getByText('My Strategies:');
        const headerBlock = header.parentElement;

        // Column layout: header is child 0, the chip row is a separate child.
        expect(headerBlock?.className).toContain('flex-col');
        expect(headerBlock?.children[0]).toBe(header);
        expect(headerBlock?.children[1]).not.toBe(header);
        expect(headerBlock?.children[1]?.className).toContain('flex-wrap');
        expect(headerBlock?.children[1]?.textContent).toContain('Claude Agent Portfolio Mirror');
    });

    it('offers a labelled remove control per strategy and reports the chosen row', () => {
        const onRemove = vi.fn();
        render(<SavedRecipesStrip recipes={strategies} onRemove={onRemove} />);

        fireEvent.click(
            screen.getByRole('button', {
                name: 'Remove Quality Value Screener from My Strategies',
            }),
        );

        expect(onRemove).toHaveBeenCalledWith(strategies[1]);
    });

    it('marks the clicked control busy and blocks a second removal in flight', () => {
        render(<SavedRecipesStrip recipes={strategies} onRemove={vi.fn()} removingId="rec-2" />);

        expect(
            screen.getByRole('button', {
                name: 'Remove Quality Value Screener from My Strategies',
            }),
        ).toHaveAttribute('aria-busy', 'true');
        expect(
            screen.getByRole('button', {
                name: 'Remove Claude Agent Portfolio Mirror from My Strategies',
            }),
        ).toBeDisabled();
    });

    it('renders a removal failure inline without dropping the chips', () => {
        render(
            <SavedRecipesStrip
                recipes={strategies}
                onRemove={vi.fn()}
                errorMessage="Failed to remove strategy"
            />,
        );

        expect(screen.getByRole('alert')).toHaveTextContent('Failed to remove strategy');
        expect(screen.getByText('Claude Agent Portfolio Mirror')).toBeInTheDocument();
    });

    it('renders every saved strategy so each one stays removable', () => {
        const many: RecipeSummaryItem[] = Array.from({ length: 8 }, (_, i) => ({
            id: `rec-${i}`,
            name: `Strategy ${i}`,
            cadence: '3h',
            is_live: false,
            trial_count: 0,
            updated_at: '2026-11-17T12:00:00.000Z',
        }));

        render(<SavedRecipesStrip recipes={many} onRemove={vi.fn()} />);

        expect(screen.getAllByRole('link')).toHaveLength(8);
        expect(
            screen.getByRole('button', { name: 'Remove Strategy 7 from My Strategies' }),
        ).toBeInTheDocument();
    });

    it('renders nothing when the user has no strategies', () => {
        const { container } = render(<SavedRecipesStrip recipes={[]} />);
        expect(container).toBeEmptyDOMElement();
    });

    it('links directly to the live status page for live strategies', () => {
        render(<SavedRecipesStrip recipes={strategies} />);

        const liveLinks = screen.getAllByRole('link', { name: /Live Status/i });
        expect(liveLinks).toHaveLength(1);
        expect(liveLinks[0]).toHaveAttribute('href', '/recipes/live/rec-1/runs');
    });
});
